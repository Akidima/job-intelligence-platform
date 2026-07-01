from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from loguru import logger

from src.storage.models import Skill, JobSkill, get_session_local


# Comprehensive skill taxonomy
TECHNICAL_SKILLS = {
    # Programming Languages
    "python", "r", "sql", "javascript", "typescript", "java", "scala",
    "sas", "matlab", "go", "rust", "c++", "c#", "vba", "perl",
    # Databases
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "oracle", "sql server", "mssql", "snowflake", "databricks",
    "bigquery", "redshift", "dynamo db", "dynamodb", "cassandra",
    "neo4j", "cockroachdb",
    # Cloud
    "aws", "gcp", "google cloud", "azure", "cloud",
    # BI Tools
    "tableau", "power bi", "powerbi", "looker", "qlik",
    "superset", "metabase", "mode", "google data studio",
    "microstrategy", "sisense", "domo",
    # Data Tools
    "excel", "google sheets", "spreadsheets",
    "dbt", "airflow", "prefect", "dagster", "luigi",
    "spark", "hadoop", "kafka", "flink", "storm",
    "docker", "kubernetes", "k8s", "terraform",
    "git", "github", "gitlab", "bitbucket",
    # ML/AI
    "machine learning", "deep learning", "nlp",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    "xgboost", "lightgbm", "catboost",
    "jupyter", "jupyter notebook", "google colab",
    "mlflow", "kubeflow", "weights & biases",
    # Stats
    "statistics", "regression", "hypothesis testing",
    "a/b testing", "experiment design", "bayesian",
    # ETL
    "etl", "data pipeline", "data warehouse",
    "talend", "informatica", "ssis", "fivetran", "stitch",
    "segment", "mixpanel", "amplitude",
    # APIs
    "rest api", "graphql", "api", "web scraping",
    # Version Control & DevOps
    "ci/cd", "jenkins", "github actions",
    "linux", "bash", "shell scripting",
}

SOFT_SKILLS = {
    "communication", "stakeholder management", "presentation",
    "problem solving", "critical thinking", "teamwork",
    "agile", "scrum", "leadership", "time management",
    "analytical thinking", "attention to detail",
    "cross-functional collaboration", "storytelling",
    "project management", "self-motivated", "adaptable",
}

# Customer service / success / support and business development / sales.
BUSINESS_SKILLS = {
    # CRM & support/sales tooling
    "salesforce", "hubspot", "zendesk", "intercom", "freshdesk",
    "servicenow", "pipedrive", "zoho", "gong", "outreach", "salesloft",
    "zoominfo", "apollo", "live chat", "help scout", "jira service management",
    # Support / CX concepts & metrics
    "csat", "nps", "sla", "customer onboarding", "customer retention",
    "customer success", "customer support", "customer service",
    "customer experience", "ticketing", "escalation management",
    "first response time", "voice of customer", "churn",
    # Business development / sales concepts
    "crm", "lead generation", "lead gen", "prospecting", "cold calling",
    "cold outreach", "cold email", "outbound", "inbound", "b2b sales",
    "pipeline management", "account management", "upselling", "cross-selling",
    "negotiation", "demand generation", "sales development", "quota attainment",
}

SKILL_CATEGORIES = {
    "sql": "database", "postgresql": "database", "mysql": "database",
    "snowflake": "database", "bigquery": "database", "redshift": "database",
    "databricks": "database", "mongodb": "database", "redis": "database",
    "excel": "spreadsheet", "google sheets": "spreadsheet",
    "python": "programming", "r": "programming", "javascript": "programming",
    "sas": "programming", "java": "programming",
    "tableau": "bi_tool", "power bi": "bi_tool", "looker": "bi_tool",
    "mode": "bi_tool", "metabase": "bi_tool",
    "aws": "cloud", "gcp": "cloud", "azure": "cloud", "google cloud": "cloud",
    "docker": "devops", "kubernetes": "devops", "git": "devops",
    "airflow": "orchestration", "dbt": "transformation",
    "spark": "big_data", "hadoop": "big_data", "kafka": "streaming",
    "pandas": "data_analysis", "numpy": "data_analysis",
    "machine learning": "ml", "deep learning": "ml",
    "tensorflow": "ml", "pytorch": "ml", "scikit-learn": "ml",
    # Business / CRM / support
    "salesforce": "crm", "hubspot": "crm", "pipedrive": "crm", "zoho": "crm",
    "zendesk": "support_tool", "intercom": "support_tool",
    "freshdesk": "support_tool", "help scout": "support_tool",
    "csat": "cx_metric", "nps": "cx_metric", "sla": "cx_metric",
    "lead generation": "sales", "prospecting": "sales", "cold outreach": "sales",
    "pipeline management": "sales", "account management": "sales",
    "customer success": "customer_success", "customer support": "customer_support",
}


