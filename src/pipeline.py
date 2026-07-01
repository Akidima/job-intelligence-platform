from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from loguru import logger

from src.scrapers.job_intelligence import JobDiscoveryEngine
from src.parsers.job_parser import JobParser
from src.validators.job_validator import JobValidator
from src.skills.extractor import SkillExtractor
from src.analytics.engine import AnalyticsEngine
from src.recommendations.engine import RecommendationEngine
from src.exports.engine import ExportEngine
from src.storage.models import (
    Job, Company, Skill, JobSkill, ExecutionLog,
    init_db, get_session_local,
)


class JobIntelligencePipeline:
    """Main orchestration pipeline that runs the full job intelligence workflow."""

    def __init__(self, user_profile: dict = None):
        self.discovery = JobDiscoveryEngine()
        self.parser = JobParser()
        self.validator = JobValidator()
        self.skill_extractor = SkillExtractor()
        self.analytics = AnalyticsEngine()
        self.recommendations = RecommendationEngine()
        self.exports = ExportEngine()
        self.user_profile = user_profile or {
            "skills": ["sql", "excel", "python"],
            "experience_years": 1,
            "projects": ["retail dashboard", "etl pipeline"],
        }
        self.run_id = str(uuid.uuid4())[:8]

    async def run(self) -> dict:
        """Execute the full pipeline."""
        start_time = datetime.now(timezone.utc)
        logger.info(f"[Pipeline] Starting run {self.run_id}")

        results = {
            "run_id": self.run_id,
            "started_at": start_time.isoformat(),
            "status": "running",
        }

        try:
            # Step 1: Discover jobs
            logger.info("[Pipeline] Step 1/7: Discovering jobs...")
            raw_jobs = await self.discovery.discover_all()
            results["raw_jobs"] = len(raw_jobs)

            # Step 2: Parse and normalize
            logger.info("[Pipeline] Step 2/7: Parsing jobs...")
            parsed_jobs = []
            for job in raw_jobs:
                parsed = self.parser.parse(job)
                if parsed:
                    parsed_jobs.append(parsed)
            results["parsed_jobs"] = len(parsed_jobs)

            # Step 3: Validate
            logger.info("[Pipeline] Step 3/7: Validating jobs...")
            valid_jobs = []
            rejected = []
            for job in parsed_jobs:
                is_valid, score, reasons = self.validator.validate(job)
                job["validation_score"] = score
                if is_valid:
                    valid_jobs.append(job)
                else:
                    rejected.append({"job": job.get("title"), "reasons": reasons})
            results["valid_jobs"] = len(valid_jobs)
            results["rejected"] = len(rejected)

            # Step 4: Extract skills
            logger.info("[Pipeline] Step 4/7: Extracting skills...")
            for job in valid_jobs:
                text = f"{job.get('title', '')} {job.get('description', '')}"
                skills = self.skill_extractor.extract_skills(text)
                job["extracted_skills"] = [s["name"] for s in skills]

            # Step 5: Store in database
            logger.info("[Pipeline] Step 5/7: Storing in database...")
            stored_count = self._store_jobs(valid_jobs)
            results["stored_jobs"] = stored_count

            # Step 6: Generate analytics
            logger.info("[Pipeline] Step 6/7: Generating analytics...")
            analytics = self.analytics.analyze(valid_jobs)
            results["analytics"] = analytics

            # Step 7: Generate recommendations
            logger.info("[Pipeline] Step 7/7: Generating recommendations...")
            job_matches = self.recommendations.match_jobs(
                self.user_profile, valid_jobs
            )
            project_recs = self.recommendations.recommend_projects(
                self.user_profile, valid_jobs
            )
            results["job_matches_top_10"] = [
                {
                    "title": m["job"].get("title"),
                    "company": m["job"].get("company"),
                    "match_score": m["match_score"],
                    "missing_skills": m["missing_skills"][:5],
                }
                for m in job_matches[:10]
            ]
            results["project_recommendations"] = [
                {
                    "title": p["title"],
                    "industry": p["industry"],
                    "difficulty": p["difficulty"],
                    "skills": p["skills"],
                }
                for p in project_recs[:5]
            ]

            # Export reports
            logger.info("[Pipeline] Exporting reports...")
            export_paths = self.exports.export_all(
                jobs=valid_jobs,
                analytics=analytics,
                recommendations=job_matches[:20],
                prefix=self.run_id,
            )
            results["exports"] = export_paths

            # Log execution
            results["status"] = "completed"
            results["completed_at"] = datetime.now(timezone.utc).isoformat()

            self._log_execution(results, start_time)

            logger.info(
                f"[Pipeline] Run {self.run_id} completed: "
                f"{results['valid_jobs']} jobs, "
                f"{len(results.get('job_matches_top_10', []))} matches"
            )

        except Exception as e:
            logger.error(f"[Pipeline] Run {self.run_id} failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            self._log_execution(results, start_time)

        return results

    def _store_jobs(self, jobs: list[dict]) -> int:
        """Store validated jobs in the database."""
        session_factory = get_session_local()
        session = session_factory()
        count = 0

        try:
            for job_data in jobs:
                # Check for existing
                existing = session.query(Job).filter_by(
                    external_id=job_data["external_id"]
                ).first()
                if existing:
                    continue

                # Get or create company
                company = None
                if job_data.get("company"):
                    normalized = job_data["company"].lower().strip()
                    company = session.query(Company).filter_by(
                        normalized_name=normalized
                    ).first()
                    if not company:
                        company = Company(
                            name=job_data["company"],
                            normalized_name=normalized,
                        )
                        session.add(company)
                        session.flush()

                # Create job
                job = Job(
                    external_id=job_data["external_id"],
                    source=job_data["source"],
                    title=job_data["title"],
                    normalized_title=job_data.get("normalized_title", ""),
                    company_id=company.id if company else None,
                    url=job_data["url"],
                    apply_url=job_data.get("apply_url"),
                    description=job_data.get("description", ""),
                    description_summary=job_data.get("description_summary", ""),
                    country=job_data.get("country"),
                    city=job_data.get("city"),
                    remote_type=job_data.get("remote_type", "unknown"),
                    salary_min=job_data.get("salary_min"),
                    salary_max=job_data.get("salary_max"),
                    salary_currency=job_data.get("salary_currency"),
                    experience_level=job_data.get("experience_level"),
                    employment_type=job_data.get("employment_type", "unknown"),
                    visa_sponsorship=job_data.get("visa_sponsorship", False),
                    international_hiring=job_data.get("international_hiring", False),
                    relocation_support=job_data.get("relocation_support", False),
                    posting_date=job_data.get("posting_date"),
                    validation_score=job_data.get("validation_score", 0),
                    is_validated=True,
                )
                session.add(job)
                count += 1

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"[Pipeline] Database storage failed: {e}")
        finally:
            session.close()

        return count

    def _log_execution(self, results: dict, start_time: datetime):
        """Log execution to database."""
        try:
            session_factory = get_session_local()
            session = session_factory()
            log = ExecutionLog(
                run_id=self.run_id,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
                status=results.get("status", "unknown"),
                jobs_found=results.get("raw_jobs", 0),
                jobs_validated=results.get("valid_jobs", 0),
                jobs_rejected=results.get("rejected", 0),
                metadata_json=results,
            )
            session.add(log)
            session.commit()
            session.close()
        except Exception as e:
            logger.error(f"[Pipeline] Failed to log execution: {e}")
