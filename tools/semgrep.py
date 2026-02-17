"""
Инструмент Semgrep
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List
from tools.base_tool import BaseTool


class SemgrepTool(BaseTool):
    """Инструмент Semgrep для статического анализа кода"""

    def __init__(self):
        super().__init__(
            name="semgrep",
            image="returntocorp/semgrep:latest",
            version="latest"
        )

    def run(self, project_path: str, config: Dict) -> bool:
        """
        Запускает Semgrep на проекте

        Args:
            project_path: Путь к проекту
            config: Конфигурация инструмента

        Returns:
            bool: Успешно ли выполнился инструмент
        """
        try:
            project_name = Path(project_path).name
            output_path = self._get_output_path(project_name)

            self.logger.info(f"Running semgrep on {project_path}")

            # Команда для запуска semgrep в контейнере
            command = [
                "semgrep",
                "scan",
                "--config=auto",
                "--json",
                "--output=/results/semgrep_results.json",
                "/src"
            ]

            # Запускаем в контейнере
            result = self.run_in_container(command, project_path)

            if result.returncode not in [0, 1]:  # 0 - успех, 1 - есть предупреждения
                self.logger.error(f"Semgrep failed with code {result.returncode}")
                return False

            # Загружаем результаты
            temp_results_path = Path("results/raw/semgrep_results.json")
            if temp_results_path.exists():
                with open(temp_results_path, 'r') as f:
                    semgrep_results = json.load(f)

                # Конвертируем в SARIF формат
                sarif_results = self._convert_to_sarif(semgrep_results)

                # Сохраняем результаты
                self.save_results(sarif_results, output_path)

                # Удаляем временный файл
                temp_results_path.unlink(missing_ok=True)
            else:
                self.logger.warning("No results file found, creating empty SARIF")
                self.save_results(self._create_empty_sarif(), output_path)

            return True

        except Exception as e:
            self.logger.error(f"Error running semgrep: {e}")
            return False

    def load_results(self) -> Dict:
        """
        Загружает результаты Semgrep

        Returns:
            Dict: Результаты в формате SARIF
        """
        if self.results is not None:
            return self.results

        if self.output_path and Path(self.output_path).exists():
            return self.load_sarif_results(self.output_path)

        return self._create_empty_sarif()

    def _convert_to_sarif(self, semgrep_results: Dict) -> Dict:
        """
        Конвертирует результаты Semgrep в SARIF формат

        Args:
            semgrep_results: Результаты Semgrep

        Returns:
            Dict: Результаты в SARIF формате
        """
        sarif = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "semgrep",
                        "version": self.version,
                        "informationUri": "https://semgrep.dev"
                    }
                },
                "results": []
            }]
        }

        if "results" not in semgrep_results:
            return sarif

        for finding in semgrep_results.get("results", []):
            result = {
                "ruleId": finding.get("check_id", "unknown"),
                "level": self._get_severity(finding.get("extra", {}).get("severity", "WARNING")),
                "message": {
                    "text": finding.get("extra", {}).get("message", "No message")
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": finding.get("path", "").replace("/src/", "")
                        },
                        "region": {
                            "startLine": finding.get("start", {}).get("line", 1),
                            "startColumn": finding.get("start", {}).get("col", 1),
                            "endLine": finding.get("end", {}).get("line", finding.get("start", {}).get("line", 1)),
                            "endColumn": finding.get("end", {}).get("col", finding.get("start", {}).get("col", 1))
                        }
                    }
                }],
                "partialFingerprints": {
                    "primaryLocationLineHash": f"{finding.get('check_id', 'unknown')}:{finding.get('path', '')}:{finding.get('start', {}).get('line', 1)}"
                }
            }

            sarif["runs"][0]["results"].append(result)

        return sarif

    def _get_severity(self, semgrep_severity: str) -> str:
        """
        Конвертирует severity из Semgrep в SARIF

        Args:
            semgrep_severity: Уровень важности Semgrep

        Returns:
            str: Уровень важности SARIF
        """
        severity_map = {
            "ERROR": "error",
            "WARNING": "warning",
            "INFO": "note"
        }
        return severity_map.get(semgrep_severity.upper(), "warning")

    def _create_empty_sarif(self) -> Dict:
        """
        Создает пустую SARIF структуру

        Returns:
            Dict: Пустая SARIF структура
        """
        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "semgrep",
                        "version": self.version,
                        "informationUri": "https://semgrep.dev"
                    }
                },
                "results": []
            }]
        }