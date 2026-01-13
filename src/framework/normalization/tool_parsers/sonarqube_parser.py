from typing import Dict, List, Any
from .base_parser import BaseSARIFParser
from ...normalization.models import NormalizedIssue


class SonarQubeParser(BaseSARIFParser):
    """Parser for SonarQube SARIF output"""

    def __init__(self):
        super().__init__("sonarqube")

    def parse(self, sarif_data: Dict[str, Any]) -> List[NormalizedIssue]:
        issues = []

        for run in sarif_data.get("runs", []):
            # SonarQube often includes rule metadata
            rules = {}
            for rule in run.get("tool", {}).get("driver", {}).get("rules", []):
                if 'id' in rule:
                    rules[rule['id']] = rule

            for result in run.get("results", []):
                rule_id = result.get("ruleId", "")

                # Get rule details
                rule_info = rules.get(rule_id, {})
                rule_name = rule_info.get("name", rule_id)

                # Extract message - SonarQube might have markdown messages
                message_obj = result.get("message", {})
                message = message_obj.get("text", "")
                if not message and 'markdown' in message_obj:
                    message = message_obj['markdown']

                # Extract location
                locations = result.get("locations", [])
                if not locations:
                    continue

                location_info = self._extract_location(locations[0])

                # Extract partial fingerprint
                partial_fingerprint = self._extract_partial_fingerprint(result)

                # Map SonarQube severities
                severity_map = {
                    "BLOCKER": "error",
                    "CRITICAL": "error",
                    "MAJOR": "warning",
                    "MINOR": "info",
                    "INFO": "info"
                }
                severity = severity_map.get(result.get("level", "MAJOR"), "warning")

                # Extract properties for additional info
                properties = result.get("properties", {})
                cwe_id = properties.get('cwe') or properties.get('security-severity')

                issue = NormalizedIssue(
                    id=f"sonarqube_{rule_id}_{location_info['file_path']}:{location_info['line_number']}",
                    tool="sonarqube",
                    rule_id=rule_id,
                    rule_name=rule_name,
                    file_path=location_info['file_path'],
                    line_number=location_info['line_number'],
                    column_number=location_info['column_number'],
                    end_line=location_info['end_line'],
                    end_column=location_info['end_column'],
                    severity=severity,
                    message=message,
                    snippet=location_info['snippet'],
                    category=properties.get('subcategory'),
                    cwe_id=cwe_id,
                    partial_fingerprint=partial_fingerprint,
                    raw_data=result
                )

                issues.append(issue)

        return issues