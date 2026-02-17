"""
Модуль для сбора и анализа метрик производительности SAST-инструментов
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Метрики производительности инструмента"""
    tool: str
    project: str
    timestamp: str
    execution_time: float  # в секундах
    memory_usage: Optional[float] = None  # в МБ
    cpu_usage: Optional[float] = None  # в %
    issues_per_second: Optional[float] = None
    files_scanned: int = 0
    lines_scanned: int = 0
    issues_found: int = 0


class PerformanceCollector:
    """Сборщик метрик производительности"""

    def __init__(self, metrics_dir: str = "results/metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history = []

    def start_timer(self, tool: str, project: str) -> Dict:
        """Начинает отсчет времени для инструмента"""
        return {
            "tool": tool,
            "project": project,
            "start_time": time.time(),
            "start_timestamp": datetime.now().isoformat()
        }

    def stop_timer(self, timer_data: Dict, issues_count: int = 0,
                   files_scanned: int = 0) -> PerformanceMetrics:
        """Завершает отсчет времени и вычисляет метрики"""
        end_time = time.time()
        execution_time = end_time - timer_data["start_time"]

        # Вычисляем issues per second
        issues_per_second = issues_count / execution_time if execution_time > 0 else 0

        metrics = PerformanceMetrics(
            tool=timer_data["tool"],
            project=timer_data["project"],
            timestamp=timer_data["start_timestamp"],
            execution_time=execution_time,
            issues_per_second=issues_per_second,
            files_scanned=files_scanned,
            issues_found=issues_count
        )

        self.save_metrics(metrics)
        return metrics

    def save_metrics(self, metrics: PerformanceMetrics):
        """Сохраняет метрики в файл"""
        # Сохраняем в общий файл истории
        history_file = self.metrics_dir / "performance_history.json"

        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []

        history.append(asdict(metrics))

        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

        # Сохраняем отдельный файл для этого запуска
        project_dir = self.metrics_dir / metrics.project
        project_dir.mkdir(exist_ok=True)

        metrics_file = project_dir / f"{metrics.tool}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metrics_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)

        logger.info(f"Performance metrics saved: {metrics_file}")

    def load_history(self, tool: Optional[str] = None, project: Optional[str] = None) -> List[Dict]:
        """Загружает историю метрик"""
        history_file = self.metrics_dir / "performance_history.json"

        if not history_file.exists():
            return []

        with open(history_file, 'r') as f:
            history = json.load(f)

        # Фильтруем по tool и project если нужно
        if tool:
            history = [h for h in history if h["tool"] == tool]
        if project:
            history = [h for h in history if h["project"] == project]

        return history

    def calculate_trends(self, tool: str, project: str) -> Dict:
        """Рассчитывает тренды производительности для инструмента и проекта"""
        history = self.load_history(tool, project)

        if not history:
            return {}

        # Сортируем по времени
        history.sort(key=lambda x: x["timestamp"])

        trends = {
            "tool": tool,
            "project": project,
            "total_runs": len(history),
            "avg_execution_time": sum(h["execution_time"] for h in history) / len(history),
            "avg_issues_per_second": sum(h.get("issues_per_second", 0) for h in history) / len(history),
            "latest_metrics": history[-1] if history else None,
            "improvement": None
        }

        # Рассчитываем улучшение/ухудшение по сравнению с предыдущим запуском
        if len(history) >= 2:
            latest = history[-1]
            previous = history[-2]

            if "execution_time" in latest and "execution_time" in previous:
                time_diff = latest["execution_time"] - previous["execution_time"]
                time_percentage = (time_diff / previous["execution_time"]) * 100

                trends["improvement"] = {
                    "execution_time_diff": time_diff,
                    "execution_time_percentage": time_percentage,
                    "is_faster": time_diff < 0
                }

        return trends

    def generate_performance_report(self, output_path: str = "results/performance_report.json"):
        """Генерирует отчет о производительности всех инструментов"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "tools_performance": {},
            "projects_performance": {},
            "recommendations": []
        }

        # Анализируем все метрики
        all_history = self.load_history()

        if not all_history:
            logger.warning("No performance data available")
            return report

        # Группируем по инструментам
        tools = set(h["tool"] for h in all_history)
        for tool in tools:
            tool_history = [h for h in all_history if h["tool"] == tool]

            report["tools_performance"][tool] = {
                "total_runs": len(tool_history),
                "avg_execution_time": sum(h["execution_time"] for h in tool_history) / len(tool_history),
                "avg_issues_found": sum(h.get("issues_found", 0) for h in tool_history) / len(tool_history),
                "best_run": min(tool_history, key=lambda x: x["execution_time"]),
                "worst_run": max(tool_history, key=lambda x: x["execution_time"])
            }

        # Группируем по проектам
        projects = set(h["project"] for h in all_history)
        for project in projects:
            project_history = [h for h in all_history if h["project"] == project]

            report["projects_performance"][project] = {
                "total_runs": len(project_history),
                "total_execution_time": sum(h["execution_time"] for h in project_history),
                "avg_execution_time": sum(h["execution_time"] for h in project_history) / len(project_history),
                "total_issues_found": sum(h.get("issues_found", 0) for h in project_history)
            }

        # Генерируем рекомендации
        self._generate_recommendations(report)

        # Сохраняем отчет
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Performance report saved to {output_path}")
        return report

    def _generate_recommendations(self, report: Dict):
        """Генерирует рекомендации на основе метрик производительности"""
        recommendations = []

        # Анализируем производительность инструментов
        for tool, metrics in report.get("tools_performance", {}).items():
            avg_time = metrics.get("avg_execution_time", 0)

            if avg_time > 300:  # Больше 5 минут
                recommendations.append({
                    "type": "performance_warning",
                    "tool": tool,
                    "message": f"Tool {tool} is slow (avg {avg_time:.1f}s). Consider optimizing or replacing.",
                    "severity": "high"
                })
            elif avg_time > 60:  # Больше 1 минуты
                recommendations.append({
                    "type": "performance_notice",
                    "tool": tool,
                    "message": f"Tool {tool} execution time is {avg_time:.1f}s. Monitor for degradation.",
                    "severity": "medium"
                })

        report["recommendations"] = recommendations