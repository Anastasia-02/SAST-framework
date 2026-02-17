"""
Модуль сравнения результатов тестирования с эталонными значениями
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Результат сравнения для одного проекта и инструмента"""
    project: str
    tool: str
    timestamp: str
    baseline_issues: int
    current_issues: int
    matched_issues: int
    new_issues: int
    missing_issues: int
    metrics: Dict[str, float]
    details: Dict[str, Any]


class Comparer:
    """Класс для сравнения результатов SAST-тестирования с эталоном"""

    def load_baseline(self, project: str, tool: str) -> Optional[Dict]:
        baseline_file = self.baseline_dir / project / f"{tool}_baseline.json"
        if not baseline_file.exists():
            logger.warning(f"Baseline file not found: {baseline_file}")
            return None
        logger.info(f"Loading baseline from {baseline_file}")
        # ... остальной код ...

    def load_current_results(self, project: str, tool: str) -> Optional[List[Dict]]:
        result_file = self.results_dir / project / f"{tool}_normalized.json"
        if not result_file.exists():
            logger.warning(f"Current results file not found: {result_file}")
            return None
        logger.info(f"Loading current results from {result_file}")

    def __init__(self, baseline_dir: str = "baseline", results_dir: str = "results/normalized"):
        self.baseline_dir = Path(baseline_dir)
        self.results_dir = Path(results_dir)
        self.comparison_results = {}

        # Поля для сравнения
        self.comparison_fields = [
            "rule_id",
            "file_path",
            "line_number",
            "message",
            "severity"
        ]

    def load_baseline(self, project: str, tool: str) -> Optional[Dict]:
        """Загружает эталонные результаты для проекта и инструмента"""
        baseline_file = self.baseline_dir / project / f"{tool}_baseline.json"

        if not baseline_file.exists():
            logger.warning(f"Baseline not found: {baseline_file}")
            return None

        try:
            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)
            logger.info(f"Loaded baseline for {project}/{tool}: {baseline_data.get('issues_count', 0)} issues")
            return baseline_data
        except Exception as e:
            logger.error(f"Error loading baseline {baseline_file}: {e}")
            return None

    def load_current_results(self, project: str, tool: str) -> Optional[List[Dict]]:
        """Загружает текущие результаты тестирования"""
        result_file = self.results_dir / project / f"{tool}_normalized.json"

        if not result_file.exists():
            logger.warning(f"Current results not found: {result_file}")
            return None

        try:
            with open(result_file, 'r') as f:
                result_data = json.load(f)

            if isinstance(result_data, dict) and 'issues' in result_data:
                return result_data['issues']
            elif isinstance(result_data, list):
                return result_data
            else:
                logger.error(f"Unexpected format in {result_file}")
                return []
        except Exception as e:
            logger.error(f"Error loading results {result_file}: {e}")
            return None

    def calculate_fingerprint(self, issue: Dict) -> str:
        """Вычисляет fingerprint для срабатывания на основе ключевых полей"""
        # Создаем строку для хеширования
        fingerprint_str = ""

        for field in self.comparison_fields:
            if field in issue:
                value = issue[field]
                if value is not None:
                    fingerprint_str += f"{field}:{str(value).lower().strip()};"

        # Добавляем partialFingerprints если есть
        if "partialFingerprints" in issue:
            for fp_key, fp_value in issue["partialFingerprints"].items():
                fingerprint_str += f"{fp_key}:{str(fp_value)};"

        # Вычисляем MD5 хеш
        return hashlib.md5(fingerprint_str.encode('utf-8')).hexdigest()

    def compare_issues(self, baseline_issues: List[Dict], current_issues: List[Dict]) -> Tuple[List, List, List]:
        """
        Сравнивает эталонные и текущие срабатывания

        Возвращает:
        - matched_issues: совпавшие срабатывания
        - new_issues: новые срабатывания (нет в эталоне)
        - missing_issues: пропущенные срабатывания (были в эталоне, но нет сейчас)
        """
        # Вычисляем fingerprints для всех срабатываний
        baseline_fingerprints = {}
        for issue in baseline_issues:
            fp = self.calculate_fingerprint(issue)
            baseline_fingerprints[fp] = issue

        current_fingerprints = {}
        for issue in current_issues:
            fp = self.calculate_fingerprint(issue)
            current_fingerprints[fp] = issue

        # Находим совпадения
        matched_fingerprints = set(baseline_fingerprints.keys()) & set(current_fingerprints.keys())
        matched_issues = [current_fingerprints[fp] for fp in matched_fingerprints]

        # Находим новые срабатывания
        new_fingerprints = set(current_fingerprints.keys()) - set(baseline_fingerprints.keys())
        new_issues = [current_fingerprints[fp] for fp in new_fingerprints]

        # Находим пропущенные срабатывания
        missing_fingerprints = set(baseline_fingerprints.keys()) - set(current_fingerprints.keys())
        missing_issues = [baseline_fingerprints[fp] for fp in missing_fingerprints]

        return matched_issues, new_issues, missing_issues

    def calculate_metrics(self, baseline_count: int, current_count: int,
                          matched_count: int, new_count: int, missing_count: int) -> Dict[str, float]:
        """Вычисляет метрики качества тестирования"""
        metrics = {}

        # Полнота тестирования (Recall)
        if baseline_count > 0:
            metrics["recall"] = matched_count / baseline_count
            metrics["recall_percentage"] = metrics["recall"] * 100
        else:
            metrics["recall"] = 0.0
            metrics["recall_percentage"] = 0.0

        # Дельта ложно-положительных срабатываний
        metrics["fp_delta"] = new_count - missing_count

        # Процент новых срабатываний
        if current_count > 0:
            metrics["new_issues_percentage"] = (new_count / current_count) * 100
        else:
            metrics["new_issues_percentage"] = 0.0

        # Процент пропущенных срабатываний
        if baseline_count > 0:
            metrics["missing_issues_percentage"] = (missing_count / baseline_count) * 100
        else:
            metrics["missing_issues_percentage"] = 0.0

        # F1-мера (баланс между полнотой и точностью)
        precision = matched_count / current_count if current_count > 0 else 0
        recall = metrics["recall"]

        if precision + recall > 0:
            metrics["f1_score"] = 2 * (precision * recall) / (precision + recall)
        else:
            metrics["f1_score"] = 0.0

        return metrics

    def compare_project_tool(self, project: str, tool: str) -> Optional[ComparisonResult]:
        """Сравнивает результаты для конкретного проекта и инструмента"""
        logger.info(f"Comparing {project}/{tool}")

        # Загружаем данные
        baseline_data = self.load_baseline(project, tool)
        if not baseline_data:
            logger.warning(f"No baseline for {project}/{tool}")
            return None

        current_issues = self.load_current_results(project, tool)
        if current_issues is None:
            logger.warning(f"No current results for {project}/{tool}")
            return None

        # Получаем срабатывания из baseline
        baseline_issues = baseline_data.get('issues', [])
        if isinstance(baseline_issues, dict) and 'issues' in baseline_issues:
            baseline_issues = baseline_issues['issues']

        # Сравниваем срабатывания
        matched_issues, new_issues, missing_issues = self.compare_issues(
            baseline_issues, current_issues
        )

        # Вычисляем метрики
        baseline_count = len(baseline_issues)
        current_count = len(current_issues)
        matched_count = len(matched_issues)
        new_count = len(new_issues)
        missing_count = len(missing_issues)

        metrics = self.calculate_metrics(
            baseline_count, current_count, matched_count, new_count, missing_count
        )

        # Создаем детализированную информацию
        details = {
            "matched_issues": matched_issues[:10],  # Ограничиваем вывод для отчета
            "new_issues": new_issues[:10],
            "missing_issues": missing_issues[:10],
            "total_matched": matched_count,
            "total_new": new_count,
            "total_missing": missing_count
        }

        # Создаем результат сравнения
        result = ComparisonResult(
            project=project,
            tool=tool,
            timestamp=datetime.now().isoformat(),
            baseline_issues=baseline_count,
            current_issues=current_count,
            matched_issues=matched_count,
            new_issues=new_count,
            missing_issues=missing_count,
            metrics=metrics,
            details=details
        )

        return result

    def compare_all(self, projects_config: Dict) -> Dict:
        """Сравнивает все проекты и инструменты из конфигурации"""
        all_results = {}

        for project_name, project_info in projects_config.get('projects', {}).items():
            project_results = {}

            for tool_name in project_info.get('tools', []):
                result = self.compare_project_tool(project_name, tool_name)
                if result:
                    project_results[tool_name] = result

            if project_results:
                all_results[project_name] = project_results

        self.comparison_results = all_results
        return all_results

    def generate_summary_report(self, output_path: str = "results/comparison/summary.json"):
        """Генерирует сводный отчет по всем сравнениям"""
        if not self.comparison_results:
            logger.warning("No comparison results to report")
            return

        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_projects": len(self.comparison_results),
            "projects": {}
        }

        # Агрегированные метрики
        total_metrics = {
            "total_baseline_issues": 0,
            "total_current_issues": 0,
            "total_matched_issues": 0,
            "total_new_issues": 0,
            "total_missing_issues": 0,
            "avg_recall": 0.0,
            "avg_f1_score": 0.0
        }

        tool_count = 0

        for project_name, project_results in self.comparison_results.items():
            project_summary = {
                "tools": {},
                "metrics": {
                    "baseline_issues": 0,
                    "current_issues": 0,
                    "matched_issues": 0,
                    "new_issues": 0,
                    "missing_issues": 0,
                    "avg_recall": 0.0
                }
            }

            for tool_name, result in project_results.items():
                tool_count += 1

                # Суммируем метрики по проекту
                project_summary["metrics"]["baseline_issues"] += result.baseline_issues
                project_summary["metrics"]["current_issues"] += result.current_issues
                project_summary["metrics"]["matched_issues"] += result.matched_issues
                project_summary["metrics"]["new_issues"] += result.new_issues
                project_summary["metrics"]["missing_issues"] += result.missing_issues

                # Суммируем общие метрики
                total_metrics["total_baseline_issues"] += result.baseline_issues
                total_metrics["total_current_issues"] += result.current_issues
                total_metrics["total_matched_issues"] += result.matched_issues
                total_metrics["total_new_issues"] += result.new_issues
                total_metrics["total_missing_issues"] += result.missing_issues
                total_metrics["avg_recall"] += result.metrics.get("recall", 0)
                total_metrics["avg_f1_score"] += result.metrics.get("f1_score", 0)

                # Сохраняем детали по инструменту
                project_summary["tools"][tool_name] = {
                    "baseline_issues": result.baseline_issues,
                    "current_issues": result.current_issues,
                    "matched_issues": result.matched_issues,
                    "new_issues": result.new_issues,
                    "missing_issues": result.missing_issues,
                    "recall": result.metrics.get("recall", 0),
                    "recall_percentage": result.metrics.get("recall_percentage", 0),
                    "fp_delta": result.metrics.get("fp_delta", 0),
                    "f1_score": result.metrics.get("f1_score", 0)
                }

            # Вычисляем средний recall для проекта
            if project_results:
                project_summary["metrics"]["avg_recall"] = (
                    project_summary["metrics"]["matched_issues"] /
                    project_summary["metrics"]["baseline_issues"]
                    if project_summary["metrics"]["baseline_issues"] > 0 else 0
                )

            summary["projects"][project_name] = project_summary

        # Вычисляем средние значения
        if tool_count > 0:
            total_metrics["avg_recall"] /= tool_count
            total_metrics["avg_f1_score"] /= tool_count

        summary["aggregated_metrics"] = total_metrics

        # Сохраняем отчет
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Summary report saved to {output_path}")
        return summary

    def generate_detailed_report(self, output_dir: str = "results/comparison/detailed"):
        """Генерирует детальные отчеты по каждому проекту и инструменту"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for project_name, project_results in self.comparison_results.items():
            project_dir = output_dir / project_name
            project_dir.mkdir(exist_ok=True)

            for tool_name, result in project_results.items():
                report = {
                    "project": result.project,
                    "tool": result.tool,
                    "timestamp": result.timestamp,
                    "statistics": {
                        "baseline_issues": result.baseline_issues,
                        "current_issues": result.current_issues,
                        "matched_issues": result.matched_issues,
                        "new_issues": result.new_issues,
                        "missing_issues": result.missing_issues
                    },
                    "metrics": result.metrics,
                    "details": result.details
                }

                report_file = project_dir / f"{tool_name}_comparison.json"
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Detailed reports saved to {output_dir}")

    def check_baseline_exists(self, project: str, tool: str) -> bool:
        """Проверяет, существует ли baseline для проекта и инструмента"""
        baseline_file = self.baseline_dir / project / f"{tool}_baseline.json"
        return baseline_file.exists()

    def list_available_baselines(self) -> Dict[str, List[str]]:
        """Возвращает список доступных baseline"""
        baselines = {}

        for project_dir in self.baseline_dir.iterdir():
            if project_dir.is_dir():
                project_name = project_dir.name
                baselines[project_name] = []

                for baseline_file in project_dir.glob("*_baseline.json"):
                    tool_name = baseline_file.stem.replace("_baseline", "")
                    baselines[project_name].append(tool_name)

        return baselines