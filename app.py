import time
import re
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ddgs import DDGS


# ================= CORE ENGINE =================
class PowerOSINTFinder:
    def __init__(self):
        self.ddgs = DDGS()

    # -------- CLEAN INPUT --------
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

    # -------- GET COMPANY NAME --------
    def get_company_name(self, domain, fallback):
        try:
            res = requests.get(f"https://{domain}", timeout=5)
            title = re.search(r"<title>(.*?)</title>", res.text, re.IGNORECASE)

            if title:
                return re.sub(r"[-|].*", "", title.group(1)).strip().lower()
        except:
            pass

        return fallback

    # -------- SCRAPE WEBSITE TEAM --------
    def scrape_website_people(self, domain):
        people = []

        paths = [
            "/team", "/about", "/about-us",
            "/our-team", "/staff"
        ]

        for path in paths:
            try:
                url = f"https://{domain}{path}"
                res = requests.get(url, timeout=5)

                soup = BeautifulSoup(res.text, "html.parser")
                text = soup.get_text()

                matches = re.findall(
                    r"(Dr\.?\s?[A-Z][a-z]+(?:\s[A-Z][a-z]+)+|[A-Z][a-z]+\s[A-Z][a-z]+)",
                    text
                )

                for m in matches:
                    if 2 <= len(m.split()) <= 3:
                        people.append({
                            "Name": m.strip(),
                            "Source": "Website",
                            "Link": url
                        })

            except:
                continue

        return people

    # -------- LINKEDIN NAME CLEAN --------
    def clean_name(self, name):
        words = name.split()

        if len(words) < 2 or len(words) > 4:
            return None

        blacklist = ["linkedin", "profile", "company", "team"]
        if any(b in name.lower() for b in blacklist):
            return None

        return name

    # -------- LINKEDIN SEARCH --------
    def search_linkedin_people(self, company_name, domain):
        people = []

        queries = [
            f'site:linkedin.com/in "{company_name}" "works at"',
            f'site:linkedin.com/in "{company_name}" founder',
            f'site:linkedin.com/in "{company_name}" owner',
        ]

        for q in queries:
            try:
                results = list(self.ddgs.text(q, max_results=5))

                for r in results:
                    link = r["href"]
                    title = r["title"]
                    text = (title + " " + r["body"]).lower()

                    # STRICT MATCH
                    if company_name not in text:
                        continue

                    if domain and domain not in text:
                        continue

                    name = title.split("|")[0].split("-")[0].strip()
                    name = self.clean_name(name)

                    if name:
                        people.append({
                            "Name": name,
                            "Source": "LinkedIn",
                            "Link": link
                        })

                time.sleep(1)

            except:
                continue

        return people

    # -------- EMAIL EXTRACTION --------
    def extract_emails(self, domain):
        emails = []

        try:
            res = requests.get(f"https://{domain}", timeout=5)
            found = re.findall(
                r"[a-zA-Z0-9._%+-]+@" + re.escape(domain),
                res.text
            )

            for e in set(found):
                emails.append({"Email": e, "Source": "Website"})

        except:
            pass

        return emails

    # -------- MAIN ENGINE --------
    def run(self, target):
        core, domain = self.clean_input(target)

        company_name = core
        if domain:
            company_name = self.get_company_name(domain, core)

        leaders = []
        emails = []

        # 🔥 PRIORITY 1: WEBSITE (REAL DATA)
        if domain:
            website_people = self.scrape_website_people(domain)
            leaders.extend(website_people)

        # 🔥 PRIORITY 2: LINKEDIN (VALIDATED)
        linkedin_people = self.search_linkedin_people(company_name, domain)
        leaders.extend(linkedin_people)

        # 🔥 EMAILS
        if domain:
            emails.extend(self.extract_emails(domain))

        # CLEAN
        leaders_df = pd.DataFrame(leaders).drop_duplicates(subset=["Name"]) if leaders else pd.DataFrame()
        emails_df = pd.DataFrame(emails).drop_duplicates(subset=["Email"]) if emails else pd.DataFrame()

        return leaders_df, emails_df


# ================= UI =================
st.set_page_config(page_title="OSINT Power Finder", layout="wide")

st.title("🔎 OSINT Power Finder")

target = st.text_input("Enter Company or Domain")

if st.button("Run Scan"):
    if not target:
        st.error("Enter a target")
    else:
        with st.spinner("Running OSINT scan..."):
            engine = PowerOSINTFinder()
            people, emails = engine.run(target)

        if people.empty and emails.empty:
            st.warning("No strong matches found")
        else:
            tab1, tab2 = st.tabs(["Leaders", "Emails"])

            with tab1:
                st.subheader("Decision Makers (Accurate)")
                st.dataframe(people, use_container_width=True)

            with tab2:
                st.subheader("Emails")
                st.dataframe(emails, use_container_width=True)

            st.success("Scan complete")
