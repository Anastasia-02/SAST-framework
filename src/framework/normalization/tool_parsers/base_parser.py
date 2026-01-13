from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional  # Добавляем Optional

from ...normalization.models import NormalizedIssue
from ...utils.logger import logger


class BaseSARIFParser(ABC):
    """Base class for SARIF parsers"""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    @abstractmethod
    def parse(self, sarif_data: Dict[str, Any]) -> List[NormalizedIssue]:
        """Parse SARIF data and return normalized issues"""
        pass

    def _extract_location(self, location: Dict[str, Any]) -> Dict[str, Any]:
        """Extract location information from SARIF location object"""
        result = {
            'file_path': '',
            'line_number': 0,
            'column_number': None,
            'end_line': None,
            'end_column': None,
            'snippet': None
        }

        try:
            if 'physicalLocation' in location:
                phys_loc = location['physicalLocation']

                # Extract file path
                if 'artifactLocation' in phys_loc:
                    result['file_path'] = phys_loc['artifactLocation'].get('uri', '')

                # Extract region (line/column info)
                if 'region' in phys_loc:
                    region = phys_loc['region']
                    result['line_number'] = region.get('startLine', 0)
                    result['column_number'] = region.get('startColumn')
                    result['end_line'] = region.get('endLine')
                    result['end_column'] = region.get('endColumn')
                    result['snippet'] = region.get('snippet', {}).get('text')

        except Exception as e:
            logger.warning(f"Error extracting location: {e}")

        return result

    def _extract_partial_fingerprint(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract partial fingerprint from SARIF result"""
        fingerprints = result.get('partialFingerprints', {})

        # Try different fingerprint keys used by various tools
        for key in ['primaryLocationLineHash', 'fingerprint', 'hash']:
            if key in fingerprints:
                return fingerprints[key]

        return None