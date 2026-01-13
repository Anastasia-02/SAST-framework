import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import NormalizedResult, NormalizedIssue
from .tool_parsers.semgrep_parser import SemgrepParser
from .tool_parsers.sonarqube_parser import SonarQubeParser
from ..utils.logger import logger


class SARIFNormalizer:
    """Main normalizer for converting SARIF files to normalized format"""

    # Registry of parsers for different tools
    _parsers = {
        "semgrep": SemgrepParser(),
        "sonarqube": SonarQubeParser(),
        # Will add more parsers as we implement them
    }

    def __init__(self):
        self._default_parser = SemgrepParser()  # Fallback parser

    def register_parser(self, tool_name: str, parser):
        """Register a parser for a specific tool"""
        self._parsers[tool_name] = parser
        logger.info(f"Registered parser for tool: {tool_name}")

    def normalize_file(self, sarif_file: Path, tool_name: str,
                       project_name: str, duration: Optional[float] = None) -> NormalizedResult:
        """Normalize a SARIF file and return normalized result"""

        try:
            # Load SARIF data
            with open(sarif_file, 'r', encoding='utf-8') as f:
                sarif_data = json.load(f)

            # Parse SARIF data
            issues = self.normalize_data(sarif_data, tool_name)

            # Create normalized result
            result = NormalizedResult(
                tool=tool_name,
                project=project_name,
                duration_seconds=duration,
                issues=issues
            )

            logger.info(f"Normalized {len(issues)} issues from {tool_name} for project {project_name}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {sarif_file}: {e}")
            return NormalizedResult(
                tool=tool_name,
                project=project_name,
                issues=[]
            )
        except Exception as e:
            logger.error(f"Failed to normalize file {sarif_file}: {e}")
            # Return empty result on error
            return NormalizedResult(
                tool=tool_name,
                project=project_name,
                issues=[]
            )

    def normalize_data(self, sarif_data: Dict[str, Any], tool_name: str) -> List[NormalizedIssue]:
        """Normalize SARIF data dictionary"""

        # Get appropriate parser
        parser = self._parsers.get(tool_name, self._default_parser)

        try:
            # Validate basic SARIF structure
            if not isinstance(sarif_data, dict):
                raise ValueError("SARIF data must be a dictionary")

            if "version" not in sarif_data:
                logger.warning(f"SARIF data missing version field, tool: {tool_name}")

            # Parse with the selected parser
            issues = parser.parse(sarif_data)

            # Post-process issues
            self._post_process_issues(issues, tool_name)

            return issues

        except Exception as e:
            logger.error(f"Error parsing SARIF data from {tool_name}: {e}")
            return []

    def _post_process_issues(self, issues: List[NormalizedIssue], tool_name: str):
        """Post-process issues after parsing"""

        for issue in issues:
            # Clean up file paths (remove any container paths)
            if issue.file_path.startswith('/'):
                # Try to extract relative path
                parts = issue.file_path.split('/')
                if 'src' in parts:
                    idx = parts.index('src')
                    issue.file_path = '/'.join(parts[idx + 1:])

            # Ensure severity is lowercase
            issue.severity = issue.severity.lower()