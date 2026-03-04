> How can I do a comprehensive search of the most promising startups in Europe working in robotics, energy and minerals. How would I setup to do such a through search. I'm looking for companies with recent funding and hiring software engineers and of course doing AI. A script? Where can I find the data?



**To conduct a comprehensive, ongoing search for promising European startups in robotics, energy, and minerals (including critical raw materials/mining tech) that have recent funding, are actively hiring software engineers, and are doing AI, you need a systematic, multi-source pipeline.** These sectors overlap heavily in "deep tech" (e.g., AI-powered robotics for energy/mining automation, autonomous systems, critical mineral exploration/recovery with ML, grid optimization, etc.). Europe has strong momentum here via EU priorities (EIC Accelerator, Horizon Europe, EIT RawMaterials) and reports like Dealroom's European Deep Tech Report.

"Promising" = traction via quality investors (e.g., Index Ventures, Atomico, Project A), employee growth, news/patents, or pilot customers. Focus on HQ/founding in EU27 + UK/CH/NO/IS. Target early-to-growth stage (Seed to Series B/C, <~200 employees typically).

### Step-by-Step Setup for Thorough, Repeatable Search
1. **Define Precise Filters (Use These Everywhere)**:
   - Location: Europe (filter by specific countries or "Europe" aggregate).
   - Industries/Sectors: Robotics (or autonomous systems, industrial automation); Energy (cleantech, renewables, grid, storage, nuclear/SMR, geothermal); Minerals/Mining (critical raw materials, mining tech, battery materials, recycling, exploration).
   - AI: Keywords like "artificial intelligence", "machine learning", "AI", "autonomous", "computer vision", "predictive" in description/tech stack/products.
   - Funding: Raised in last 24-36 months (at least €1-5M+ total or recent round); exclude grants-only unless VC-backed.
   - Hiring: Actively posting/open roles for "Software Engineer", "AI Engineer", "ML Engineer", "Backend/Full-stack" (check last 3-6 months; signals like headcount growth >10-20% or "We're hiring" on site/LinkedIn).
   - Other: Founded <10-12 years ago preferred; traction signals (customers, pilots, patents); exclude pure software if no hardware/physical tie-in.

2. **Core Data Sources (Ranked by Europe Strength & Relevance)**:
   - **Dealroom.co** (best starting point for Europe/deep tech): Excellent ecosystem mapping, funding, talent metrics, and sector reports (e.g., 2025 European Deep Tech Report covers robotics €700M+, novel energy, AI applications). Search/filter by location=Europe, industries=robotics/energy/advanced materials/mining, technologies=AI, funding activity=recent. Tracks ~90k+ funded European startups. Book a demo (enterprise plans); some free ecosystem views. Strong for robotics/energy/minerals overlaps.
   - **Crunchbase** (gold standard for funding): Public hubs like "Europe Robotics Companies" or "European Union Robotics Companies". Advanced search: HQ in European countries + categories (Robotics, Energy, Mining) + keywords (AI) + funding rounds date filter. Pro/Enterprise unlocks full API + exports. Great for recent rounds (e.g., warehouse robotics, energy storage).
   - **Harmonic.ai**: AI-native database (35M+ companies, 195M+ professional profiles). Fresh funding signals, headcount/hiring velocity, people search (great for spotting SWE hiring via LinkedIn-like profiles). AI search/agent for custom queries like "Europe robotics startups raising recently with AI". Subscriptions start affordable (web platform + alerts); enterprise for CSV/API/bulk. Ideal for "promising" discovery before others.
   - **Specialized/Complementary**:
     - ai-startups-europe.eu: Free directory of 1,500+ AI startups by country (filter Germany/France/Netherlands for robotics/energy).
     - EU-Startups.com + Sifted.eu: News, funded lists, job board for European startups (search "robotics funding" or "critical minerals").
     - Growthlist.co or Seedtable: AI/funded startup trackers.
     - EIT RawMaterials / EU Funding Portal: Grants for minerals/energy/AI (e.g., alternatives to critical minerals, robotics for recycling).
     - LinkedIn (Sales Navigator ideal): Upload company list from above, filter jobs posted recently + "software engineer" + Europe.

3. **Hiring + AI Validation Layer**:
   - After getting candidate lists (100-500 companies), cross-reference:
     - LinkedIn: Search "[company name] software engineer" or "hiring" + company page (jobs tab, employee posts). Sales Nav lets you filter by company list + recent postings.
     - Company websites: Careers page + "AI" / "machine learning" mentions.
     - Signals: Headcount growth (Harmonic/Crunchbase), recent job posts on Wellfound (AngelList), JobFluent, or EU-Startups jobs.

4. **Ongoing Monitoring & Alerts**:
   - Set email/Slack alerts in Crunchbase/Harmonic/Dealroom for new funding in your filters.
   - Google Alerts: "robotics startup Europe funding" OR "critical minerals AI Europe" OR "energy robotics funding".
   - Follow VCs active in space (e.g., via their portfolios) and EU programs (EIC, Horizon calls for GenAI in robotics/energy).
   - Monthly: Re-run searches + review Sifted/EU-Startups roundups.

5. **Scoring & Shortlisting**:
   - Export to Airtable/Notion/Google Sheets.
   - Columns: Company, Location, Sector, Recent Funding (amount/date/investors), AI Use, Hiring Signals, Website, Score (e.g., investor quality + funding size + hiring velocity).
   - Prioritize: Recent €10M+ rounds, top-tier investors, explicit AI/robotics for minerals/energy (e.g., autonomous drilling/exploration).

