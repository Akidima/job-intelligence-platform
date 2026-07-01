from __future__ import annotations

from collections import Counter

from loguru import logger

from src.skills.extractor import SkillExtractor
from src.recommendations.catalog import PROJECT_CATALOG


class RecommendationEngine:
    """Matches candidate profiles to jobs and recommends projects."""

    def __init__(self):
        self.skill_extractor = SkillExtractor()

    def match_jobs(
        self,
        user_profile: dict,
        jobs: list[dict],
    ) -> list[dict]:
        """Match a candidate profile against available jobs."""
        user_skills = set(s.lower() for s in user_profile.get("skills", []))
        user_experience = user_profile.get("experience_years", 0)

        ranked = []
        for job in jobs:
            job_skills = self.skill_extractor.extract_skills(
                f"{job.get('title', '')} {job.get('description', '')}"
            )
            job_skill_names = {s["name"].lower() for s in job_skills}

            # Calculate match score
            if not job_skill_names:
                match_score = 0.5
            else:
                overlap = len(user_skills & job_skill_names)
                match_score = overlap / max(len(job_skill_names), 1)

            # Boost for experience level match
            exp_level = (job.get("experience_level", "") or "").lower()
            if "entry" in exp_level or "junior" in exp_level or "graduate" in exp_level:
                if user_experience <= 3:
                    match_score = min(match_score + 0.1, 1.0)

            # Boost for visa sponsorship
            if job.get("visa_sponsorship"):
                match_score = min(match_score + 0.05, 1.0)

            missing = job_skill_names - user_skills
            strengths = job_skill_names & user_skills

            # Estimate application success
            success_prob = match_score * 0.7 + (0.3 if job.get("visa_sponsorship") else 0)

            ranked.append({
                "job": job,
                "match_score": round(match_score * 100, 1),
                "missing_skills": sorted(missing),
                "strengths": sorted(strengths),
                "interview_readiness": round(min(match_score * 100 + 20, 100), 1),
                "application_success_prob": round(min(success_prob * 100, 100), 1),
                "resume_improvements": self._resume_improvements(missing, job),
                "learning_recs": self._learning_for_job(missing),
            })

        # Sort by match score
        ranked.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked

    def recommend_projects(
        self,
        user_profile: dict,
        jobs: list[dict],
        role_category: str | None = None,
    ) -> list[dict]:
        """Recommend portfolio projects, tailored to the relevant role category.

        The category is taken from ``role_category`` if given, else the user's
        ``target_role``, else inferred from the discovered jobs (most common
        category first). Each project is annotated with the skills the user
        already has, the skills they'd build, and how in-demand those skills are
        across the current jobs.
        """
        user_skills = set(s.lower() for s in user_profile.get("skills", []))

        # In-demand skills across the current jobs (for annotation/ranking)
        skill_demand: dict[str, int] = {}
        for job in jobs:
            for s in self.skill_extractor.extract_skills(
                f"{job.get('title', '')} {job.get('description', '')}"
            ):
                name = s["name"].lower()
                skill_demand[name] = skill_demand.get(name, 0) + 1

        projects: list[dict] = []
        for category in self._categories_for(jobs, role_category, user_profile):
            for template in PROJECT_CATALOG.get(category, []):
                projects.append(
                    self._annotate_project(template, category, user_skills, skill_demand)
                )

        # Most market-relevant projects first
        projects.sort(key=lambda p: p["market_demand_score"], reverse=True)
        return projects

    def _categories_for(
        self, jobs: list[dict], role_category: str | None, user_profile: dict
    ) -> list[str]:
        """Decide which role categories to recommend projects for."""
        if role_category and role_category in PROJECT_CATALOG:
            return [role_category]
        target = user_profile.get("target_role")
        if target in PROJECT_CATALOG:
            return [target]
        # Infer from the jobs, most common category first
        freq = Counter(j.get("role_category") for j in jobs if j.get("role_category"))
        ordered = [c for c, _ in freq.most_common() if c in PROJECT_CATALOG]
        return ordered or ["analytics"]

    def _annotate_project(
        self, template: dict, category: str, user_skills: set, skill_demand: dict
    ) -> dict:
        project = dict(template)
        project["role_category"] = category
        proj_skills = {s.lower() for s in template.get("skills", [])}
        project["skills_you_have"] = sorted(proj_skills & user_skills)
        project["skills_youll_build"] = sorted(proj_skills - user_skills)
        # How strongly this project's skills show up in the live job set
        project["market_demand_score"] = sum(skill_demand.get(s, 0) for s in proj_skills)
        return project

    def _resume_improvements(self, missing_skills: set, job: dict) -> list[str]:
        improvements = []
        if missing_skills:
            improvements.append(
                f"Add these skills to your resume if you have them: {', '.join(list(missing_skills)[:5])}"
            )
        if not job.get("visa_sponsorship"):
            improvements.append(
                "Consider highlighting your ability to work independently across time zones"
            )
        improvements.append(
            "Tailor your resume keywords to match this job description"
        )
        return improvements

    def _learning_for_job(self, missing_skills: set) -> list[str]:
        recs = []
        learning_map = {
            "sql": "Practice complex queries on LeetCode or HackerRank",
            "python": "Build 3 data analysis projects with pandas",
            "tableau": "Create a public Tableau portfolio with 5+ dashboards",
            "power bi": "Complete Microsoft's PL-300 learning path",
            "excel": "Master advanced formulas and pivot tables",
            "docker": "Containerize a data pipeline project",
            "git": "Practice branching and PR workflows",
            "spark": "Build a distributed data processing project",
            "airflow": "Create an ETL DAG with error handling",
            "dbt": "Build a dbt project with tests and documentation",
        }
        for skill in list(missing_skills)[:5]:
            if skill in learning_map:
                recs.append(f"{skill}: {learning_map[skill]}")
        return recs
