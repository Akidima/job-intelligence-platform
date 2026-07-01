from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from loguru import logger

from src.skills.extractor import SkillExtractor


class AnalyticsEngine:
    """Generates hiring trend analytics from collected job data."""

    def __init__(self):
        self.skill_extractor = SkillExtractor()

    def analyze(self, jobs: list[dict]) -> dict:
        """Run full analytics pipeline on job data."""
        if not jobs:
            return {"error": "No jobs to analyze"}

        df = pd.DataFrame(jobs)
        results = {
            "summary": self._summary_stats(df),
            "top_skills": self._top_skills(jobs),
            "country_distribution": self._country_distribution(df),
            "remote_trends": self._remote_trends(df),
            "salary_analysis": self._salary_analysis(df),
            "company_hiring": self._company_hiring(df),
            "title_distribution": self._title_distribution(df),
            "skill_by_country": self._skills_by_country(jobs),
            "experience_distribution": self._experience_distribution(df),
            "source_distribution": self._source_distribution(df),
        }
        logger.info(f"[Analytics] Generated analytics for {len(jobs)} jobs")
        return results

    def _summary_stats(self, df: pd.DataFrame) -> dict:
        return {
            "total_jobs": len(df),
            "unique_companies": df["company"].nunique() if "company" in df else 0,
            "unique_locations": df["country"].nunique() if "country" in df else 0,
            "remote_percentage": round(
                (df["remote_type"] == "remote").sum() / len(df) * 100, 1
            ) if "remote_type" in df else 0,
            "visa_sponsorship_count": int(
                df["visa_sponsorship"].sum()
            ) if "visa_sponsorship" in df else 0,
        }

    def _top_skills(self, jobs: list[dict], top_n: int = 20) -> list[dict]:
        freq = self.skill_extractor.get_skill_frequency(jobs)
        return [{"skill": k, "count": v} for k, v in list(freq.items())[:top_n]]

    def _country_distribution(self, df: pd.DataFrame) -> dict:
        if "country" not in df:
            return {}
        return df["country"].value_counts().head(15).to_dict()

    def _remote_trends(self, df: pd.DataFrame) -> dict:
        if "remote_type" not in df:
            return {}
        return df["remote_type"].value_counts().to_dict()

    def _salary_analysis(self, df: pd.DataFrame) -> dict:
        result = {}
        if "salary_min" in df:
            sal = df[df["salary_min"].notna()]["salary_min"]
            if len(sal) > 0:
                result["min_salary"] = {
                    "mean": round(sal.mean(), 0),
                    "median": round(sal.median(), 0),
                    "min": int(sal.min()),
                    "max": int(sal.max()),
                }
        if "salary_max" in df:
            sal = df[df["salary_max"].notna()]["salary_max"]
            if len(sal) > 0:
                result["max_salary"] = {
                    "mean": round(sal.mean(), 0),
                    "median": round(sal.median(), 0),
                    "min": int(sal.min()),
                    "max": int(sal.max()),
                }
        return result

    def _company_hiring(self, df: pd.DataFrame, top_n: int = 20) -> list[dict]:
        if "company" not in df:
            return []
        counts = df["company"].value_counts().head(top_n)
        return [{"company": k, "job_count": int(v)} for k, v in counts.items()]

    def _title_distribution(self, df: pd.DataFrame, top_n: int = 15) -> list[dict]:
        if "normalized_title" not in df:
            if "title" not in df:
                return []
            counts = df["title"].value_counts().head(top_n)
        else:
            counts = df["normalized_title"].value_counts().head(top_n)
        return [{"title": k, "count": int(v)} for k, v in counts.items()]

    def _skills_by_country(self, jobs: list[dict]) -> dict:
        return self.skill_extractor.get_country_skill_rankings(jobs)

    def _experience_distribution(self, df: pd.DataFrame) -> dict:
        if "experience_level" not in df:
            return {}
        return df["experience_level"].value_counts().to_dict()

    def _source_distribution(self, df: pd.DataFrame) -> dict:
        if "source" not in df:
            return {}
        return df["source"].value_counts().to_dict()

    def generate_skill_gap_report(
        self, user_skills: list[str], jobs: list[dict]
    ) -> dict:
        """Compare user skills against market demands."""
        freq = self.skill_extractor.get_skill_frequency(jobs)
        user_set = {s.lower() for s in user_skills}

        required_skills = []
        missing_skills = []
        for skill, count in freq.items():
            entry = {"skill": skill, "market_demand": count}
            if skill.lower() in user_set:
                entry["status"] = "covered"
            else:
                entry["status"] = "missing"
                missing_skills.append(entry)
            required_skills.append(entry)

        coverage = len(user_skills) / max(len(freq), 1) * 100

        return {
            "user_skills": list(user_set),
            "market_top_skills": [
                {"skill": s, "count": c} for s, c in list(freq.items())[:20]
            ],
            "missing_skills": missing_skills[:10],
            "skill_coverage": round(coverage, 1),
            "recommendation": self._generate_learning_recommendations(missing_skills[:5]),
        }

    def _generate_learning_recommendations(self, missing: list[dict]) -> list[str]:
        recommendations = []
        learning_paths = {
            "sql": "Complete SQL fundamentals on Mode Analytics or SQLZoo",
            "python": "Take Python for Data Science on DataCamp or Coursera",
            "tableau": "Complete Tableau Public training and build 3 dashboards",
            "power bi": "Take Microsoft Power BI learning path on Microsoft Learn",
            "excel": "Master Excel pivot tables and advanced formulas",
            "aws": "Get AWS Cloud Practitioner certification",
            "docker": "Complete Docker fundamentals on Docker's official training",
            "git": "Learn Git branching and collaboration workflows",
            "machine learning": "Take Andrew Ng's ML course on Coursera",
            "airflow": "Build ETL pipelines with Apache Airflow",
            "dbt": "Learn analytics engineering with dbt",
            "spark": "Complete Databricks Community Edition tutorials",
        }
        for item in missing:
            skill = item["skill"]
            if skill in learning_paths:
                recommendations.append(f"{skill}: {learning_paths[skill]}")

        return recommendations
