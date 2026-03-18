<!DOCTYPE html>
<html>
<head>
    <title>🔥 OSINT POWER FINDER — NUCLEAR MODE</title>
    <style>
        body { font-family: monospace; background: #0a0a0a; color: #0f0; padding: 20px; }
        pre { background: #111; padding: 20px; border: 2px solid #0f0; overflow-x: auto; }
    </style>
</head>
<body>
<h1>🚀 HERE'S THE FUCKING NUCLEAR VERSION</h1>
<p>I turned your script into a goddamn monster. More queries, smarter cleaning, auto email extraction, LinkedIn name parsing, tabs, spinner, and it actually searches the SHIT out of everything.</p>

<pre><code>
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
        
        if '.' in domain and ' ' not in domain and len(domain) > 4:
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
            if domain_lower and (domain_lower in email.lower() or email.lower().split('@')[1].endswith(domain_lower)):
                relevant.append(email)
            elif '@' in email:
                relevant.append(email)
        return list(set(relevant))

    def extract_potential_names(self, title, link):
        if 'linkedin.com/in' in link.lower():
            try:
                name_part = title.split('|')[0].split(' - ')[0].strip()
                if len(name_part.split()) >= 2 and len(name_part) < 60 and not any(w in name_part.lower() for w in ['linkedin', 'profile', 'company']):
                    return name_part
            except:
                pass
        return None

    def execute_recon(self, target):
        core_name, website = self.clean_input(target)
        
        queries = [
            f'"{core_name}" (CEO OR Founder OR President OR "Managing Director" OR Director) site:linkedin.com/in/',
            f'"{core_name}" (CEO OR Founder OR President OR Owner OR Director)',
            f'"{core_name}" (CFO OR CTO OR CMO OR "Chief")',
            f'who is the CEO of {core_name}',
            f'who is the founder of {core_name}',
            f'"{core_name}" (leadership OR executives OR "key personnel" OR "board members")',
            f'"{core_name}" site:crunchbase.com',
            f'"{core_name}" site:linkedin.com/company',
        ]
        
        if website:
            queries.extend([
                f'site:{website} ("About Us" OR "Our Team" OR "Leadership" OR "Meet the Team" OR "Contact Us")',
                f'site:{website} (email OR contact OR "@")',
                f'filetype:pdf site:{website} (CEO OR director OR team)',
                f'@{website} (CEO OR founder)',
            ])

        results_list = []
        emails_list = []
        leaders = []

        for q in queries:
            try:
                results = list(self.ddgs.text(q, max_results=10))
                for r in results:
                    full_text = r['title'] + " " + r['body']
                    full_lower = full_text.lower()
                    
                    if core_name in full_lower or (website and website in full_lower):
                        results_list.append({
                            'Title': r['title'],
                            'Link': r['href'],
                            'Snippet': (r['body'][:300] + '...') if len(r['body']) > 300 else r['body']
                        })

                        # Emails
                        found_emails = self.extract_emails(full_text, website or core_name)
                        for em in found_emails:
                            emails_list.append({'Email': em, 'Link': r['href']})

                        # LinkedIn names
                        name = self.extract_potential_names(r['title'], r['href'])
                        if name:
                            leaders.append({'Name': name, 'Link': r['href']})
                
                time.sleep(1.2)  # rate limit friendly but still aggressive
            except:
                continue

        # Deduplicate
        leaders_df = pd.DataFrame(leaders).drop_duplicates(subset=['Name']) if leaders else pd.DataFrame(columns=['Name', 'Link'])
        emails_df = pd.DataFrame(emails_list).drop_duplicates(subset=['Email']) if emails_list else pd.DataFrame(columns=['Email', 'Link'])
        general_df = pd.DataFrame(results_list).drop_duplicates(subset=['Link']) if results_list else pd.DataFrame()

        return leaders_df, emails_df, general_df


# ===================== STREAMLIT UI =====================
st.set_page_config(page_title="NUCLEAR OSINT", page_icon="☢️", layout="wide")
st.title("☢️ OSINT POWER FINDER — NUCLEAR MODE")
st.markdown("**I turned it into a fucking monster. More queries. Emails extracted. LinkedIn names parsed. It searches the SHIT out of everything.**")

target = st.text_input("Enter Company Name or Domain (e.g. tesla.com or Google)", placeholder="tesla.com")

if st.button("🚀 LAUNCH NUCLEAR SCAN", type="primary"):
    if target:
        with st.spinner("Searching the absolute shit out of it... (this actually goes hard)"):
            recon = PowerOSINTFinder()
            people_df, emails_df, general_df = recon.execute_recon(target)
        
        if people_df.empty and emails_df.empty and general_df.empty:
            st.error("Nothing found. Target might be too obscure or DDGS blocked it.")
        else:
            tab1, tab2, tab3 = st.tabs(["👔 LEADERS", "📧 EMAILS", "📋 RAW HITS"])
            
            with tab1:
                st.subheader("Auto-Extracted Leadership")
                if not people_df.empty:
                    st.dataframe(people_df, use_container_width=True)
                else:
                    st.info("No clear LinkedIn names extracted (try deeper manual check)")
            
            with tab2:
                st.subheader("Extracted Emails")
                if not emails_df.empty:
                    st.dataframe(emails_df, use_container_width=True)
                else:
                    st.info("No emails found in snippets")
            
            with tab3:
                st.subheader("All Search Results")
                if not general_df.empty:
                    st.dataframe(general_df, use_container_width=True)
                else:
                    st.warning("No results at all")
            
            st.success("💥 SCAN COMPLETE — WE SEARCHED THE SHIT OUT OF IT")
            st.balloons()
    else:
        st.error("Enter a target you lazy fuck")

st.caption("Pro tip: Use company domains for best results. DDGS is free but can get rate-limited — this version already sleeps smart.")
</code></pre>

<p><strong>Just copy-paste the whole thing into a new .py file and run with <code>streamlit run yourfile.py</code></strong></p>
<p>It now has 12+ aggressive queries, proper domain/company handling, email regex extraction, better name parsing, tabs, and a proper spinner. This is as powerful as a free DDGS script can get without getting banned instantly.</p>
<p>Want it even more insane (Hunter.io API, phone extraction, parallel threads)? Say the word and I'll drop v2.</p>
</body>
</html>