### Example Companies That Fit (From Recent Public Data)
- **Hades Mining** (Germany): Critical minerals + geothermal energy via advanced drilling (robotics/tech tie-in); €15M recent round + prior pre-seed.
- **Nomagic** (Poland): Warehouse robotics with physical AI; recent $10M extension.
- Others in pipeline: Look for Trener Robotics (Norway, industrial adaptive robots, $32M), Sofi Filtration (Finland, critical mineral recovery from wastewater via cleantech), plus many in Dealroom deep tech reports (humanoids, quadrupeds, AI for grid/mining).

### Script / Automation for Scale (Python-Based)
If you subscribe to Crunchbase API (or Dealroom/Harmonic equivalents), automate pulls. Otherwise, export CSVs manually and enrich.

**Sample Python Setup (using Crunchbase API – requires API key from Pro plan; adapt for others)**:
```python
import requests
import pandas as pd
from datetime import datetime

# Your Crunchbase API key
API_KEY = 'your_key_here'
BASE_URL = 'https://api.crunchbase.com/api/v4/searches/organizations'

def search_startups():
    payload = {
        "field_ids": ["identifier", "short_description", "location_identifiers", "categories", "num_funding_rounds", "last_funding_at", "founded_on"],
        "order": [{"field_id": "last_funding_at", "sort": "desc"}],
        "query": [
            {"type": "predicate", "field_id": "location_identifiers", "operator_id": "includes", "values": ["Europe countries list or use continent filter"]},  # e.g., Germany, France, UK, etc.
            {"type": "predicate", "field_id": "categories", "operator_id": "includes", "values": ["Robotics", "Energy", "Mining"]},  # or specific
            {"type": "predicate", "field_id": "short_description", "operator_id": "contains", "values": ["AI", "artificial intelligence", "machine learning"]},
            {"type": "predicate", "field_id": "last_funding_at", "operator_id": "gte", "values": ["2023-01-01"]}  # recent
        ],
        "limit": 200
    }
    
    response = requests.post(f"{BASE_URL}?user_key={API_KEY}", json=payload)
    data = response.json()
    
    # Process to DataFrame (funding, etc.)
    companies = []
    for item in data.get('entities', []):
        companies.append({
            'name': item['properties']['identifier']['value'],
            'description': item['properties']['short_description'],
            'location': item['properties']['location_identifiers'],
            'last_funding': item['properties']['last_funding_at'],
            # Add more fields
        })
    df = pd.DataFrame(companies)
    df.to_csv('europe_robotics_energy_mineral_startups.csv', index=False)
    return df

# Run and then enrich hiring (e.g., via another function calling LinkedIn API or Selenium on careers pages)
```

**For Hiring Automation (No API Needed, Use Carefully – Respect TOS)**:
- Use libraries like `jobspy` (Python) or Apify actors (no-code, has LinkedIn/Indeed scrapers) to query "software engineer" + company name list.
- Or Selenium/Playwright script to visit each company's /careers and search for keywords.
- Bulk: Upload company list to LinkedIn Sales Nav or PhantomBuster.

**No-Code Alternative (Easier for Most)**:
- Zapier/Make.com/n8n: Trigger on new funding RSS/news → enrich via APIs → check LinkedIn → add to Airtable.
- Apify or BrightData for scheduled scrapes of job boards + company sites.

**Cost & Time Estimate**:
- Free tier/start: 1-2 weeks manual (Crunchbase free search + LinkedIn) → 50-100 candidates.
- Paid (Crunchbase Pro ~$29-99/mo + Dealroom/Harmonic demo): Full pipeline in days, then automated weekly runs.
- Legal note: API use is fine; heavy scraping of public sites risks blocks/TOS issues—prefer paid tools or manual for top 50.

**Pro Tips**:
- Start narrow (e.g., robotics + AI + Europe + funding 2024+) then expand to energy/minerals.
- Validate "doing AI" by quick website/news check (many robotics/energy firms now integrate it).
- For minerals specifically: Add "critical raw materials", "battery minerals", "rare earth" or EIT RawMaterials-funded.
- Track via personal dashboard (Notion/Airtable) and reach out via LinkedIn (warm via shared connections).

This setup scales from one-off deep dive to always-on pipeline. If you have access to specific paid tools already or want help refining a script/export, provide more details! Sources like Dealroom reports and recent Sifted/Crunchbase news confirm the space is heating up fast.



----

Perfect — that's clear enough to dive in. You're targeting European startups (<100 employees) in robotics, energy, and minerals/mining that are AI-driven, recently funded, and hiring software engineers, with the goal of joining one. I'll research:

- **Best data sources and APIs** (Crunchbase, Dealroom, PitchBook alternatives, job boards, EU-specific databases)
- **Top matching companies** across those three verticals
- **A methodology + reusable script template** for ongoing discovery

Kicking off the deep research now.Your European AI startup discovery report is ready. It covers data sources and APIs for building a repeatable screening pipeline, profiles 28 vetted startups across robotics, energy, and mining, and includes a working Python script for automated discovery. The report features funding details, employee estimates, hiring signals, and a cross-referencing strategy using Dealroom, Crunchbase, CORDIS, and free job APIs like Adzuna and Arbeitnow.
