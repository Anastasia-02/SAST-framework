from typing import Dict, List, Any
from .base_parser import BaseSARIFParser
from ...normalization.models import NormalizedIssue


class SemgrepParser(BaseSARIFParser):
    """Parser for Semgrep SARIF output"""

    def __init__(self):
        super().__init__("semgrep")

    def parse(self, sarif_data: Dict[str, Any]) -> List[NormalizedIssue]:
        issues = []

        for run in sarif_data.get("runs", []):
            tool = run.get("tool", {}).get("driver", {})
            tool_name = tool.get("name", self.tool_name)

            for result in run.get("results", []):
                # Extract basic info
                rule_id = result.get("ruleId", "")
                message = result.get("message", {}).get("text", "")

                # Extract location
                locations = result.get("locations", [])
                if not locations:
                    continue

                location_info = self._extract_location(locations[0])

                # Extract partial fingerprint
                partial_fingerprint = self._extract_partial_fingerprint(result)

                # Map Semgrep severity levels
                severity_map = {
                    "error": "error",
                    "warning": "warning",
                    "info": "info"
                }
                severity = severity_map.get(result.get("level", "warning").lower(), "warning")

                # Create normalized issue
                issue = NormalizedIssue(
                    tool=tool_name,
                    rule_id=rule_id,
                    rule_name=rule_id,  # Semgrep rule IDs are descriptive
                    file_path=location_info['file_path'],
                    line_number=location_info['line_number'],
                    column_number=location_info['column_number'],
                    end_line=location_info['end_line'],
                    end_column=location_info['end_column'],
                    severity=severity,
                    message=message,
                    snippet=location_info['snippet'],
                    partial_fingerprint=partial_fingerprint,
                    raw_data=result
                )

                issues.append(issue)

        return issues