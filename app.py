from ddgs import DDGS
import time
import re
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlparse

class PowerOSINTFinder:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    # -------- HANDLES BOTH WAYS (google.com OR https://google.com) --------
    def clean_input(self, user_input):
        user_input = user_input.strip().lower()
        
        # Add protocol if missing to help urlparse
        if not user_input.startswith(('http://', 'https://')) and "." in user_input:
            temp_input = 'https://' + user_input
        else:
            temp_input = user_input

        parsed = urlparse(temp_input)
        domain = parsed.netloc if parsed.netloc else user_input
        
        # Remove www.
        domain = domain.replace("www.", "")
        
        # Core name (e.g., 'google' from 'google.com')
        core = domain.split(".")[0] if "." in domain else domain
        
        return core, domain

    def clean_name(self, title):
        # Cleans: "John Doe - CEO - Company Name | LinkedIn" -> "John Doe"
        name = re.split(r'[-|–|—]', title)[0].strip()
        words = name.split()
        if len(words) < 2 or len(words) > 4 or "linkedin" in name.lower():
            return None
        return name

    # -------- IMPROVED DORKING FOR DECISION MAKERS --------
    def search_leaders(self, core, domain):
        people = []
        # Target specific personas for pitching
        roles = "(CEO OR Founder OR Director OR VP OR 'Marketing Manager')"
        queries = [
            f'site:linkedin.com/in/ "{core}" {roles}',
            f'site:linkedin.com/in/ "{domain}" {roles}',
        ]

        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = ddgs.text(q, max_results=15)
                    for r in results:
                        title = r.get("title", "")
                        href = r.get("href", "")
                        
                        name = self.clean_name(title)
                        if name and "profiles" not in href:
                            people.append({
                                "Name": name,
                                "Role/Context": title.replace(" | LinkedIn", ""),
                                "Link": href
                            })
                    time.sleep(1.5)
                except Exception as e:
                    st.error(f"Search error: {e}")
        return people

    def extract_emails(self, domain):
        emails = []
        if "." not in domain: return emails
        
        try:
            # Try to scrape the homepage for exposed emails
            res = requests.get(f"https://{domain}", headers=self.headers, timeout=5)
            found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', res.text)
            for e in set(found):
                if domain in e.lower(): # Only keep company-specific emails
                    emails.append({"Email": e, "Source": "Website Scrape"})
        except:
            pass
        return emails

    def run(self, target):
        core, domain = self.clean_input(target)
        st.write(f"🔍 **Targeting:** {core} | **Domain:** {domain}")
        
        people = self.search_leaders(core, domain)
        emails = self.extract_emails(domain)
        
        df_people = pd.DataFrame(people).drop_duplicates(subset=["Name"]) if people else pd.DataFrame()
        df_emails = pd.DataFrame(emails).drop_duplicates(subset=["Email"]) if emails else pd.DataFrame()
        
        return df_people, df_emails

# ================= UI =================
st.set_page_config(page_title="Decision Maker Finder", layout="wide")
st.title("🚀 Decision Maker & Lead Finder")

target = st.text_input("Enter Company Name or URL (e.g. google.com or Google)")

if st.button("Find Decision Makers"):
    if target:
        finder = PowerOSINTFinder()
        people_df, emails_df = finder.run(target)
        
        t1, t2 = st.tabs(["👥 Decision Makers", "📧 Emails Found"])
        with t1:
            st.dataframe(people_df, use_container_width=True)
        with t2:
            st.dataframe(emails_df, use_container_width=True)
    else:
        st.warning("Please enter a target first.")
