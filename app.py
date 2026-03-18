import time
import re
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlparse
from ddgs import DDGS


class PowerOSINTFinder:
    def __init__(self):
        self.ddgs = DDGS()

    # -------- INPUT CLEAN --------
    def clean_input(self, user_input):
        user_input = user_input.strip()

        if user_input.startswith(("http://", "https://")):
            domain = urlparse(user_input).netloc
        else:
            domain = user_input.split("/")[0]

        domain = domain.replace("www.", "").lower()

        if "." in domain:
            core = domain.split(".")[0]
            return core, domain
        return user_input.lower(), None

    # -------- NAME CLEAN --------
    def clean_name(self, name):
        words = name.split()

        if len(words) < 2 or len(words) > 4:
            return None

        blacklist = ["linkedin", "profile", "company", "team", "jobs"]
        if any(b in name.lower() for b in blacklist):
            return None

        return name

    # -------- LINKEDIN SEARCH --------
    def search_linkedin(self, core, domain):
        people = []

        queries = [
            f'site:linkedin.com/in "{core}"',
        ]

        for q in queries:
            try:
                results = list(self.ddgs.text(q, max_results=10))

                for r in results:
                    title = r["title"]
                    body = r["body"]
                    link = r["href"]

                    combined = (title + " " + body).lower()

                    # 🔥 BALANCED FILTER (not too strict, not dumb)
                    if core not in combined:
                        continue

                    # Extract name
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
                emails.append({
                    "Email": e,
                    "Source": "Website"
                })

        except:
            pass

        return emails

    # -------- MAIN RUN --------
    def run(self, target):
        core, domain = self.clean_input(target)

        leaders = []
        emails = []

        # LinkedIn
        linkedin_people = self.search_linkedin(core, domain)
        leaders.extend(linkedin_people)

        # Emails
        if domain:
            emails.extend(self.extract_emails(domain))

        # CLEAN DATA
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
        with st.spinner("Scanning..."):
            engine = PowerOSINTFinder()
            people, emails = engine.run(target)

        if people.empty and emails.empty:
            st.warning("No relevant results found")
        else:
            tab1, tab2 = st.tabs(["Leaders", "Emails"])

            with tab1:
                st.subheader("Relevant Profiles")
                st.dataframe(people, use_container_width=True)

            with tab2:
                st.subheader("Emails")
                st.dataframe(emails, use_container_width=True)

            st.success("Scan complete")
