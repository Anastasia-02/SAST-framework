"""
Инструмент Cppcheck
"""

import os
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict
from .base_tool import BaseTool


class CppcheckTool(BaseTool):
    """Инструмент Cppcheck для анализа C/C++ кода"""

    def __init__(self):
        super().__init__(
            name="cppcheck",
            image="ghcr.io/facthunder/cppcheck:latest",
            version="latest"
        )

    def run(self, project_path: str, config: Dict) -> bool:
        """
        Запускает Cppcheck на проекте

        Args:
            project_path: Путь к проекту
            config: Конфигурация инструмента

        Returns:
            bool: Успешно ли выполнился инструмент
        """
        try:
            project_name = Path(project_path).name
            output_path = self._get_output_path(project_name)

            self.logger.info(f"Running cppcheck on {project_path}")

            # Создаем временный файл для XML вывода
            xml_output = "/results/cppcheck_results.xml"

            # Команда для запуска cppcheck
            command = [
                "cppcheck",
                "--enable=all",
                "--xml",
                "--xml-version=2",
                f"--output-file={xml_output}",
                "/src"
            ]

            # Запускаем в контейнере
            result = self.run_in_container(command, project_path)

            # Cppcheck возвращает 0 при успехе, 1 при наличии предупреждений
            if result.returncode not in [0, 1]:
                self.logger.error(f"Cppcheck failed with code {result.returncode}")
                return False

            # Конвертируем XML в SARIF
            temp_xml_path = Path("results/raw/cppcheck_results.xml")
            if temp_xml_path.exists():
                sarif_results = self._convert_xml_to_sarif(temp_xml_path)

                # Сохраняем результаты
                self.save_results(sarif_results, output_path)

                # Удаляем временный файл
                temp_xml_path.unlink(missing_ok=True)
            else:
                self.logger.warning("No XML results found, creating empty SARIF")
                self.save_results(self._create_empty_sarif(), output_path)

            return True

        except Exception as e:
            self.logger.error(f"Error running cppcheck: {e}")
            return False

    def load_results(self) -> Dict:
        """
        Загружает результаты Cppcheck

        Returns:
            Dict: Результаты в формате SARIF
        """
        if self.results is not None:
            return self.results

        if self.output_path and Path(self.output_path).exists():
            return self.load_sarif_results(self.output_path)

        return self._create_empty_sarif()

    def _convert_xml_to_sarif(self, xml_path: Path) -> Dict:
        """
        Конвертирует XML вывод Cppcheck в SARIF формат

        Args:
            xml_path: Путь к XML файлу

        Returns:
            Dict: Результаты в SARIF формате
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            sarif = {
                "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
                "version": "2.1.0",
                "runs": [{
                    "tool": {
                        "driver": {
                            "name": "cppcheck",
                            "version": self._get_version(),
                            "informationUri": "https://cppcheck.sourceforge.net"
                        }
                    },
                    "results": []
                }]
            }

            # Обрабатываем ошибки
            errors_element = root.find('errors')
            if errors_element is not None:
                for error in errors_element.findall('error'):
                    result = {
                        "ruleId": error.get('id', 'unknown'),
                        "level": self._get_severity(error.get('severity', 'style')),
                        "message": {
                            "text": error.get('msg', 'No message')
                        },
                        "locations": []
                    }

                    # Добавляем информацию о местоположении
                    location_elem = error.find('location')
                    if location_elem is not None:
                        location = {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": location_elem.get('file', '').replace("/src/", "")
                                },
                                "region": {
                                    "startLine": int(location_elem.get('line', 1)),
                                    "startColumn": 1
                                }
                            }
                        }
                        result["locations"].append(location)

                    # Добавляем fingerprint
                    if location_elem is not None:
                        result["partialFingerprints"] = {
                            "primaryLocationLineHash": f"{error.get('id', 'unknown')}:{location_elem.get('file', '')}:{location_elem.get('line', 1)}"
                        }

                    sarif["runs"][0]["results"].append(result)

            return sarif

        except Exception as e:
            self.logger.error(f"Error converting Cppcheck XML to SARIF: {e}")
            return self._create_empty_sarif()

    def _get_severity(self, cppcheck_severity: str) -> str:
        """
        Конвертирует severity из Cppcheck в SARIF

        Args:
            cppcheck_severity: Уровень важности Cppcheck

        Returns:
            str: Уровень важности SARIF
        """
        severity_map = {
            "error": "error",
            "warning": "warning",
            "style": "note",
            "performance": "warning",
            "portability": "note"
        }
        return severity_map.get(cppcheck_severity.lower(), "note")

    def _get_version(self) -> str:
        """
        Получает версию Cppcheck

        Returns:
            str: Версия Cppcheck
        """
        try:
            result = subprocess.run(
                ["cppcheck", "--version"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                return result.stdout.strip()
        except:
            pass
        return "unknown"

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
                        "name": "cppcheck",
                        "version": self.version,
                        "informationUri": "https://cppcheck.sourceforge.net"
                    }
                },
                "results": []
            }]
        }