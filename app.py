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

    # -------- Input Cleaning --------
    def clean_input(self, user_input):
        user_input = user_input.strip()

        if user_input.startswith(('http://', 'https://')):
            domain = urlparse(user_input).netloc
        else:
            domain = user_input.split('/')[0]

        domain = domain.replace("www.", "").lower()

        if "." in domain:
            return domain.split('.')[0], domain
        else:
            return user_input.lower(), None

    # -------- Validation --------
    def is_valid_name(self, name):
        if not name:
            return False

        words = name.split()

        if len(words) < 2 or len(words) > 4:
            return False

        blacklist = [
            "linkedin", "profile", "company",
            "team", "jobs", "hiring",
            "about", "contact", "activities"
        ]

        return not any(b in name.lower() for b in blacklist)

    # -------- Email Extraction --------
    def extract_emails(self, text, domain):
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found = re.findall(pattern, text)

        if not domain:
            return []

        return list(set([e for e in found if domain in e.lower()]))

    # -------- Name Extraction --------
    def extract_name(self, title, link):
        if "linkedin.com/in" not in link.lower():
            return None

        name = title.split("|")[0].split("-")[0].strip()

        return name if self.is_valid_name(name) else None

    # -------- Hunter API (optional) --------
    def get_hunter_emails(self, domain, api_key=None):
        if not api_key:
            return []

        try:
            url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
            res = requests.get(url, timeout=5).json()

            emails = res.get("data", {}).get("emails", [])

            return [{"Email": e["value"], "Source": "Hunter"} for e in emails]
        except:
            return []

    # -------- Main Recon --------
    def run(self, target, hunter_api=None):
        core, domain = self.clean_input(target)

        queries = [
            f'"{core}" CEO',
            f'"{core}" founder',
            f'"{core}" leadership team',
            f'"{core}" site:linkedin.com/in',
        ]

        if domain:
            queries += [
                f'site:{domain} "team"',
                f'site:{domain} "about"',
                f'"{domain}" CEO',
                f'"{domain}" founder',
            ]

        leaders, emails, results = [], [], []

        for q in queries:
            try:
                search_results = list(self.ddgs.text(q, max_results=8))

                for r in search_results:
                    link = r["href"].lower()
                    title = r["title"]
                    body = r["body"]

                    # STRICT DOMAIN FILTER
                    if domain and domain not in link:
                        continue

                    results.append({
                        "Title": title,
                        "Link": r["href"]
                    })

                    # Extract emails
                    emails.extend(
                        [{"Email": e, "Source": "Search"} for e in self.extract_emails(title + body, domain)]
                    )

                    # Extract names
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

        # API ENRICHMENT
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
                st.subheader("Leadership")
                st.dataframe(people, use_container_width=True)

            with tab2:
                st.subheader("Emails")
                st.dataframe(emails, use_container_width=True)

            with tab3:
                st.subheader("Search Results")
                st.dataframe(results, use_container_width=True)

            st.success("Scan complete")
