from __future__ import annotations

import json
import re

from loguru import logger

from src.config.settings import get_settings
from src.skills.extractor import (
    SkillExtractor, TECHNICAL_SKILLS, BUSINESS_SKILLS, SKILL_CATEGORIES,
)


_SYSTEM_PROMPT = (
    "You extract professional skills, tools, and competencies from a job "
    "posting. Return ONLY a compact JSON object of the form "
    '{"skills": [{"name": "python", "category": "technical", '
    '"is_required": true}]}. Use lowercase skill names. category must be one '
    "of: technical, business, soft. Include hard tools (e.g. sql, salesforce, "
    "zendesk), domain competencies (e.g. lead generation, csat), and key soft "
    "skills. Do not invent skills that are not implied by the text."
)


class LLMSkillExtractor(SkillExtractor):
    """LLM-assisted skill extractor over any OpenAI-compatible endpoint.

    Subclasses :class:`SkillExtractor` so it keeps the full interface (frequency
    rankings, etc.) and, crucially, a working regex-based fallback. If the LLM
    is unreachable, the client library is missing, or the response can't be
    parsed, it transparently falls back to the regex extractor — the pipeline
    never breaks because an LLM is misconfigured or offline.
    """

    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self._cache: dict[str, list[dict]] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # lazy: optional dependency
            self._client = OpenAI(
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key or "not-needed",
                timeout=30.0,
                max_retries=1,
            )
        return self._client

    def extract_skills(self, text: str) -> list[dict]:
        if not text:
            return []
        key = text.strip()
        if key in self._cache:
            return self._cache[key]

        try:
            skills = self._parse(self._call_llm(text))
            if not skills:
                raise ValueError("empty LLM result")
        except Exception as e:
            logger.debug(f"[LLMSkillExtractor] falling back to regex: {e}")
            skills = super().extract_skills(text)

        self._cache[key] = skills
        return skills

    def _call_llm(self, text: str) -> str:
        resp = self._get_client().chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text[:6000]},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    def _parse(self, content: str) -> list[dict]:
        """Parse the model's JSON into the SkillExtractor result shape."""
        data = self._loads(content)
        raw = data.get("skills", data) if isinstance(data, dict) else data
        if not isinstance(raw, list):
            return []

        results: list[dict] = []
        seen: set[str] = set()
        for item in raw:
            name = (item.get("name") if isinstance(item, dict) else str(item) or "").strip().lower()
            if not name or name in seen:
                continue
            seen.add(name)
            category = None
            if isinstance(item, dict):
                category = item.get("category")
            category = category or SKILL_CATEGORIES.get(name) or self._default_category(name)
            results.append({
                "name": name,
                "category": category,
                "is_required": bool(item.get("is_required")) if isinstance(item, dict) else False,
                "count": 1,
            })
        return results

    @staticmethod
    def _default_category(name: str) -> str:
        if name in TECHNICAL_SKILLS:
            return "technical"
        if name in BUSINESS_SKILLS:
            return "business"
        return "soft"

    @staticmethod
    def _loads(content: str):
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            # Some models wrap JSON in prose or code fences; grab the object.
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise


def get_skill_extractor() -> SkillExtractor:
    """Return the LLM extractor when configured, else the regex extractor."""
    settings = get_settings()
    if settings.llm_enabled():
        logger.info(
            f"[Skills] LLM extraction enabled via {settings.llm_base_url} "
            f"(model={settings.llm_model})"
        )
        return LLMSkillExtractor()
    return SkillExtractor()
