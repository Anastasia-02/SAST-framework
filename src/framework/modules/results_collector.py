import json
from pathlib import Path
from typing import Dict, List, Optional
from ..utils.logger import logger


class ResultsCollector:
    """Collect and manage test results"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.raw_dir = output_dir / "raw"
        self.normalized_dir = output_dir / "normalized"

        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.normalized_dir.mkdir(parents=True, exist_ok=True)

    def save_raw_result(self, project_name: str, tool_name: str,
                        sarif_data: Dict, output_path: Path) -> Path:
        """Save raw SARIF result"""

        project_dir = self.raw_dir / project_name
        project_dir.mkdir(exist_ok=True)

        # Create filename
        filename = f"{tool_name}.sarif"
        filepath = project_dir / filename

        # Save SARIF file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sarif_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved raw result to {filepath}")
        return filepath

    def load_raw_result(self, filepath: Path) -> Optional[Dict]:
        """Load raw SARIF result from file"""

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load raw result from {filepath}: {e}")
            return None

    def save_normalized_result(self, normalized_data: Dict,
                               project_name: str, tool_name: str) -> Path:
        """Save normalized result"""

        project_dir = self.normalized_dir / project_name
        project_dir.mkdir(exist_ok=True)

        # Create filename
        filename = f"{tool_name}.json"
        filepath = project_dir / filename

        # Save normalized data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(normalized_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved normalized result to {filepath}")
        return filepath

    def find_raw_results(self, project_name: str, tool_name: Optional[str] = None) -> List[Path]:
        """Find raw results for a project/tool"""

        project_dir = self.raw_dir / project_name

        if not project_dir.exists():
            return []

        if tool_name:
            pattern = f"*{tool_name}*.sarif"
        else:
            pattern = "*.sarif"

        return list(project_dir.glob(pattern))

    def get_project_results(self, project_name: str) -> Dict[str, List[Path]]:
        """Get all results for a project grouped by tool"""

        results = {}
        project_dir = self.raw_dir / project_name

        if not project_dir.exists():
            return results

        for filepath in project_dir.glob("*.sarif"):
            # Extract tool name from filename
            tool_name = filepath.stem.split('_')[0]

            if tool_name not in results:
                results[tool_name] = []

            results[tool_name].append(filepath)

        return results