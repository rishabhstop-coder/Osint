import time
import pandas as pd
import streamlit as st
from urllib.parse import urlparse
from ddgs import DDGS


class PowerOSINTFinder:
    def __init__(self):
        self.ddgs = DDGS()

    def clean_input(self, user_input):
        user_input = user_input.strip().lower()

        if user_input.startswith(('http://', 'https://')):
            domain = urlparse(user_input).netloc
        else:
            domain = user_input.split('/')[0]

        core_name = domain.split('.')[0]
        return core_name, domain

    def execute_recon(self, target):
        core_name, domain = self.clean_input(target)

        queries = [
            f'"{core_name}" (CEO OR Founder OR President) site:linkedin.com/in/',
            f'"{domain}" (CEO OR Founder OR Owner)',
            f'site:{domain} "About Us" OR "Our Team"',
            f'"{core_name}" leadership team names'
        ]

        results_list = []

        for q in queries:
            try:
                results = list(self.ddgs.text(q, max_results=5))
                for r in results:
                    text = (r['title'] + " " + r['body']).lower()

                    if core_name in text or domain in text:
                        raw_name = r['title'].split('|')[0].split('-')[0].strip()

                        if len(raw_name.split()) > 1 and "linkedin" not in raw_name.lower():
                            results_list.append({
                                'Name': raw_name,
                                'Link': r['href']
                            })
                time.sleep(1)
            except:
                continue

        return results_list


st.title("🔎 OSINT Power Finder")

target = st.text_input("Enter Company or Domain")

if st.button("Run Scan"):
    if target:
        recon = PowerOSINTFinder()
        results = recon.execute_recon(target)

        if results:
            df = pd.DataFrame(results).drop_duplicates()
            st.dataframe(df)
        else:
            st.warning("No data found")
