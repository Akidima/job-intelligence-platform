from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger


class ExportEngine:
    """Exports data to various formats."""

    def __init__(self, output_dir: str = "./data/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_csv(self, data: list[dict], filename: str) -> str:
        if not data:
            return ""
        filepath = self.output_dir / f"{filename}.csv"
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        logger.info(f"[Export] CSV saved: {filepath}")
        return str(filepath)

    def export_excel(self, data: list[dict], filename: str, sheets: dict = None) -> str:
        filepath = self.output_dir / f"{filename}.xlsx"
        with pd.ExcelWriter(filepath, engine="xlsxwriter") as writer:
            if sheets:
                for sheet_name, sheet_data in sheets.items():
                    if sheet_data:
                        df = pd.DataFrame(sheet_data) if isinstance(sheet_data, list) else sheet_data
                        self._excel_safe(df).to_excel(writer, sheet_name=sheet_name, index=False)
            elif data:
                df = pd.DataFrame(data)
                self._excel_safe(df).to_excel(writer, sheet_name="Data", index=False)
        logger.info(f"[Export] Excel saved: {filepath}")
        return str(filepath)

    @staticmethod
    def _excel_safe(df: pd.DataFrame) -> pd.DataFrame:
        """Drop timezone info from datetime values; Excel can't store tz-aware
        datetimes (jobs carry tz-aware posting_date from several sources)."""
        for col in df.columns:
            if isinstance(df[col].dtype, pd.DatetimeTZDtype):
                df[col] = df[col].dt.tz_localize(None)
            elif df[col].dtype == object:
                df[col] = df[col].map(
                    lambda v: v.replace(tzinfo=None)
                    if isinstance(v, datetime) and v.tzinfo is not None else v
                )
        return df

    def export_json(self, data: list[dict] | dict, filename: str) -> str:
        filepath = self.output_dir / f"{filename}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"[Export] JSON saved: {filepath}")
        return str(filepath)

    def export_markdown(self, analytics: dict, jobs: list[dict], filename: str) -> str:
        filepath = self.output_dir / f"{filename}.md"
        lines = [
            f"# Job Intelligence Report",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        ]

        # Summary
        summary = analytics.get("summary", {})
        lines.append("## Summary")
        lines.append(f"- **Total Jobs:** {summary.get('total_jobs', 0)}")
        lines.append(f"- **Unique Companies:** {summary.get('unique_companies', 0)}")
        lines.append(f"- **Countries:** {summary.get('unique_locations', 0)}")
        lines.append(f"- **Remote Positions:** {summary.get('remote_percentage', 0)}%")
        lines.append(f"- **Visa Sponsorship:** {summary.get('visa_sponsorship_count', 0)} jobs\n")

        # Top Skills
        lines.append("## Top 20 In-Demand Skills")
        for i, skill in enumerate(analytics.get("top_skills", [])[:20], 1):
            lines.append(f"{i}. **{skill['skill']}** — {skill['count']} jobs")
        lines.append("")

        # Country Distribution
        lines.append("## Jobs by Country")
        for country, count in list(analytics.get("country_distribution", {}).items())[:15]:
            lines.append(f"- {country}: {count}")
        lines.append("")

        # Top Companies
        lines.append("## Top Hiring Companies")
        for item in analytics.get("company_hiring", [])[:10]:
            lines.append(f"- **{item['company']}**: {item['job_count']} jobs")
        lines.append("")

        # Title Distribution
        lines.append("## Most Common Job Titles")
        for item in analytics.get("title_distribution", [])[:10]:
            lines.append(f"- {item['title']}: {item['count']}")
        lines.append("")

        # Sample Jobs
        lines.append("## Sample Job Listings")
        for job in jobs[:10]:
            lines.append(f"### {job.get('title', 'N/A')}")
            lines.append(f"- **Company:** {job.get('company', 'N/A')}")
            lines.append(f"- **Location:** {job.get('country', 'N/A')}")
            lines.append(f"- **Remote:** {job.get('remote_type', 'N/A')}")
            lines.append(f"- **Source:** {job.get('source', 'N/A')}")
            lines.append(f"- **URL:** {job.get('url', 'N/A')}")
            lines.append("")

        content = "\n".join(lines)
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"[Export] Markdown saved: {filepath}")
        return str(filepath)

    def export_all(
        self,
        jobs: list[dict],
        analytics: dict,
        recommendations: list[dict] = None,
        prefix: str = None,
    ) -> dict:
        ts = prefix or datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = {}

        paths["jobs_csv"] = self.export_csv(jobs, f"jobs_{ts}")
        paths["jobs_json"] = self.export_json(jobs, f"jobs_{ts}")
        paths["analytics_json"] = self.export_json(analytics, f"analytics_{ts}")
        paths["report_md"] = self.export_markdown(analytics, jobs, f"report_{ts}")

        # Excel with multiple sheets
        sheets = {
            "Jobs": jobs,
            "Analytics_Summary": [analytics.get("summary", {})],
            "Top_Skills": analytics.get("top_skills", []),
            "Country_Distribution": [
                {"country": k, "count": v}
                for k, v in analytics.get("country_distribution", {}).items()
            ],
        }
        if recommendations:
            sheets["Recommendations"] = recommendations
        paths["full_report_xlsx"] = self.export_excel(jobs, f"full_report_{ts}", sheets)

        return paths
