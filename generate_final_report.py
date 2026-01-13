#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime

def generate_report():
    report = {
        "generated_at": datetime.now().isoformat(),
        "baseline_summary": {},
        "projects": []
    }

    baseline_dir = Path("./baseline")
    if not baseline_dir.exists():
        print("Baseline directory not found!")
        return

    # Читаем сводку
    summary_file = baseline_dir / "baseline_summary.yaml"
    if summary_file.exists():
        import yaml
        with open(summary_file, 'r') as f:
            summary = yaml.safe_load(f)
        report["baseline_summary"] = summary

    # Собираем детали по проектам
    for project_dir in baseline_dir.iterdir():
        if project_dir.is_dir():
            project_info = {
                "name": project_dir.name,
                "tools": [],
                "total_issues": 0
            }

            for baseline_file in project_dir.glob("*_baseline.json"):
                with open(baseline_file, 'r') as f:
                    data = json.load(f)

                tool_info = {
                    "name": data.get("tool", "unknown"),
                    "issues": data.get("issue_count", 0),
                    "severities": data.get("issues_by_severity", {}),
                    "timestamp": data.get("timestamp"),
                    "file": baseline_file.name
                }

                project_info["tools"].append(tool_info)
                project_info["total_issues"] += tool_info["issues"]

            report["projects"].append(project_info)

    # Сохраняем отчет
    report_file = Path("./baseline_final_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ Финальный отчет создан: {report_file}")

    # Выводим краткую информацию
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ ПО BASELINE")
    print("="*60)

    total_issues = 0
    for project in report["projects"]:
        print(f"\n📁 {project['name']}: {project['total_issues']} issues")
        for tool in project["tools"]:
            print(f"  🔧 {tool['name']}: {tool['issues']} issues")
            for severity, count in tool["severities"].items():
                print(f"    - {severity}: {count}")
        total_issues += project["total_issues"]

    print(f"\n📊 Всего issues во всех проектах: {total_issues}")
    print("="*60)

if __name__ == "__main__":
    generate_report()
