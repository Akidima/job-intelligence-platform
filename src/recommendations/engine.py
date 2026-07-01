from __future__ import annotations

from loguru import logger

from src.skills.extractor import SkillExtractor


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
    ) -> list[dict]:
        """Recommend portfolio projects aligned with job requirements."""
        user_skills = set(s.lower() for s in user_profile.get("skills", []))

        # Find most demanded skills across jobs
        all_skill_freq = {}
        for job in jobs:
            skills = self.skill_extractor.extract_skills(
                f"{job.get('title', '')} {job.get('description', '')}"
            )
            for s in skills:
                name = s["name"].lower()
                all_skill_freq[name] = all_skill_freq.get(name, 0) + 1

        # Find skills user is missing that are in demand
        missing_demanded = {
            skill: count
            for skill, count in sorted(all_skill_freq.items(), key=lambda x: -x[1])
            if skill not in user_skills
        }

        projects = self._generate_project_recommendations(missing_demanded, user_profile)
        return projects

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

    def _generate_project_recommendations(
        self, missing_skills: dict, user_profile: dict
    ) -> list[dict]:
        """Generate specific project recommendations."""
        projects = []

        # SQL-focused project
        if "sql" in missing_skills:
            projects.append({
                "title": "E-Commerce Sales Analytics Dashboard",
                "industry": "Retail / E-Commerce",
                "business_problem": "Track sales performance, customer segments, and revenue trends",
                "dataset_source": "Kaggle - Brazilian E-Commerce by Olist",
                "dataset_url": "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
                "skills": ["sql", "python", "tableau", "excel"],
                "difficulty": "Beginner",
                "estimated_hours": 20,
                "description": (
                    "Analyze 100k+ orders across multiple dimensions: customer geography, "
                    "product categories, payment methods, and delivery performance. "
                    "Build SQL queries for cohort analysis, RFM segmentation, and revenue forecasting."
                ),
                "sql_tasks": [
                    "Create star schema data model",
                    "Write queries for monthly revenue by region",
                    "Calculate customer lifetime value",
                    "Build cohort retention analysis",
                    "Create product affinity analysis",
                ],
                "python_tasks": [
                    "ETL pipeline to clean and load data",
                    "Automated data quality checks",
                    "Statistical analysis of delivery times",
                ],
                "dashboard_tasks": [
                    "Executive summary KPIs",
                    "Sales trend line charts",
                    "Geographic heat map",
                    "Customer segmentation scatter plot",
                ],
                "resume_bullets": [
                    "Built SQL analytics pipeline processing 100k+ e-commerce transactions",
                    "Created cohort analysis revealing 23% customer retention improvement opportunity",
                    "Designed interactive dashboard reducing executive reporting time by 40%",
                ],
            })

        # Python data analysis project
        if "python" in missing_skills:
            projects.append({
                "title": "Healthcare Patient Outcome Analysis",
                "industry": "Healthcare",
                "business_problem": "Analyze patient readmission rates and identify risk factors",
                "dataset_source": "UCI ML Repository - Heart Disease Dataset",
                "dataset_url": "https://archive.ics.uci.edu/ml/datasets/Heart+Disease",
                "skills": ["python", "pandas", "scikit-learn", "statistics"],
                "difficulty": "Intermediate",
                "estimated_hours": 30,
                "description": (
                    "Analyze patient data to identify factors contributing to heart disease. "
                    "Build predictive models, create visualizations, and generate actionable "
                    "insights for healthcare providers."
                ),
                "sql_tasks": [],
                "python_tasks": [
                    "Exploratory data analysis with pandas",
                    "Feature engineering and selection",
                    "Build logistic regression and random forest models",
                    "Create statistical hypothesis tests",
                    "Generate ROC curves and confusion matrices",
                ],
                "dashboard_tasks": [
                    "Patient risk score distribution",
                    "Feature importance visualization",
                    "Model performance comparison",
                ],
                "resume_bullets": [
                    "Built ML pipeline predicting patient outcomes with 85% accuracy",
                    "Conducted statistical analysis identifying 5 key risk factors",
                    "Presented findings to stakeholders via interactive Streamlit dashboard",
                ],
            })

        # BI Dashboard project
        if any(s in missing_skills for s in ["tableau", "power bi", "looker"]):
            projects.append({
                "title": "Marketing Campaign Performance Analytics",
                "industry": "Marketing",
                "business_problem": "Measure ROI across marketing channels and optimize spend",
                "dataset_source": "Kaggle - Marketing Campaign Data",
                "dataset_url": "https://www.kaggle.com/datasets/rodsaldanha/arketing-campaign",
                "skills": ["sql", "excel", "tableau", "power bi"],
                "difficulty": "Beginner",
                "estimated_hours": 15,
                "description": (
                    "Analyze marketing campaign performance across channels. "
                    "Build KPI dashboards, attribution models, and budget optimization recommendations."
                ),
                "sql_tasks": [
                    "Multi-touch attribution queries",
                    "Campaign ROI calculations",
                    "Channel performance comparisons",
                ],
                "python_tasks": [
                    "Data cleaning and transformation",
                    "Statistical significance testing",
                ],
                "dashboard_tasks": [
                    "Channel performance scorecard",
                    "Budget allocation optimization chart",
                    "Campaign timeline visualization",
                ],
                "resume_bullets": [
                    "Designed marketing analytics dashboard tracking $2M+ annual ad spend",
                    "Identified 15% budget reallocation opportunity saving $300K annually",
                ],
            })

        # Data engineering project
        if any(s in missing_skills for s in ["airflow", "dbt", "spark", "docker"]):
            projects.append({
                "title": "Real-Time Data Pipeline with Monitoring",
                "industry": "SaaS",
                "business_problem": "Build a production-grade ETL pipeline with observability",
                "dataset_source": "GitHub - Public API data",
                "dataset_url": "https://docs.github.com/en/rest",
                "skills": ["python", "docker", "sql", "git"],
                "difficulty": "Advanced",
                "estimated_hours": 40,
                "description": (
                    "Build an end-to-end data pipeline: extract from APIs, transform with dbt, "
                    "load into PostgreSQL, and monitor with custom dashboards."
                ),
                "sql_tasks": [
                    "Create data warehouse schema",
                    "Write dbt models and tests",
                    "Build data quality checks",
                ],
                "python_tasks": [
                    "API extraction with pagination handling",
                    "Incremental loading logic",
                    "Error handling and retry logic",
                    "Unit tests with pytest",
                ],
                "dashboard_tasks": [
                    "Pipeline execution monitoring",
                    "Data freshness alerts",
                    "Quality metrics dashboard",
                ],
                "resume_bullets": [
                    "Built production ETL pipeline processing 1M+ records daily",
                    "Implemented data quality framework reducing errors by 90%",
                    "Deployed containerized pipeline with automated monitoring",
                ],
            })

        # Add general project for any user
        projects.append({
            "title": "Job Market Intelligence Portfolio",
            "industry": "Career Analytics",
            "business_problem": "Analyze job market trends and build a career intelligence platform",
            "dataset_source": "This platform's own data",
            "dataset_url": "N/A - Self-generated",
            "skills": ["python", "sql", "streamlit", "docker"],
            "difficulty": "Intermediate",
            "estimated_hours": 25,
            "description": (
                "Use this platform's collected job data to build your own analytics project. "
                "Analyze hiring trends, skill demands, and create visualizations."
            ),
            "sql_tasks": [
                "Complex aggregation queries",
                "Time-series analysis",
                "Geographic clustering",
            ],
            "python_tasks": [
                "Data pipeline automation",
                "Statistical trend analysis",
                "Streamlit app development",
            ],
            "dashboard_tasks": [
                "Interactive job market dashboard",
                "Skill demand heat map",
                "Salary trend analysis",
            ],
            "resume_bullets": [
                "Built end-to-end data platform collecting and analyzing 1000+ job listings",
                "Identified top 10 in-demand skills with 95% market coverage",
                "Created interactive dashboard used by 50+ job seekers",
            ],
        })

        return projects
