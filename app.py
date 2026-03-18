import time
import re
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlparse
from ddgs import DDGS


# ================= CORE ENGINE =================
class PowerOSINTFinder:
    def __init__(self):
        self.ddgs = DDGS()

    # -------- INPUT CLEANING --------
    def clean_input(self, user_input):
        user_input = user_input.strip()

        if user_input.startswith(("http://", "https://")):
            domain = urlparse(user_input).netloc
        else:
            domain = user_input.split("/")[0]

        domain = domain.replace("www.", "").lower()

        if "." in domain:
            return domain.split('.')[0], domain
        return user_input.lower(), None

    # -------- EXTRACT COMPANY NAME FROM WEBSITE --------
    def get_company_name(self, domain, fallback):
        try:
            url = f"https://{domain}"
            res = requests.get(url, timeout=5)

            title = re.search(r"<title>(.*?)</title>", res.text, re.IGNORECASE)
            if title:
                name = re.sub(r"[-|].*", "", title.group(1)).strip()
                return name.lower()

        except:
            pass

        return fallback

    # -------- NAME VALIDATION --------
    def is_valid_name(self, name):
        if not name:
            return False

        words = name.split()

        if len(words) < 2 or len(words) > 4:
            return False

        blacklist = ["linkedin", "profile", "company", "team", "jobs"]
        return not any(b in name.lower() for b in blacklist)

    # -------- EMAIL EXTRACTION --------
    def extract_emails(self, text, domain):
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        found = re.findall(pattern, text)

        if not domain:
            return []

        return list(set([e for e in found if domain in e.lower()]))

    # -------- NAME EXTRACTION --------
    def extract_name(self, title, link):
        if "linkedin.com/in" not in link:
            return None

        name = title.split("|")[0].split("-")[0].strip()
        return name if self.is_valid_name(name) else None

    # -------- HUNTER API --------
    def get_hunter_emails(self, domain, api_key=None):
        if not api_key:
            return []

        try:
            url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
            res = requests.get(url, timeout=5).json()

            return [
                {"Email": e["value"], "Source": "Hunter"}
                for e in res.get("data", {}).get("emails", [])
            ]
        except:
            return []

    # -------- MAIN ENGINE --------
    def run(self, target, hunter_api=None):
        core, domain = self.clean_input(target)

        # Extract real company name
        company_name = core
        if domain:
            company_name = self.get_company_name(domain, core)

        queries = [
            # LinkedIn (primary source)
            f'site:linkedin.com/in "{company_name}" "works at"',
            f'site:linkedin.com/in "{company_name}" "company"',
            f'site:linkedin.com/in "{company_name}" founder',
            f'site:linkedin.com/in "{company_name}" owner',
            f'site:linkedin.com/in "{company_name}" director',

            # Leadership
            f'"{company_name}" CEO',
            f'"{company_name}" founder',
            f'"{company_name}" leadership team',

            # Emails
            f'"@{domain}"' if domain else "",
        ]

        leaders, emails, results = [], [], []

        for q in queries:
            if not q:
                continue

            try:
                search_results = list(self.ddgs.text(q, max_results=10))

                for r in search_results:
                    link = r["href"].lower()
                    title = r["title"]
                    body = r["body"]

                    combined = (title + " " + body).lower()

                    # -------- SOURCE FILTER --------
                    allowed_sources = [
                        "linkedin.com",
                        "crunchbase.com",
                        "zoominfo.com",
                        "rocketreach.co",
                    ]

                    if domain:
                        allowed_sources.append(domain)

                    if not any(src in link for src in allowed_sources):
                        continue

                    # -------- LINKEDIN VALIDATION --------
                    if "linkedin.com/in" in link:
                        validation = [company_name, core]

                        job_signals = [
                            "works at",
                            "company",
                            "employee",
                            "founder",
                            "owner",
                            "director",
                            "ceo"
                        ]

                        if not any(v in combined for v in validation):
                            continue

                        if not any(j in combined for j in job_signals):
                            continue

                    # -------- REMOVE USELESS PAGES --------
                    useless = [
                        "blog", "category", "service",
                        "treatment", "patient"
                    ]

                    if any(u in link for u in useless):
                        continue

                    results.append({
                        "Title": title,
                        "Link": r["href"]
                    })

                    # Emails
                    found_emails = self.extract_emails(combined, domain)
                    for e in found_emails:
                        emails.append({"Email": e, "Source": "Search"})

                    # Leaders
                    name = self.extract_name(title, link)
                    if name:
                        leaders.append({
                            "Name": name,
                            "Source": "LinkedIn",
                            "Link": r["href"]
                        })

                time.sleep(1)

            except:
                continue

        # API enrichment
        if domain:
            emails.extend(self.get_hunter_emails(domain, hunter_api))

        # Deduplicate
        leaders_df = pd.DataFrame(leaders).drop_duplicates(subset=["Name"]) if leaders else pd.DataFrame()
        emails_df = pd.DataFrame(emails).drop_duplicates(subset=["Email"]) if emails else pd.DataFrame()
        results_df = pd.DataFrame(results).drop_duplicates(subset=["Link"]) if results else pd.DataFrame()

        return leaders_df, emails_df, results_df


# ================= UI =================
st.set_page_config(page_title="OSINT Power Finder", layout="wide")

st.title("🔎 OSINT Power Finder")

target = st.text_input("Enter Company or Domain")

hunter_key = st.text_input("Hunter API Key (optional)", type="password")

if st.button("Run Scan"):
    if not target:
        st.error("Enter a target")
    else:
        with st.spinner("Running OSINT scan..."):
            engine = PowerOSINTFinder()
            people, emails, results = engine.run(target, hunter_key)

        if people.empty and emails.empty and results.empty:
            st.warning("No strong matches found")
        else:
            tab1, tab2, tab3 = st.tabs(["Leaders", "Emails", "Results"])

            with tab1:
                st.subheader("Decision Makers")
                st.dataframe(people, use_container_width=True)

            with tab2:
                st.subheader("Emails")
                st.dataframe(emails, use_container_width=True)

            with tab3:
                st.subheader("Filtered Results")
                st.dataframe(results, use_container_width=True)

            st.success("Scan complete")
