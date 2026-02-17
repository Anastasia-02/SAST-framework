import time
import logging
import os
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path

from environment import Environment
from normalizer import Normalizer
from tools_registry import ToolsRegistry
from performance_metrics import PerformanceCollector

logger = logging.getLogger(__name__)

class TestRunner:
    def __init__(self, config_path: str):
        """
        Инициализация TestRunner.

        Args:
            config_path: Путь к файлу конфигурации проектов (YAML).
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.environment = Environment()
        self.normalizer = Normalizer()
        self.tools_registry = ToolsRegistry()
        self.performance_collector = PerformanceCollector()
        self.timers = {}

    def _load_config(self) -> Dict:
        """Загружает конфигурацию из YAML-файла."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {self.config_path}")
        return config

    def run_all_tests(self) -> Dict:
        """
        Запускает тестирование для всех проектов из конфигурации.

        Returns:
            Dict: Словарь с результатами для каждого проекта.
        """
        results = {}
        projects = self.config.get('projects', {})
        logger.info(f"Found {len(projects)} projects in config")
        for project_name, project_info in projects.items():
            logger.info(f"Running tests for project: {project_name}")
            project_results = self.run_test(project_name, project_info)
            results[project_name] = project_results
        return results

    def run_test(self, project_name: str, project_info: Dict) -> Dict:
        """Запускает тестирование для одного проекта с метриками производительности"""
        try:
            logger.info(f"Starting testing for project: {project_name}")

            # Подготовка окружения
            self.environment.setup()

            results = {}
            project_path = project_info['path']

            # Запуск каждого инструмента
            for tool_name in project_info['tools']:
                logger.info(f"  Running {tool_name}...")

                try:
                    # Запускаем таймер
                    self.timers[(project_name, tool_name)] = (
                        self.performance_collector.start_timer(tool_name, project_name)
                    )

                    # Получаем инструмент
                    tool = self.tools_registry.get_tool(tool_name)
                    if not tool:
                        logger.error(f"Tool {tool_name} not found")
                        results[tool_name] = {'success': False, 'error': f'Tool {tool_name} not found'}
                        continue

                    # Запускаем инструмент
                    success = tool.run(project_path, self.config)

                    if success:
                        # Загружаем и нормализуем результаты
                        raw_result = tool.load_results()
                        normalized = self.normalizer.normalize(raw_result)

                        # Сохраняем нормализованные результаты на диск
                        self.normalizer.save_normalized(normalized, project_name, tool_name)

                        # Останавливаем таймер и получаем метрики
                        timer_data = self.timers.pop((project_name, tool_name), None)
                        if timer_data:
                            files_count = self._count_files_in_project(project_path, tool_name)
                            performance_metrics = self.performance_collector.stop_timer(
                                timer_data,
                                issues_count=len(normalized),
                                files_scanned=files_count
                            )
                        else:
                            performance_metrics = None

                        results[tool_name] = {
                            'success': True,
                            'raw_result': raw_result,
                            'normalized': normalized,
                            'issues_count': len(normalized),
                            'performance': performance_metrics
                        }
                        logger.info(f"    Found {len(normalized)} issues")
                    else:
                        results[tool_name] = {'success': False, 'error': 'Tool execution failed'}
                        logger.error(f"    Tool {tool_name} failed")

                except Exception as e:
                    logger.error(f"Error running tool {tool_name}: {e}")
                    results[tool_name] = {'success': False, 'error': str(e)}

            return results

        except Exception as e:
            logger.error(f"Error testing project {project_name}: {e}")
            return {}
        finally:
            # Очистка окружения
            self.environment.cleanup()

    def _count_files_in_project(self, project_path: str, tool_name: str) -> int:
        """Подсчитывает количество файлов, которые будет сканировать инструмент"""
        file_patterns = {
            'semgrep': ['.py', '.js', '.ts', '.java', '.go', '.rb'],
            'cppcheck': ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp'],
            'shellcheck': ['.sh', '.bash', '.zsh', '.ksh'],
            'sonarqube': ['.py', '.java', '.js', '.ts', '.cpp', '.c', '.go', '.rb'],
            'pvs-studio': ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp'],
            'svace': ['.c', '.cpp', '.cc', '.cxx', '.java'],
            'clang': ['.c', '.cpp', '.cc', '.cxx', '.m', '.mm']
        }

        patterns = file_patterns.get(tool_name, [])

        if not patterns:
            # Если нет специфичных паттернов, считаем все файлы
            count = 0
            for root, dirs, files in os.walk(project_path):
                count += len(files)
            return count

        count = 0
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if any(file.endswith(ext) for ext in patterns):
                    count += 1
        return count