"""
Инструмент ShellCheck
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional
from .base_tool import BaseTool

logger = logging.getLogger(__name__)

class ShellcheckTool(BaseTool):
    """Инструмент ShellCheck для анализа shell скриптов"""

    def __init__(self):
        super().__init__(
            name="shellcheck",
            image="koalaman/shellcheck-alpine:stable",
            version="stable"
        )
        self.shell_extensions = ['.sh', '.bash', '.zsh', '.ksh']

    def run(self, project_path: str, config: Dict) -> bool:
        """
        Запускает ShellCheck на проекте.
        """
        try:
            project_name = Path(project_path).name
            output_path = self._get_output_path(project_name)
            self.logger.info(f"Running shellcheck on {project_path}")

            # Находим все shell-файлы
            shell_files = self._find_shell_files(project_path)
            if not shell_files:
                self.logger.warning(f"No shell files found in {project_path}. Creating empty SARIF.")
                empty_sarif = self._create_empty_sarif()
                self.save_results(empty_sarif, output_path)
                return True

            # Формируем пути внутри контейнера
            container_files = [f"/src/{f}" for f in shell_files]
            files_str = " ".join(container_files)
            # Команда: shellcheck -f json файлы > /results/shellcheck_results.json
            cmd = f"shellcheck -f json {files_str} > /results/shellcheck_results.json"

            self.logger.info(f"Running command in container: {cmd}")

            # Запускаем контейнер с командой
            result = self.run_in_container(["sh", "-c", cmd], project_path)

            # Коды 0 и 1 считаем успешными (0 – нет ошибок, 1 – есть предупреждения)
            if result.returncode not in [0, 1]:
                self.logger.error(f"Shellcheck failed with code {result.returncode}: {result.stderr}")
                # Всё равно создаём пустой SARIF, чтобы не прерывать процесс
                empty_sarif = self._create_empty_sarif()
                self.save_results(empty_sarif, output_path)
                return True

            # Загружаем результаты из временного файла
            temp_json_path = Path("results/raw/shellcheck_results.json")
            if temp_json_path.exists():
                with open(temp_json_path, 'r', encoding='utf-8') as f:
                    shellcheck_results = json.load(f)
                sarif_results = self._convert_to_sarif(shellcheck_results)
                self.save_results(sarif_results, output_path)
                temp_json_path.unlink(missing_ok=True)
            else:
                self.logger.warning("No JSON results file created, creating empty SARIF")
                empty_sarif = self._create_empty_sarif()
                self.save_results(empty_sarif, output_path)

            return True

        except Exception as e:
            self.logger.error(f"Error running shellcheck: {e}", exc_info=True)
            return False

    def load_results(self) -> Dict:
        if self.results is not None:
            return self.results
        if self.output_path and Path(self.output_path).exists():
            return self.load_sarif_results(self.output_path)
        return self._create_empty_sarif()

    def _find_shell_files(self, project_path: str) -> List[str]:
        """Находит все shell-файлы в проекте."""
        shell_files = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_path)
                if any(file.endswith(ext) for ext in self.shell_extensions):
                    shell_files.append(rel_path)
                elif self._has_shebang(full_path):
                    shell_files.append(rel_path)
        return shell_files

    def _has_shebang(self, filepath: str) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                return first_line.startswith('#!') and any(
                    shell in first_line for shell in ['bash', 'sh', 'zsh', 'ksh']
                )
        except:
            return False

    def _convert_to_sarif(self, shellcheck_results: List[Dict]) -> Dict:
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
            file_path = item.get('file', '')
            if file_path.startswith('/src/'):
                file_path = file_path[5:]
            result = {
                "ruleId": f"SC{item.get('code', '0000')}",
                "level": self._get_severity(item.get('level', 'info')),
                "message": {"text": item.get('message', 'No message')},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": file_path},
                        "region": {
                            "startLine": item.get('line', 1),
                            "startColumn": item.get('column', 1),
                            "endLine": item.get('endLine', item.get('line', 1)),
                            "endColumn": item.get('endColumn', item.get('column', 1))
                        }
                    }
                }],
                "partialFingerprints": {
                    "primaryLocationLineHash": f"SC{item.get('code', '0000')}:{file_path}:{item.get('line', 1)}"
                }
            }
            sarif["runs"][0]["results"].append(result)
        return sarif

    def _get_severity(self, shellcheck_level: str) -> str:
        severity_map = {
            "error": "error",
            "warning": "warning",
            "info": "note",
            "style": "note"
        }
        return severity_map.get(shellcheck_level.lower(), "note")

    def _get_version(self) -> str:
        try:
            result = subprocess.run(
                ["shellcheck", "--version"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        return line.split()[-1]
        except:
            pass
        return "unknown"

    def _create_empty_sarif(self) -> Dict:
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