"""
Инструмент ShellCheck
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List
from tools.base_tool import BaseTool


class ShellcheckTool(BaseTool):
    """Инструмент ShellCheck для анализа shell скриптов"""

    def __init__(self):
        super().__init__(
            name="shellcheck",
            image="koalaman/shellcheck-alpine:stable",
            version="stable"
        )

    def run(self, project_path: str, config: Dict) -> bool:
        """
        Запускает ShellCheck на проекте

        Args:
            project_path: Путь к проекту
            config: Конфигурация инструмента

        Returns:
            bool: Успешно ли выполнился инструмент
        """
        try:
            project_name = Path(project_path).name
            output_path = self._get_output_path(project_name)

            self.logger.info(f"Running shellcheck on {project_path}")

            # Находим все shell файлы в проекте
            shell_files = self._find_shell_files(project_path)

            if not shell_files:
                self.logger.warning(f"No shell files found in {project_path}")
                self.save_results(self._create_empty_sarif(), output_path)
                return True

            # Создаем временный файл для JSON вывода
            json_output = "/results/shellcheck_results.json"

            # Формируем команду для shellcheck
            # Сначала находим файлы в контейнере
            find_cmd = "find /src -type f \\( -name '*.sh' -o -name '*.bash' -o -name '*.zsh' -o -name '*.ksh' \\)"
            shellcheck_cmd = f"shellcheck -f json {{}} > {json_output}"
            command = ["sh", "-c", f"{find_cmd} | xargs -I {{}} {shellcheck_cmd}"]

            # Запускаем в контейнере
            result = self.run_in_container(command, project_path)

            # Shellcheck возвращает 0 при успехе, 1 при наличии предупреждений
            if result.returncode not in [0, 1]:
                self.logger.error(f"Shellcheck failed with code {result.returncode}")
                return False

            # Конвертируем JSON в SARIF
            temp_json_path = Path("results/raw/shellcheck_results.json")
            if temp_json_path.exists():
                with open(temp_json_path, 'r') as f:
                    shellcheck_results = json.load(f)

                sarif_results = self._convert_to_sarif(shellcheck_results)

                # Сохраняем результаты
                self.save_results(sarif_results, output_path)

                # Удаляем временный файл
                temp_json_path.unlink(missing_ok=True)
            else:
                self.logger.warning("No JSON results found, creating empty SARIF")
                self.save_results(self._create_empty_sarif(), output_path)

            return True

        except Exception as e:
            self.logger.error(f"Error running shellcheck: {e}")
            return False

    def load_results(self) -> Dict:
        """
        Загружает результаты ShellCheck

        Returns:
            Dict: Результаты в формате SARIF
        """
        if self.results is not None:
            return self.results

        if self.output_path and Path(self.output_path).exists():
            return self.load_sarif_results(self.output_path)

        return self._create_empty_sarif()

    def _find_shell_files(self, project_path: str) -> List[str]:
        """
        Находит все shell файлы в проекте

        Args:
            project_path: Путь к проекту

        Returns:
            List[str]: Список путей к shell файлам
        """
        shell_extensions = ['.sh', '.bash', '.zsh', '.ksh']
        shell_files = []

        for root, dirs, files in os.walk(project_path):
            # Пропускаем скрытые директории
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if any(file.endswith(ext) for ext in shell_extensions):
                    shell_files.append(os.path.join(root, file))
                elif self._has_shebang(os.path.join(root, file)):
                    shell_files.append(os.path.join(root, file))

        return shell_files

    def _has_shebang(self, filepath: str) -> bool:
        """
        Проверяет, содержит ли файл shebang для shell

        Args:
            filepath: Путь к файлу

        Returns:
            bool: True если файл содержит shebang для shell
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                return first_line.startswith('#!') and any(
                    shell in first_line for shell in ['bash', 'sh', 'zsh', 'ksh']
                )
        except:
            return False

    def _convert_to_sarif(self, shellcheck_results: List[Dict]) -> Dict:
        """
        Конвертирует результаты ShellCheck в SARIF формат

        Args:
            shellcheck_results: Результаты ShellCheck

        Returns:
            Dict: Результаты в SARIF формате
        """
        sarif = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "shellcheck",
                        "version": self._get_version(),
                        "informationUri": "https://www.shellcheck.net"
                    }
                },
                "results": []
            }]
        }

        for item in shellcheck_results:
            result = {
                "ruleId": f"SC{item.get('code', '0000')}",
                "level": self._get_severity(item.get('level', 'info')),
                "message": {
                    "text": item.get('message', 'No message')
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": item.get('file', '').replace("/src/", "")
                        },
                        "region": {
                            "startLine": item.get('line', 1),
                            "startColumn": item.get('column', 1),
                            "endLine": item.get('endLine', item.get('line', 1)),
                            "endColumn": item.get('endColumn', item.get('column', 1))
                        }
                    }
                }],
                "partialFingerprints": {
                    "primaryLocationLineHash": f"SC{item.get('code', '0000')}:{item.get('file', '')}:{item.get('line', 1)}"
                }
            }

            sarif["runs"][0]["results"].append(result)

        return sarif

    def _get_severity(self, shellcheck_level: str) -> str:
        """
        Конвертирует severity из ShellCheck в SARIF

        Args:
            shellcheck_level: Уровень важности ShellCheck

        Returns:
            str: Уровень важности SARIF
        """
        severity_map = {
            "error": "error",
            "warning": "warning",
            "info": "note",
            "style": "note"
        }
        return severity_map.get(shellcheck_level.lower(), "note")

    def _get_version(self) -> str:
        """
        Получает версию ShellCheck

        Returns:
            str: Версия ShellCheck
        """
        try:
            result = subprocess.run(
                ["shellcheck", "--version"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                # Парсим версию из вывода
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        return line.split()[-1]
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
                        "name": "shellcheck",
                        "version": self.version,
                        "informationUri": "https://www.shellcheck.net"
                    }
                },
                "results": []
            }]
        }