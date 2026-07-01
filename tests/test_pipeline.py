#!/usr/bin/env python3
"""Tests for the job intelligence pipeline."""

import pytest
import asyncio
from datetime import datetime, timezone


def test_parser_cleans_title():
    from src.parsers.job_parser import JobParser
    parser = JobParser()
    assert parser._clean_title("Data Analyst - Remote") == "Data Analyst"
    assert parser._clean_title("Junior Python Developer (Remote)") == "Junior Python Developer"


def test_parser_normalizes_title():
    from src.parsers.job_parser import JobParser
    parser = JobParser()
    assert parser._normalize_title("Junior Data Analyst") == "data analyst"
    assert parser._normalize_title("Senior Python Developer") == "python developer"


def test_validator_rejects_scam():
    from src.validators.job_validator import JobValidator
    validator = JobValidator()
    is_valid, score, reasons = validator.validate({
        "title": "Make Money Fast - Work From Home",
        "description": "Earn $5000 per day with no experience needed",
        "url": "https://example.com",
    })
    assert not is_valid
    assert "scam_indicators" in reasons


def test_validator_accepts_valid_job():
    from src.validators.job_validator import JobValidator
    validator = JobValidator()
    is_valid, score, reasons = validator.validate({
        "title": "Data Analyst",
        "company": "Google",
        "url": "https://careers.google.com/jobs/123",
        "description": "Analyze data using SQL and Python",
        "country": "United States",
        "posting_date": datetime.now(timezone.utc),
    })
    assert is_valid or score > 0.5


def test_skill_extractor_finds_skills():
    from src.skills.extractor import SkillExtractor
    extractor = SkillExtractor()
    skills = extractor.extract_skills(
        "Looking for Python, SQL, and Tableau experience"
    )
    names = [s["name"] for s in skills]
    assert "python" in names
    assert "sql" in names
    assert "tableau" in names


def test_skill_extractor_categorizes():
    from src.skills.extractor import SkillExtractor
    extractor = SkillExtractor()
    skills = extractor.extract_skills("Need Python, SQL, and communication skills")
    for s in skills:
        if s["name"] == "python":
            assert s["category"] == "programming"
        if s["name"] == "sql":
            assert s["category"] == "database"


def test_analytics_summary():
    from src.analytics.engine import AnalyticsEngine
    engine = AnalyticsEngine()
    jobs = [
        {"title": "Data Analyst", "company": "Google", "country": "US", "remote_type": "remote",
         "visa_sponsorship": True, "experience_level": "Entry-Level", "source": "linkedin",
         "description": "Python SQL Tableau"},
        {"title": "BI Developer", "company": "Meta", "country": "UK", "remote_type": "hybrid",
         "visa_sponsorship": False, "experience_level": "Entry-Level", "source": "greenhouse",
         "description": "SQL Power BI Excel"},
    ]
    result = engine.analyze(jobs)
    assert result["summary"]["total_jobs"] == 2
    assert result["summary"]["unique_companies"] == 2


def test_recommendation_engine():
    from src.recommendations.engine import RecommendationEngine
    engine = RecommendationEngine()
    user = {"skills": ["sql", "python", "excel"], "experience_years": 1}
    jobs = [
        {"title": "Data Analyst", "company": "Google", "description": "SQL Python Tableau Excel",
         "experience_level": "Entry-Level", "visa_sponsorship": True},
    ]
    matches = engine.match_jobs(user, jobs)
    assert len(matches) > 0
    assert matches[0]["match_score"] > 0


def test_export_csv(tmp_path):
    from src.exports.engine import ExportEngine
    engine = ExportEngine(output_dir=str(tmp_path))
    data = [{"name": "test", "value": 1}]
    path = engine.export_csv(data, "test")
    assert path
    assert (tmp_path / "test.csv").exists()


def test_job_fingerprint():
    from src.scrapers.base import JobResult
    job1 = JobResult(source="test", external_id="123", title="Analyst", company="Google", url="http://x")
    job2 = JobResult(source="test", external_id="123", title="Analyst", company="Google", url="http://x")
    assert job1.fingerprint == job2.fingerprint


def test_classify_role_categories():
    from src.config.settings import get_settings
    s = get_settings()
    assert s.classify_role("Junior Data Analyst") == "analytics"
    assert s.classify_role("Customer Service Representative") == "customer_service"
    assert s.classify_role("Business Development Analyst") == "business_development"
    assert s.classify_role("Sales Development Representative") == "business_development"
    assert s.classify_role("Plumber") is None


