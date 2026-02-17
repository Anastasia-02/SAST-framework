"""
Базовый класс для всех SAST-инструментов
"""

import os
import json
import logging
import subprocess
import docker
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Абстрактный базовый класс для инструментов SAST"""

    def __init__(self, name: str, image: str = None, version: str = "latest"):
        self.name = name
        self.image = image
        self.version = version
        self.output_path = None
        self.results = None
        self.logger = logging.getLogger(f"sast_framework.tools.{name}")

    @abstractmethod
    def run(self, project_path: str, config: Dict) -> bool:
        """
        Запускает инструмент на указанном проекте

        Args:
            project_path: Путь к проекту
            config: Конфигурация инструмента

        Returns:
            bool: Успешно ли выполнился инструмент
        """
        pass

    @abstractmethod
    def load_results(self) -> Dict:
        """
        Загружает результаты выполнения инструмента

        Returns:
            Dict: Результаты в формате SARIF или аналогичном
        """
        pass

    def run_in_container(self, command: List[str], project_path: str,
                         mount_readonly: bool = True) -> subprocess.CompletedProcess:
        """
        Запускает команду в Docker-контейнере и возвращает результат.
        Не выбрасывает исключение при ненулевом коде возврата, а возвращает объект с этим кодом.
        """
        try:
            client = docker.from_env()

            output_dir = Path("results/raw")
            output_dir.mkdir(parents=True, exist_ok=True)

            abs_project_path = Path(project_path).absolute()
            abs_output_dir = output_dir.absolute()

            volumes = {
                str(abs_project_path): {
                    'bind': '/src',
                    'mode': 'ro' if mount_readonly else 'rw'
                },
                str(abs_output_dir): {
                    'bind': '/results',
                    'mode': 'rw'
                }
            }

            self.logger.info(f"Running container: {self.image}")
            self.logger.info(f"Command: {' '.join(command)}")

            container = client.containers.run(
                image=self.image,
                command=command,
                volumes=volumes,
                working_dir='/src',
                detach=False,
                remove=True,
                stdout=True,
                stderr=True
            )

            stdout = container.decode('utf-8') if isinstance(container, bytes) else str(container)
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=stdout,
                stderr=''
            )

        except docker.errors.ContainerError as e:
            self.logger.warning(f"Container exited with code {e.exit_status}")
            stdout = e.stdout if hasattr(e, 'stdout') else ''
            stderr = e.stderr if hasattr(e, 'stderr') else ''
            return subprocess.CompletedProcess(
                args=command,
                returncode=e.exit_status,
                stdout=stdout,
                stderr=stderr
            )
        except docker.errors.ImageNotFound as e:
            self.logger.error(f"Docker image not found: {self.image}")
            raise
        except docker.errors.APIError as e:
            self.logger.error(f"Docker API error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error running container: {e}")
            raise

    def run_local(self, command: List[str], cwd: str = None) -> subprocess.CompletedProcess:
        """
        Запускает команду локально (без Docker)

        Args:
            command: Команда для выполнения
            cwd: Рабочая директория

        Returns:
            subprocess.CompletedProcess: Результат выполнения
        """
        self.logger.info(f"Running locally: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут таймаут
            )

            if result.stdout:
                self.logger.debug(f"Stdout: {result.stdout[:500]}...")
            if result.stderr:
                self.logger.debug(f"Stderr: {result.stderr[:500]}...")

            return result

        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(command)}")
            raise
        except Exception as e:
            self.logger.error(f"Error running command locally: {e}")
            raise

    def save_results(self, results: Dict, output_path: str) -> None:
        """
        Сохраняет результаты в файл

        Args:
            results: Результаты для сохранения
            output_path: Путь для сохранения
        """
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Results saved to {output_path}")
        self.output_path = output_path
        self.results = results

    def load_sarif_results(self, file_path: str) -> Dict:
        """
        Загружает результаты из SARIF файла

        Args:
            file_path: Путь к SARIF файлу

        Returns:
            Dict: Загруженные результаты
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.logger.info(f"Loaded SARIF results from {file_path}")
            return data

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON from {file_path}: {e}")
            # Возвращаем пустую SARIF структуру
            return {
                "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
                "version": "2.1.0",
                "runs": []
            }
        except FileNotFoundError:
            self.logger.error(f"Results file not found: {file_path}")
            return {
                "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
                "version": "2.1.0",
                "runs": []
            }

    def _get_output_path(self, project_name: str) -> str:
        """
        Генерирует путь для сохранения результатов

        Args:
            project_name: Имя проекта

        Returns:
            str: Путь к файлу результатов
        """
        timestamp = subprocess.getoutput('date +%Y%m%d_%H%M%S')
        return f"results/raw/{project_name}/{self.name}_{timestamp}.sarif"