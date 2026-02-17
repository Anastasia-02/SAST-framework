import time
import logging
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

# Используем абсолютные импорты внутри пакета (рекомендуется)
from environment import Environment
from normalizer import Normalizer
from tools_registry import ToolsRegistry
from performance_metrics import PerformanceCollector

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)


class TestRunner:
    def __init__(self, config_path: str):
        """
        Инициализация TestRunner.

        Args:
            config_path: Путь к файлу конфигурации проектов (YAML).
        """
        self.config_path = config_path
        self.config = self._load_config()                # загружаем конфигурацию
        self.environment = Environment()                  # для управления Docker и временными файлами
        self.normalizer = Normalizer()                    # для нормализации результатов
        self.tools_registry = ToolsRegistry()             # реестр доступных инструментов
        self.performance_collector = PerformanceCollector()
        self.timers = {}                                   # для замера времени выполнения

    def _load_config(self) -> Dict:
        """Загружает конфигурацию из YAML-файла."""
        import yaml
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {self.config_path}")
        return config

    def run_test(self, project_name: str, project_info: Dict) -> Dict:
        """
        Запускает тестирование одного проекта.

        Args:
            project_name: Имя проекта.
            project_info: Словарь с информацией о проекте (путь, язык, инструменты).

        Returns:
            Dict: Результаты для каждого инструмента.
        """
        try:
            logger.info(f"Starting testing for project: {project_name}")

            # Подготовка окружения (создание папок, проверка Docker)
            self.environment.setup()

            results = {}
            project_path = project_info['path']

            # Запуск каждого инструмента
            for tool_name in project_info['tools']:
                logger.info(f"  Running {tool_name}...")

                try:
                    # Запускаем таймер для метрик производительности
                    self.timers[(project_name, tool_name)] = (
                        self.performance_collector.start_timer(tool_name, project_name)
                    )

                    # Получаем экземпляр инструмента из реестра
                    tool = self.tools_registry.get_tool(tool_name)  # было self.tools.get — исправлено
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
            # Очистка окружения в любом случае
            self.environment.cleanup()

    def _count_files_in_project(self, project_path: str, tool_name: str) -> int:
        """
        Подсчитывает количество файлов, подходящих для сканирования указанным инструментом.

        Args:
            project_path: Путь к проекту.
            tool_name: Имя инструмента.

        Returns:
            int: Количество подходящих файлов.
        """
        # Расширения файлов для разных инструментов
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

        # Считаем только файлы с нужными расширениями
        count = 0
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if any(file.endswith(ext) for ext in patterns):
                    count += 1
        return count