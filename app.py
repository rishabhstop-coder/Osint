import time
import re
import requests
import pandas as pd
import streamlit as st
from urllib.parse import urlparse
from duckduckgo_search import DDGS

class PowerOSINTFinder:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    # -------- HANDLES google.com, https://google.com, or "Google" --------
    def clean_input(self, user_input):
        user_input = user_input.strip()
        
        # 1. Check if it looks like a URL or just a name
        if "." in user_input:
            if not user_input.startswith(('http://', 'https://')):
                temp_url = 'https://' + user_input
            else:
                temp_url = user_input
            
            parsed = urlparse(temp_url)
            domain = parsed.netloc.replace("www.", "")
            # Extract name from domain (google.com -> google)
            core_name = domain.split(".")[0].capitalize()
        else:
            # It's just a name (e.g., "Tesla")
            core_name = user_input.capitalize()
            domain = None
            
        return core_name, domain

    def clean_name(self, title, target_name):
        # STRICTOR FILTER: Title must contain the target company name
        if target_name.lower() not in title.lower():
            return None
            
        # Clean: "John Doe - CEO - Google | LinkedIn" -> "John Doe"
        name_part = re.split(r'[-|–|—]', title)[0].strip()
        words = name_part.split()
        
        if len(words) < 2 or len(words) > 4:
            return None
        return name_part

    # -------- STRICT DORKING --------
    def search_leaders(self, core_name, domain):
        people = []
        # We use 'intitle' to force the company name AND role to be in the title
        # This prevents "famous" CEOs from other companies popping up
        queries = [
            f'site:linkedin.com/in/ intitle:"{core_name}" (CEO OR Founder OR Owner OR Director)',
            f'site:linkedin.com/in/ "{core_name}" "Current"' 
        ]

        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = ddgs.text(q, max_results=10)
                    for r in results:
                        title = r.get("title", "")
                        href = r.get("href", "")
                        
                        name = self.clean_name(title, core_name)
                        if name:
                            people.append({
                                "Name": name,
                                "Position": title.split("|")[0].strip(),
                                "Link": href
                            })
                    time.sleep(2) # Prevent rate limiting
                except Exception as e:
                    st.error(f"Search error: {e}")
        return people

    def run(self, target):
        core_name, domain = self.clean_input(target)
        st.info(f"🔎 Scanning for: **{core_name}**")
        
        people = self.search_leaders(core_name, domain)
        df_people = pd.DataFrame(people).drop_duplicates(subset=["Name"]) if people else pd.DataFrame()
        
        return df_people, domain

# ================= UI =================
st.set_page_config(page_title="Lead Finder Pro", layout="wide")
st.title("🎯 Precise Decision Maker Finder")

target = st.text_input("Enter Company Name or URL (e.g., 'google.com' or 'Apple')")

if st.button("Find Leaders"):
    if target:
        finder = PowerOSINTFinder()
        people_df, domain = finder.run(target)
        
        if not people_df.empty:
            st.subheader(f"Relevant Decision Makers")
            st.dataframe(people_df, use_container_width=True)
            
            # Show Free API links for the next step
            st.divider()
            st.markdown("### 💡 Next Step: Get Verified Emails")
            st.write("Use these free tools to find the emails for the names above:")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.link_button("Apollo.io (10k Free/Mo)", "https://www.apollo.io/")
            with col2:
                st.link_button("Hunter.io (Search Patterns)", "https://hunter.io/")
            with col3:
                st.link_button("Lusha (Direct Dials)", "https://www.lusha.com/")
        else:
            st.warning("No precise matches found. Try entering the full legal company name.")