class SkillExtractor:
    """Extracts skills from job descriptions using pattern matching and NLP."""

    def __init__(self):
        self.all_skills = TECHNICAL_SKILLS | SOFT_SKILLS | BUSINESS_SKILLS
        self._compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        for skill in self.all_skills:
            pattern = re.compile(
                r"\b" + re.escape(skill) + r"\b",
                re.IGNORECASE,
            )
            self._compiled_patterns[skill] = pattern

    def extract_skills(self, text: str) -> list[dict]:
        """
        Extract skills from text.
        Returns list of {"name": str, "category": str, "is_required": bool}.
        """
        if not text:
            return []

        text_lower = text.lower()
        found = []

        for skill, pattern in self._compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                is_required = self._check_if_required(skill, text_lower)
                if skill in TECHNICAL_SKILLS:
                    default_category = "technical"
                elif skill in BUSINESS_SKILLS:
                    default_category = "business"
                else:
                    default_category = "soft"
                category = SKILL_CATEGORIES.get(skill, default_category)
                found.append({
                    "name": skill,
                    "category": category,
                    "is_required": is_required,
                    "count": len(matches),
                })

        # Deduplicate and sort by count
        seen = set()
        unique = []
        for item in sorted(found, key=lambda x: -x["count"]):
            if item["name"] not in seen:
                seen.add(item["name"])
                unique.append(item)

        return unique

    def _check_if_required(self, skill: str, text: str) -> bool:
        """Check if skill is in a 'required' section."""
        required_patterns = [
            rf"required.*?{re.escape(skill)}",
            rf"must have.*?{re.escape(skill)}",
            rf"essential.*?{re.escape(skill)}",
            rf"minimum.*?{re.escape(skill)}",
            rf"qualifications.*?{re.escape(skill)}",
        ]
        for pattern in required_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def get_skill_frequency(self, jobs: list[dict]) -> dict:
        """Get skill frequency across all jobs."""
        counter = Counter()
        for job in jobs:
            skills = self.extract_skills(
                f"{job.get('title', '')} {job.get('description', '')}"
            )
            for skill in skills:
                counter[skill["name"]] += 1
        return dict(counter.most_common(50))

    def get_country_skill_rankings(self, jobs: list[dict]) -> dict:
        """Get skill rankings by country."""
        country_counter: dict[str, Counter] = {}
        for job in jobs:
            country = job.get("country", "Unknown")
            if country not in country_counter:
                country_counter[country] = Counter()
            skills = self.extract_skills(
                f"{job.get('title', '')} {job.get('description', '')}"
            )
            for skill in skills:
                country_counter[country][skill["name"]] += 1

        return {
            country: dict(counter.most_common(20))
            for country, counter in country_counter.items()
        }

    def get_industry_skill_rankings(self, jobs: list[dict]) -> dict:
        """Get skill rankings by industry."""
        industry_counter: dict[str, Counter] = {}
        for job in jobs:
            industry = job.get("industry", "Unknown")
            if industry not in industry_counter:
                industry_counter[industry] = Counter()
            skills = self.extract_skills(
                f"{job.get('title', '')} {job.get('description', '')}"
            )
            for skill in skills:
                industry_counter[industry][skill["name"]] += 1

        return {
            industry: dict(counter.most_common(15))
            for industry, counter in industry_counter.items()
        }

    def get_emerging_technologies(self, jobs: list[dict], threshold: float = 0.1) -> list[str]:
        """Identify emerging technologies (mentioned in >threshold% of jobs)."""
        freq = self.get_skill_frequency(jobs)
        total = len(jobs) if jobs else 1
        return [
            skill for skill, count in freq.items()
            if count / total >= threshold
        ]
