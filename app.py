import time
import re
import pandas as pd
import streamlit as st
from urllib.parse import urlparse
from ddgs import DDGS


class PowerOSINTFinder:
    def __init__(self):
        self.ddgs = DDGS()

    def clean_input(self, user_input):
        user_input = user_input.strip()

        if user_input.lower().startswith(('http://', 'https://')):
            domain = urlparse(user_input).netloc
        else:
            domain = user_input.split('/')[0]

        domain = re.sub(r'^https?://', '', domain).split('/')[0].strip().lower()

        if '.' in domain and ' ' not in domain:
            website = domain
            core_name = domain.split('.')[0].replace('www.', '')
        else:
            website = None
            core_name = user_input.lower()

        return core_name, website

    def extract_emails(self, text, domain_part):
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, text)

        relevant = []
        domain_lower = domain_part.lower() if domain_part else ''

        for email in emails:
            if domain_lower and domain_lower in email.lower():
                relevant.append(email)
            else:
                relevant.append(email)

        return list(set(relevant))

    def extract_potential_names(self, title, link):
        if 'linkedin.com/in' in link.lower():
            name_part = title.split('|')[0].split(' - ')[0].strip()

            if 2 <= len(name_part.split()) <= 4:
                return name_part

        return None

    def execute_recon(self, target):
        core_name, website = self.clean_input(target)

        queries = [
            f'"{core_name}" (CEO OR Founder OR President OR Director) site:linkedin.com/in/',
            f'"{core_name}" (CEO OR Founder OR Owner OR Director)',
            f'"{core_name}" (CFO OR CTO OR CMO)',
            f'who is the CEO of {core_name}',
            f'"{core_name}" leadership team',
        ]

        if website:
            queries.extend([
                f'site:{website} ("About Us" OR "Team" OR "Leadership")',
                f'site:{website} (email OR contact)',
            ])

        results_list = []
        emails_list = []
        leaders = []

        for q in queries:
            try:
                results = list(self.ddgs.text(q, max_results=8))

                for r in results:
                    full_text = r['title'] + " " + r['body']
                    full_lower = full_text.lower()

                    if core_name in full_lower or (website and website in full_lower):
                        results_list.append({
                            'Title': r['title'],
                            'Link': r['href']
                        })

                        # Emails
                        emails = self.extract_emails(full_text, website or core_name)
                        for e in emails:
                            emails_list.append({'Email': e, 'Link': r['href']})

                        # Names
                        name = self.extract_potential_names(r['title'], r['href'])
                        if name:
                            leaders.append({'Name': name, 'Link': r['href']})

                time.sleep(1)

            except:
                continue

        leaders_df = pd.DataFrame(leaders).drop_duplicates() if leaders else pd.DataFrame()
        emails_df = pd.DataFrame(emails_list).drop_duplicates() if emails_list else pd.DataFrame()
        general_df = pd.DataFrame(results_list).drop_duplicates() if results_list else pd.DataFrame()

        return leaders_df, emails_df, general_df


# ================= UI =================
st.set_page_config(page_title="OSINT Finder", layout="wide")

st.title("🔎 OSINT Power Finder")

target = st.text_input("Enter Company or Domain")

if st.button("Run Scan"):
    if target:
        with st.spinner("Scanning..."):
            recon = PowerOSINTFinder()
            people_df, emails_df, general_df = recon.execute_recon(target)

        if people_df.empty and emails_df.empty and general_df.empty:
            st.warning("No data found")
        else:
            tab1, tab2, tab3 = st.tabs(["Leaders", "Emails", "Results"])

            with tab1:
                st.dataframe(people_df, use_container_width=True)

            with tab2:
                st.dataframe(emails_df, use_container_width=True)

            with tab3:
                st.dataframe(general_df, use_container_width=True)

            st.success("Scan complete")
    else:
        st.error("Enter a target")
