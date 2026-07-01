"""Portfolio project catalog, organised by role category.

Each entry is a self-contained project idea a candidate can build to become
competitive for that role. The recommendation engine selects from the catalogs
matching the role categories present in the discovered jobs.
"""
from __future__ import annotations


PROJECT_CATALOG: dict[str, list[dict]] = {
    # ------------------------------------------------------------------ #
    "analytics": [
        {
            "title": "E-Commerce Sales Analytics Dashboard",
            "industry": "Retail / E-Commerce",
            "business_problem": "Track sales performance, customer segments, and revenue trends",
            "dataset_source": "Kaggle - Brazilian E-Commerce by Olist",
            "dataset_url": "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
            "skills": ["sql", "python", "tableau", "excel"],
            "difficulty": "Beginner",
            "estimated_hours": 20,
            "description": (
                "Analyze 100k+ orders across customer geography, product categories, "
                "and delivery performance. Build SQL for cohort analysis, RFM "
                "segmentation, and a dashboard of the KPIs."
            ),
            "key_tasks": [
                "Model a star schema and load the data",
                "Query monthly revenue by region and customer lifetime value",
                "Build cohort retention and product-affinity analysis",
                "Ship an executive KPI dashboard with a geographic heat map",
            ],
            "resume_bullets": [
                "Built a SQL analytics pipeline over 100k+ e-commerce transactions",
                "Surfaced a 23% customer-retention opportunity via cohort analysis",
            ],
        },
        {
            "title": "Marketing Campaign Performance Analytics",
            "industry": "Marketing",
            "business_problem": "Measure ROI across marketing channels and optimize spend",
            "dataset_source": "Kaggle - Marketing Campaign Data",
            "dataset_url": "https://www.kaggle.com/datasets/rodsaldanha/arketing-campaign",
            "skills": ["sql", "excel", "tableau", "power bi"],
            "difficulty": "Beginner",
            "estimated_hours": 15,
            "description": (
                "Analyze campaign performance across channels; build attribution "
                "and a budget-optimization view."
            ),
            "key_tasks": [
                "Compute multi-touch attribution and campaign ROI",
                "Compare channel performance and test significance",
                "Build a channel scorecard and budget-allocation chart",
            ],
            "resume_bullets": [
                "Designed a marketing dashboard tracking $2M+ annual ad spend",
                "Identified a 15% budget-reallocation opportunity (~$300K/yr)",
            ],
        },
        {
            "title": "Job Market Intelligence Portfolio",
            "industry": "Career Analytics",
            "business_problem": "Analyze hiring trends and in-demand skills",
            "dataset_source": "This platform's own data",
            "dataset_url": "N/A - self-generated",
            "skills": ["python", "sql", "streamlit", "docker"],
            "difficulty": "Intermediate",
            "estimated_hours": 25,
            "description": (
                "Use this platform's collected job data to analyze hiring trends, "
                "skill demand, and geography, and publish an interactive dashboard."
            ),
            "key_tasks": [
                "Aggregate and time-series the job data with SQL",
                "Build a Streamlit dashboard of skills and geography",
                "Automate the pipeline end to end",
            ],
            "resume_bullets": [
                "Built an end-to-end platform analyzing 1000+ job listings",
                "Identified the top 10 in-demand skills across the market",
            ],
        },
    ],
    # ------------------------------------------------------------------ #
    "customer_service": [
        {
            "title": "Support Ticket & SLA Analytics Dashboard",
            "industry": "SaaS / Customer Support",
            "business_problem": "Reduce response times and SLA breaches; improve CSAT",
            "dataset_source": "Kaggle - Customer Support on Twitter",
            "dataset_url": "https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter",
            "skills": ["sql", "excel", "tableau", "csat", "sla"],
            "difficulty": "Beginner",
            "estimated_hours": 18,
            "description": (
                "Analyze a support-ticket log to measure response and resolution "
                "times, first-contact resolution, and CSAT, and flag SLA breaches "
                "by channel and agent."
            ),
            "key_tasks": [
                "Compute response/resolution time and first-contact-resolution rates",
                "Build an SLA-breach view by channel, priority, and hour of day",
                "Trend CSAT over time and by category",
                "Ship a support-ops dashboard for team leads",
            ],
            "resume_bullets": [
                "Built a support analytics dashboard over 50k+ tickets",
                "Surfaced a 30% SLA-breach reduction opportunity via peak-hour staffing",
            ],
        },
        {
            "title": "Customer Churn / Health-Score Model",
            "industry": "Customer Success",
            "business_problem": "Identify at-risk accounts before they cancel",
            "dataset_source": "Kaggle - Telco Customer Churn",
            "dataset_url": "https://www.kaggle.com/datasets/blastchar/telco-customer-churn",
            "skills": ["python", "pandas", "scikit-learn", "churn"],
            "difficulty": "Intermediate",
            "estimated_hours": 25,
            "description": (
                "Predict which customers are likely to churn and turn the model "
                "into a simple account health score a CS team can act on."
            ),
            "key_tasks": [
                "EDA and feature engineering on usage/billing signals",
                "Train and evaluate churn models (logistic regression, gradient boosting)",
                "Translate probabilities into a 0-100 health score with drivers",
                "Recommend a playbook for each risk tier",
            ],
            "resume_bullets": [
                "Built a churn model predicting at-risk accounts with 85% recall",
                "Converted model output into an actionable account health score",
            ],
        },
        {
            "title": "Ticket Auto-Categorization & Sentiment (NLP)",
            "industry": "Customer Experience",
            "business_problem": "Route tickets faster and quantify customer sentiment",
            "dataset_source": "Kaggle - Customer Support on Twitter",
            "dataset_url": "https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter",
            "skills": ["python", "nlp", "pandas", "scikit-learn"],
            "difficulty": "Intermediate",
            "estimated_hours": 22,
            "description": (
                "Classify incoming messages by topic and score sentiment so tickets "
                "route to the right queue and negative trends surface early."
            ),
            "key_tasks": [
                "Clean text and build a topic classifier",
                "Score sentiment and track it over time",
                "Surface the top negative themes as a weekly summary",
            ],
            "resume_bullets": [
                "Built an NLP classifier routing support tickets to the right queue",
                "Automated voice-of-customer sentiment reporting",
            ],
        },
    ],
    # ------------------------------------------------------------------ #
    "business_development": [
        {
            "title": "Sales Pipeline & Conversion Analytics",
            "industry": "B2B Sales",
            "business_problem": "Find where deals stall and which sources convert best",
            "dataset_source": "Kaggle - CRM Sales Opportunities",
            "dataset_url": "https://www.kaggle.com/datasets/innocentmfa/crm-sales-opportunities",
            "skills": ["sql", "excel", "tableau", "pipeline management"],
            "difficulty": "Beginner",
            "estimated_hours": 18,
            "description": (
                "Analyze a CRM funnel to measure stage-to-stage conversion, sales "
                "cycle length, and win rates by source, rep, and segment."
            ),
            "key_tasks": [
                "Compute conversion rates by pipeline stage and lead source",
                "Measure average sales-cycle length and win rate by segment",
                "Build a funnel + rep-performance dashboard",
            ],
            "resume_bullets": [
                "Analyzed a B2B sales funnel to expose a stage with 40% drop-off",
                "Built a pipeline dashboard tracking win rates by source and rep",
            ],
        },
        {
            "title": "Lead Scoring Model",
            "industry": "Sales / Growth",
            "business_problem": "Prioritize the leads most likely to convert",
            "dataset_source": "Kaggle - Lead Scoring Dataset",
            "dataset_url": "https://www.kaggle.com/datasets/ashydv/leads-dataset",
            "skills": ["python", "pandas", "scikit-learn", "lead generation"],
            "difficulty": "Intermediate",
            "estimated_hours": 24,
            "description": (
                "Score inbound leads by conversion likelihood so BD reps focus "
                "outreach where it pays off."
            ),
            "key_tasks": [
                "Engineer features from lead source, engagement, and firmographics",
                "Train a scoring model and calibrate probabilities",
                "Rank leads into A/B/C tiers with recommended actions",
            ],
            "resume_bullets": [
                "Built a lead-scoring model improving conversion focus for BD reps",
                "Ranked inbound leads into priority tiers with next-best actions",
            ],
        },
        {
            "title": "Prospect Intelligence Tracker (Hiring Signals)",
            "industry": "Business Development",
            "business_problem": "Find companies that are expanding — a buying signal",
            "dataset_source": "This platform's own job + company data",
            "dataset_url": "N/A - self-generated",
            "skills": ["python", "sql", "web scraping", "prospecting"],
            "difficulty": "Intermediate",
            "estimated_hours": 26,
            "description": (
                "Reuse this platform's scraped job and company data to flag "
                "organizations that are hiring/expanding, then build a ranked "
                "prospect list segmented by industry and size — a genuine BD tool."
            ),
            "key_tasks": [
                "Aggregate hiring volume per company over time as an expansion signal",
                "Segment prospects by industry, size, and location",
                "Rank accounts and export a CRM-ready target list",
            ],
            "resume_bullets": [
                "Built a prospecting tool that flags expanding companies from hiring data",
                "Generated a ranked, segmented target-account list for outbound BD",
            ],
        },
    ],
}


def categories() -> list[str]:
    return list(PROJECT_CATALOG.keys())
