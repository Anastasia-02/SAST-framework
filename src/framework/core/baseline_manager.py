import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..normalization.models import NormalizedResult
from ..utils.logger import logger


class BaselineManager:
    """Manage baseline (reference) results for comparison"""

    def __init__(self, baseline_dir: Path):
        self.baseline_dir = baseline_dir
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    def save_baseline(self, result: NormalizedResult, tool_name: str) -> Path:
        """Save normalized result as baseline"""

        project_dir = self.baseline_dir / result.project
        project_dir.mkdir(exist_ok=True)

        # Create filename
        filename = f"{tool_name}_baseline.json"
        filepath = project_dir / filename

        # Convert to dict and save
        data = result.to_dict()
        data['created_at'] = datetime.now().isoformat()
        data['is_baseline'] = True

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved baseline for {result.project}/{tool_name} to {filepath}")
        return filepath

    def load_baseline(self, project_name: str, tool_name: str) -> Optional[NormalizedResult]:
        """Load baseline result"""

        filename = f"{tool_name}_baseline.json"
        filepath = self.baseline_dir / project_name / filename

        if not filepath.exists():
            logger.warning(f"No baseline found for {project_name}/{tool_name}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert string timestamp back to datetime
            if 'timestamp' in data and isinstance(data['timestamp'], str):
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])

            # Convert back to NormalizedResult
            return NormalizedResult(**data)

        except Exception as e:
            logger.error(f"Failed to load baseline from {filepath}: {e}")
            return None

    def list_baselines(self) -> Dict[str, List[str]]:
        """List all available baselines"""

        baselines = {}

        for project_dir in self.baseline_dir.iterdir():
            if project_dir.is_dir():
                project_name = project_dir.name
                baselines[project_name] = []

                for baseline_file in project_dir.glob("*_baseline.json"):
                    tool_name = baseline_file.stem.replace('_baseline', '')
                    baselines[project_name].append(tool_name)

        return baselines

    def generate_baseline_summary(self) -> Dict[str, Any]:
        """Generate summary of all baselines"""

        summary = {
            "generated_at": datetime.now().isoformat(),
            "projects": {}
        }

        baselines = self.list_baselines()

        for project_name, tools in baselines.items():
            project_summary = {
                "tools": {},
                "total_issues": 0
            }

            for tool_name in tools:
                baseline = self.load_baseline(project_name, tool_name)
                if baseline:
                    project_summary["tools"][tool_name] = {
                        "issue_count": baseline.issue_count,
                        "by_severity": baseline.issues_by_severity,
                        "timestamp": baseline.timestamp.isoformat()
                    }
                    project_summary["total_issues"] += baseline.issue_count

            summary["projects"][project_name] = project_summary

        # Save summary
        summary_file = self.baseline_dir / "baseline_summary.yaml"
        with open(summary_file, 'w', encoding='utf-8') as f:
            yaml.dump(summary, f, default_flow_style=False)

        return summary