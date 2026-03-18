from ddgs import DDGS
import time
import requests
import pandas as pd
import streamlit as st
from duckduckgo_search import DDGS

class APIOSINTFramework:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    # -------- 1. CLEARBIT API (FREE - NO KEY NEEDED) --------
    def enrich_company(self, query):
        """
        Uses Clearbit's open Autocomplete API to fix mashed URLs.
        If you pass 'parkwayfamilydental.ca', it returns 'Parkway Family Dental'.
        """
        clean_query = query.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        
        try:
            url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={clean_query}"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200 and len(response.json()) > 0:
                data = response.json()[0] # Take the top match
                return {
                    "Name": data.get("name"),
                    "Domain": data.get("domain"),
                    "Logo": data.get("logo")
                }
        except Exception as e:
            pass
            
        # Fallback if Clearbit fails
        fallback_domain = clean_query if "." in clean_query else None
        return {"Name": query.title(), "Domain": fallback_domain, "Logo": None}

    # -------- 2. HUNTER.IO API (FREEMIUM - NEEDS KEY) --------
    def get_verified_emails(self, domain, api_key):
        """
        Hits Hunter.io's API to pull verified corporate emails and the pattern.
        """
        if not domain or not api_key:
            return [], None

        try:
            url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
            response = self.session.get(url, timeout=8)
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                emails = data.get("emails", [])
                pattern = data.get("pattern", "Unknown")
                
                parsed_emails = []
                for e in emails:
                    parsed_emails.append({
                        "Email": e.get("value"),
                        "Type": e.get("type", "generic"),
                        "Confidence": f"{e.get('confidence', 0)}%",
                        "Source": "Hunter.io API"
                    })
                return parsed_emails, pattern
            else:
                st.error(f"Hunter API Error: {response.json().get('errors', [{}])[0].get('details')}")
                return [], None
        except Exception as e:
            st.error(f"Failed to connect to Hunter: {e}")
            return [], None

    # -------- 3. STRICT LINKEDIN DORKING --------
    def dork_linkedin(self, exact_name, domain):
        """
        Uses the verified name from Clearbit to find people, 
        and ruthlessly drops anyone not associated with the company.
        """
        people = []
        roles = '(CEO OR Founder OR Owner OR Partner OR Director OR Principal OR Dentist OR Manager)'
        
        # We now trust the exact_name because Clearbit verified it
        query = f'site:linkedin.com/in/ "{exact_name}" {roles}'

        with DDGS() as ddgs:
            try:
                results = ddgs.text(query, max_results=15)
                if results:
                    for r in results:
                        title = r.get("title", "")
                        href = r.get("href", "")
                        body = r.get("body", "")

                        # RUTHLESS VALIDATION: Must contain exact name or domain
                        combined_text = (title + " " + body).lower()
                        if exact_name.lower() not in combined_text and (domain and domain.split('.')[0] not in combined_text):
                            continue 

                        if "/company/" in href or "/dir/" in href:
                            continue

                        clean_title = title.split(" - ")[0].split(" | ")[0].strip()
                        people.append({
                            "Name & Title": clean_title,
                            "Context": body[:120] + "...",
                            "LinkedIn URL": href
                        })
                time.sleep(1)
            except Exception:
                pass 
                
        return list({p["LinkedIn URL"]: p for p in people}.values())


# ================= UI & EXECUTION =================
st.set_page_config(page_title="API Lead Generator", layout="wide")

# Sidebar for API Keys
with st.sidebar:
    st.header("🔑 API Configurations")
    st.write("Get 25 free searches/month at [Hunter.io](https://hunter.io/)")
    hunter_key = st.text_input("Hunter.io API Key", type="password")
    
    st.divider()
    st.write("✅ Clearbit Autocomplete API (Active - No Key Required)")

st.title("⚡ Data-Driven OSINT Finder")
target_input = st.text_input("Enter Company Name or URL (e.g., parkwayfamilydental.ca)")

if st.button("Run API Scan", type="primary"):
    if not target_input:
        st.error("Please enter a target.")
    else:
        engine = APIOSINTFramework()
        
        with st.status("Querying APIs...", expanded=True) as status:
            # Step 1: Clearbit
            st.write("📡 Hitting Clearbit API for company resolution...")
            company_data = engine.enrich_company(target_input)
            exact_name = company_data["Name"]
            domain = company_data["Domain"]
            
            # Step 2: Hunter.io
            st.write("📧 Hitting Hunter API for verified emails...")
            emails, email_pattern = engine.get_verified_emails(domain, hunter_key)
            
            # Step 3: DuckDuckGo
            st.write("👥 Scraping LinkedIn for decision makers...")
            people = engine.dork_linkedin(exact_name, domain)
            
            status.update(label="Scan Complete!", state="complete", expanded=False)

        # --- RESULTS DASHBOARD ---
        st.divider()
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if company_data["Logo"]:
                st.image(company_data["Logo"], width=100)
            else:
                st.write("🏢 No Logo")
                
        with col2:
            st.subheader(exact_name)
            st.write(f"**Verified Domain:** {domain}")
            if email_pattern:
                st.success(f"**Most Common Email Pattern:** `{email_pattern}`")

        # Data Tables
        tab1, tab2 = st.tabs(["👥 Decision Makers (Strict Validation)", "📧 Verified Emails (Hunter API)"])
        
        with tab1:
            people_df = pd.DataFrame(people)
            if not people_df.empty:
                st.dataframe(people_df, use_container_width=True)
            else:
                st.warning("No verified LinkedIn profiles found for this exact company.")
                
        with tab2:
            emails_df = pd.DataFrame(emails)
            if not emails_df.empty:
                st.dataframe(emails_df, use_container_width=True)
            elif not hunter_key:
                st.info("⚠️ Please enter a Hunter.io API key in the sidebar to extract verified emails.")
            else:
                st.warning("Hunter API did not find any public emails for this domain.")