def _job(title, level="Entry-Level", country="Remote"):
    from src.scrapers.base import JobResult
    return JobResult(source="t", external_id=title, title=title, company="ACME",
                     url="https://x/" + title, experience_level=level, country=country)


def test_filter_keeps_customer_service_and_business_development():
    from src.scrapers.job_intelligence import JobDiscoveryEngine
    engine = JobDiscoveryEngine()
    kept = engine._filter_entry_level([
        _job("Customer Service Representative"),
        _job("Customer Success Associate"),
        _job("Business Development Analyst"),
    ])
    titles = {j.title for j in kept}
    assert "Customer Service Representative" in titles
    assert "Business Development Analyst" in titles
    # category is tagged for downstream analytics
    assert all(j.role_category for j in kept)


def test_filter_drops_senior_and_irrelevant():
    from src.scrapers.job_intelligence import JobDiscoveryEngine
    engine = JobDiscoveryEngine()
    kept = engine._filter_entry_level([
        _job("Senior Data Engineer", level="Senior"),
        _job("Head of Customer Service"),
        _job("Warehouse Operative"),
        _job("Graphic Designer"),
    ])
    assert kept == []


def test_filter_sets_role_category_on_jobresult():
    from src.scrapers.job_intelligence import JobDiscoveryEngine
    engine = JobDiscoveryEngine()
    kept = engine._filter_entry_level([_job("Customer Success Associate")])
    assert kept and kept[0].role_category == "customer_service"


def test_parser_passes_role_category_through():
    from src.parsers.job_parser import JobParser
    from src.scrapers.base import JobResult
    jr = JobResult(source="t", external_id="1", title="Business Development Analyst",
                   company="ACME", url="https://x", role_category="business_development")
    parsed = JobParser().parse(jr)
    assert parsed["role_category"] == "business_development"


def test_skill_extractor_finds_business_skills():
    from src.skills.extractor import SkillExtractor
    ex = SkillExtractor()
    names = {s["name"] for s in ex.extract_skills(
        "Experience with Salesforce and Zendesk; strong lead generation and CSAT focus"
    )}
    assert "salesforce" in names
    assert "zendesk" in names
    assert "lead generation" in names


def test_get_skill_extractor_defaults_to_regex():
    from src.skills.llm_extractor import get_skill_extractor
    from src.skills.extractor import SkillExtractor
    # LLM is disabled by default -> plain regex extractor
    assert type(get_skill_extractor()) is SkillExtractor


def test_llm_extractor_falls_back_to_regex_on_error(monkeypatch):
    from src.skills.llm_extractor import LLMSkillExtractor
    ex = LLMSkillExtractor()

    def boom(_text):
        raise RuntimeError("LLM unreachable")

    monkeypatch.setattr(ex, "_call_llm", boom)
    names = {s["name"] for s in ex.extract_skills("Looking for Python and SQL")}
    assert "python" in names and "sql" in names  # regex fallback still works


def test_llm_extractor_parses_json(monkeypatch):
    from src.skills.llm_extractor import LLMSkillExtractor
    ex = LLMSkillExtractor()
    canned = '{"skills":[{"name":"Salesforce","category":"business","is_required":true},{"name":"CSAT"}]}'
    monkeypatch.setattr(ex, "_call_llm", lambda _text: canned)
    skills = ex.extract_skills("a customer success role")
    by_name = {s["name"]: s for s in skills}
    assert "salesforce" in by_name  # names lowercased
    assert "csat" in by_name
    assert by_name["salesforce"]["is_required"] is True


def test_recommend_projects_is_role_aware():
    from src.recommendations.engine import RecommendationEngine
    engine = RecommendationEngine()
    user = {"skills": ["excel"]}
    # Customer service jobs -> customer service projects
    cs_jobs = [{"title": "Customer Support Specialist", "description": "zendesk csat",
                "role_category": "customer_service"}]
    cs = engine.recommend_projects(user, cs_jobs)
    assert cs and all(p["role_category"] == "customer_service" for p in cs)
    # Explicit business_development override
    bd = engine.recommend_projects(user, [], role_category="business_development")
    assert bd and all(p["role_category"] == "business_development" for p in bd)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
