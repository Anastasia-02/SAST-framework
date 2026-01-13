#!/usr/bin/env python3
# baseline_utils.py

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class BaselineUtils:
    """Утилиты для работы с baseline"""

    def __init__(self, baseline_dir: str = "./baseline"):
        self.baseline_dir = Path(baseline_dir)

    def list_all_baselines(self) -> Dict[str, List[Dict[str, Any]]]:
        """Список всех baseline с деталями"""
        baselines = {}

        for project_dir in self.baseline_dir.iterdir():
            if project_dir.is_dir():
                project_name = project_dir.name
                baselines[project_name] = []

                for baseline_file in project_dir.glob("*_baseline.json"):
                    with open(baseline_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    baselines[project_name].append({
                        'tool': data.get('tool'),
                        'issues': data.get('issue_count', 0),
                        'file': baseline_file.name,
                        'timestamp': data.get('timestamp'),
                        'severities': data.get('issues_by_severity', {})
                    })

        return baselines

    def compare_two_baselines(self, project: str, tool: str,
                              baseline1: str, baseline2: str) -> Dict[str, Any]:
        """Сравнить две версии baseline для одного проекта и инструмента"""

        file1 = self.baseline_dir / project / f"{tool}_{baseline1}.json"
        file2 = self.baseline_dir / project / f"{tool}_{baseline2}.json"

        if not file1.exists() or not file2.exists():
            return {"error": "Baseline files not found"}

        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)

        # Простое сравнение
        return {
            'project': project,
            'tool': tool,
            'baseline1': baseline1,
            'baseline2': baseline2,
            'issues1': data1.get('issue_count', 0),
            'issues2': data2.get('issue_count', 0),
            'delta': data2.get('issue_count', 0) - data1.get('issue_count', 0),
            'severity_changes': self._compare_severities(
                data1.get('issues_by_severity', {}),
                data2.get('issues_by_severity', {})
            )
        }

    def _compare_severities(self, sev1: Dict, sev2: Dict) -> Dict:
        """Сравнить распределение по серьезности"""
        all_severities = set(sev1.keys()) | set(sev2.keys())
        changes = {}

        for severity in all_severities:
            count1 = sev1.get(severity, 0)
            count2 = sev2.get(severity, 0)
            changes[severity] = {
                'before': count1,
                'after': count2,
                'delta': count2 - count1
            }

        return changes

    def export_to_csv(self, output_file: str = "baseline_report.csv"):
        """Экспорт baseline в CSV"""
        import csv

        baselines = self.list_all_baselines()

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Project', 'Tool', 'Issues', 'Errors', 'Warnings', 'Info', 'Timestamp'])

            for project, tools_data in baselines.items():
                for tool_data in tools_data:
                    writer.writerow([
                        project,
                        tool_data['tool'],
                        tool_data['issues'],
                        tool_data['severities'].get('error', 0),
                        tool_data['severities'].get('warning', 0),
                        tool_data['severities'].get('info', 0),
                        tool_data['timestamp']
                    ])

        print(f"✅ Отчет сохранен в {output_file}")


# Использование
if __name__ == "__main__":
    utils = BaselineUtils()

    print("=== ВСЕ BASELINE ===")
    all_baselines = utils.list_all_baselines()

    for project, tools in all_baselines.items():
        print(f"\n📁 {project}:")
        for tool in tools:
            print(
                f"  🔧 {tool['tool']}: {tool['issues']} issues (E:{tool['severities'].get('error', 0)} W:{tool['severities'].get('warning', 0)} I:{tool['severities'].get('info', 0)})")

    # Экспорт в CSV
    utils.export_to_csv()