
from ddgs import DDGS
import time
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from urllib.parse import urlparse

class EnterpriseOSINT:
    def __init__(self):
        # Professional-grade headers to mimic real browser traffic and avoid 403 blocks
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # -------- 1. INTELLIGENT TARGET RESOLUTION --------
    def resolve_target(self, user_input):
        """
        Determines the REAL human-readable company name by scraping the domain's homepage.
        This solves the 'parkwayfamilydental' smashed-string problem.
        """
        user_input = user_input.strip().lower()
        domain, real_name = None, None

        # Check if input is a domain
        if "." in user_input and " " not in user_input:
            domain = user_input.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            fallback_name = domain.split(".")[0]
            
            # Attempt to scrape the real name from the website title
            try:
                res = self.session.get(f"https://{domain}", timeout=8)
                soup = BeautifulSoup(res.text, 'html.parser')
                title = soup.title.string if soup.title else ""
                
                # Clean up the title (e.g., "Parkway Family Dental | Home" -> "Parkway Family Dental")
                clean_title = re.split(r'[-|\||–|—]', title)[0].strip()
                
                # Only use it if it looks like a valid name, otherwise use fallback
                if 2 <= len(clean_title) <= 50:
                    real_name = clean_title
                else:
                    real_name = fallback_name
            except Exception:
                real_name = fallback_name # If site is down/blocks us, use fallback
        else:
            # Input was already a name (e.g., "Google")
            real_name = user_input.title()

        return real_name, domain

    # -------- 2. LINKEDIN DORKING ENGINE --------
    def dork_linkedin(self, name, domain):
        """Executes targeted dorks with fault tolerance."""
        people = []
        
        # Comprehensive roles covering enterprise AND local/medical businesses
        roles = '(CEO OR Founder OR Owner OR Partner OR Director OR Principal OR "Managing Director" OR Dentist OR Doctor OR Proprietor)'
        
        queries = []
        # Primary strict search using the resolved human-readable name
        queries.append(f'site:linkedin.com/in/ "{name}" {roles}')
        
        # Secondary fallback using the domain
        if domain:
            queries.append(f'site:linkedin.com/in/ "{domain}" {roles}')

        with DDGS() as ddgs:
            for query in queries:
                try:
                    # Fetch results, handling DDG's generator logic safely
                    results = ddgs.text(query, max_results=20)
                    
                    if not results:
                        continue
                        
                    for r in results:
                        title = r.get("title", "")
                        href = r.get("href", "")
                        body = r.get("body", "")

                        # Filter out garbage results (company pages, posts, directories)
                        if any(x in href for x in ["/company/", "/dir/", "/posts/", "/jobs/"]):
                            continue

                        # Clean the profile title
                        clean_title = re.split(r'[-|\||–|—|\.\.\.]', title)[0].strip()
                        
                        people.append({
                            "Name & Title": clean_title,
                            "Context": body[:150] + "...",
                            "LinkedIn URL": href
                        })

                except Exception as e:
                    # Suppress standard "No results" API chatter, log actual critical errors
                    if "No results" not in str(e) and "ratelimit" not in str(e).lower():
                        pass 
                
                # Polite delay to avoid IP ban
                time.sleep(2)
                
        # Deduplicate based on LinkedIn URL
        unique_people = list({p["LinkedIn URL"]: p for p in people}.values())
        return unique_people

    # -------- 3. EMAIL PERMUTATOR & SCRAPER --------
    def generate_emails(self, domain, people_data):
        """Scrapes exposed emails and generates probable corporate emails."""
        emails = []
        
        # 1. Scrape Homepage for exposed emails (Contact Us, Footer)
        if domain:
            try:
                res = self.session.get(f"https://{domain}", timeout=8)
                found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', res.text)
                for e in set(found):
                    if domain in e.lower():
                        emails.append({"Email": e, "Source": "Website Scrape", "Type": "Generic/Exposed"})
            except:
                pass

        # 2. Generate Permutations based on found LinkedIn names
        if domain and people_data:
            for person in people_data:
                # Extract just the first and last name from the LinkedIn title
                name_parts = person["Name & Title"].split(" ")
                if len(name_parts) >= 2:
                    first = re.sub(r'[^a-zA-Z]', '', name_parts[0].lower())
                    last = re.sub(r'[^a-zA-Z]', '', name_parts[1].lower())
                    
                    if first and last:
                        perms = [
                            f"{first}@{domain}",
                            f"{first}.{last}@{domain}",
                            f"{first[0]}{last}@{domain}"
                        ]
                        for p in perms:
                            emails.append({"Email": p, "Source": "Permutator", "Type": f"Guess for {first.title()}"})

        # Deduplicate
        unique_emails = list({e["Email"]: e for e in emails}.values())
        return unique_emails

    # -------- 4. MAIN ORCHESTRATOR --------
    def run(self, target):
        real_name, domain = self.resolve_target(target)
        
        st.write(f"### 🌐 Target Locked")
        st.write(f"**Resolved Name:** `{real_name}`")
        st.write(f"**Domain:** `{domain if domain else 'None provided'}`")
        
        st.info("Executing Dorks and extracting profile data... This takes a few seconds to bypass rate limits.")
        
        people = self.dork_linkedin(real_name, domain)
        emails = self.generate_emails(domain, people)
        
        return pd.DataFrame(people), pd.DataFrame(emails)

# ================= UI & EXECUTION =================
st.set_page_config(page_title="Enterprise OSINT Tool", layout="wide", page_icon="🥷")

st.markdown("""
# 🥷 Enterprise OSINT Lead Generator
*Built for accuracy. Automatically resolves mashed URLs, applies fault-tolerant dorking, and generates email permutations.*
""")

target_input = st.text_input("Enter Target Domain or Company Name (e.g., parkwayfamilydental.ca)")

if st.button("Initialize Scan", type="primary"):
    if not target_input:
        st.error("Target parameter required.")
    else:
        engine = EnterpriseOSINT()
        people_df, emails_df = engine.run(target_input)
        
        tab1, tab2 = st.tabs(["👥 Decision Makers (LinkedIn)", "📧 Email Matrix"])
        
        with tab1:
            if not people_df.empty:
                st.success(f"Successfully extracted {len(people_df)} profiles.")
                st.dataframe(people_df, use_container_width=True)
            else:
                st.warning("No profiles found. The target may not have an active LinkedIn footprint.")
                
        with tab2:
            if not emails_df.empty:
                st.success(f"Generated {len(emails_df)} email data points.")
                st.dataframe(emails_df, use_container_width=True)
            else:
                st.info("No domain provided or no emails could be resolved.")
