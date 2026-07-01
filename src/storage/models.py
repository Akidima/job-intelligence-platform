from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, Index, UniqueConstraint, JSON, Enum as SAEnum,
    create_engine, inspect, text,
)
from sqlalchemy.orm import (
    DeclarativeBase, relationship, sessionmaker, Session,
)
import enum

from src.config.settings import get_settings


class Base(DeclarativeBase):
    pass


class RemoteType(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    GRADUATE = "graduate"
    UNKNOWN = "unknown"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, unique=True, index=True)
    industry = Column(String(255), nullable=True)
    website = Column(String(512), nullable=True)
    linkedin_url = Column(String(512), nullable=True)
    glassdoor_url = Column(String(512), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    employee_count = Column(Integer, nullable=True)
    visa_sponsorship = Column(Boolean, default=False)
    international_hiring = Column(Boolean, default=False)
    relocation_support = Column(Boolean, default=False)
    global_hiring_program = Column(Boolean, default=False)
    hire_from_africa = Column(Boolean, default=False)
    sponsorship_confidence = Column(Float, default=0.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    jobs = relationship("Job", back_populates="company")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    normalized_name = Column(String(100), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False, default="technical")
    subcategory = Column(String(100), nullable=True)
    frequency = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    job_skills = relationship("JobSkill", back_populates="skill")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(255), nullable=False, unique=True, index=True)
    source = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    normalized_title = Column(String(500), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    url = Column(String(1024), nullable=False)
    apply_url = Column(String(1024), nullable=True)
    description = Column(Text, nullable=True)
    description_summary = Column(Text, nullable=True)

    # Location
    country = Column(String(100), nullable=True, index=True)
    city = Column(String(100), nullable=True)
    remote_type = Column(String(20), default="unknown")

    # Compensation
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(10), nullable=True)

    # Requirements
    experience_level = Column(String(50), nullable=True, index=True)
    employment_type = Column(String(50), default="unknown")
    education_required = Column(String(100), nullable=True)

    # Role category: analytics | business_development | customer_service
    role_category = Column(String(50), nullable=True, index=True)

    # Sponsorship / International
    visa_sponsorship = Column(Boolean, default=False)
    international_hiring = Column(Boolean, default=False)
    relocation_support = Column(Boolean, default=False)

    # Dates
    posting_date = Column(DateTime, nullable=True, index=True)
    closing_date = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_validated = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_duplicate = Column(Boolean, default=False)
    is_validated = Column(Boolean, default=False)
    validation_score = Column(Float, default=0.0)

    # Metadata
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="jobs")
    job_skills = relationship("JobSkill", back_populates="job")

    __table_args__ = (
        Index("idx_job_source_external", "source", "external_id", unique=True),
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
    is_required = Column(Boolean, default=False)
    proficiency_level = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")

    __table_args__ = (
        UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
    )


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)
    industry = Column(String(100), nullable=True)
    format = Column(String(50), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, unique=True, index=True)
    industry = Column(String(100), nullable=False)
    business_problem = Column(Text, nullable=False)
    business_impact = Column(Text, nullable=True)
    difficulty = Column(String(50), nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    objectives = Column(JSON, nullable=True)
    tech_stack = Column(JSON, nullable=True)
    sql_tasks = Column(JSON, nullable=True)
    python_tasks = Column(JSON, nullable=True)
    dashboard_requirements = Column(Text, nullable=True)
    github_structure = Column(JSON, nullable=True)
    resume_bullets = Column(JSON, nullable=True)
    star_stories = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset")
    project_skills = relationship("ProjectSkill", back_populates="project")


class ProjectSkill(Base):
    __tablename__ = "project_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)

    project = relationship("Project", back_populates="project_skills")
    skill = relationship("Skill")

    __table_args__ = (
        UniqueConstraint("project_id", "skill_id", name="uq_project_skill"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    skills = Column(JSON, nullable=True)
    experience_years = Column(Integer, default=0)
    projects_completed = Column(JSON, nullable=True)
    target_role = Column(String(255), nullable=True)
    target_location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    rec_type = Column(String(50), nullable=False, index=True)
    match_score = Column(Float, default=0.0)
    missing_skills = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    job = relationship("Job")
    project = relationship("Project")


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False, unique=True, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running")
    jobs_found = Column(Integer, default=0)
    jobs_validated = Column(Integer, default=0)
    jobs_rejected = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)


# --- Database Setup ---

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=settings.app_env == "development",
        )
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_db() -> Session:
    session_factory = get_session_local()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_columns(engine)


# Lightweight, idempotent additive migrations. create_all() creates missing
# tables but never alters existing ones, so newly added columns are applied here
# without dropping data.
_ADDED_COLUMNS = {
    "jobs": {"role_category": "VARCHAR(50)"},
}


def _ensure_columns(engine):
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in existing_tables:
            continue
        present = {c["name"] for c in insp.get_columns(table)}
        for name, ddl_type in columns.items():
            if name not in present:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))
