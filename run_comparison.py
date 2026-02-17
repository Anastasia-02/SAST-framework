#!/usr/bin/env python3
"""
Скрипт для запуска полного цикла тестирования и сравнения с эталоном.
Выводит отчёт с метриками: полнота, дельта FP, время анализа.
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Создаём необходимые директории
Path("logs").mkdir(exist_ok=True)
Path("results/comparison").mkdir(parents=True, exist_ok=True)
Path("results/metrics").mkdir(parents=True, exist_ok=True)

# Настройка логирования
log_filename = f"logs/comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Добавляем корень проекта в путь Python
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Импорты модулей фреймворка
try:
    from test_runner import TestRunner
    from comparer import Comparer
    from performance_metrics import PerformanceCollector
    import yaml
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    print("❌ Ошибка импорта. Убедитесь, что все зависимости установлены: pip install pyyaml docker")
    sys.exit(1)

def main(force_baseline: bool = False):
    """Основная функция запуска сравнения."""
    print("🚀 Запуск полного цикла тестирования и сравнения")

    # Шаг 1: Запуск тестирования проектов
    print("\n📊 Шаг 1: Запуск тестирования проектов...")
    config_path = "config/projects_config.yaml"
    if not Path(config_path).exists():
        logger.error(f"Конфигурационный файл не найден: {config_path}")
        sys.exit(1)

    runner = TestRunner(config_path)
    test_results = runner.run_all_tests()

    if not test_results:
        logger.warning("Нет результатов тестирования")
        print("⚠️  Нет результатов тестирования")
        return

    # Шаг 2: Сравнение с эталоном
    print("\n📊 Шаг 2: Сравнение результатов с эталоном...")
    comparer = Comparer()
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    comparison_results = comparer.compare_all(config)

    if not comparison_results:
        logger.warning("Нет результатов для сравнения")
        print("⚠️  Нет результатов для сравнения")
    else:
        # Генерация отчётов (JSON)
        summary = comparer.generate_summary_report()
        comparer.generate_detailed_report()

        # Вывод сводки с тремя ключевыми метриками
        print("\n📋 Сводка сравнения (ключевые метрики):")
        print("=" * 80)
        for project_name, project_results in comparison_results.items():
            print(f"\n📁 Проект: {project_name}")
            print("-" * 60)
            for tool_name, result in project_results.items():
                recall = result.metrics.get('recall_percentage', 0)
                fp_delta = result.metrics.get('fp_delta', 0)
                f1 = result.metrics.get('f1_score', 0)

                # Извлекаем время выполнения из test_results
                exec_time = None
                if project_name in test_results and tool_name in test_results[project_name]:
                    perf = test_results[project_name][tool_name].get('performance')
                    if perf:
                        # PerformanceMetrics может быть объектом или dict
                        if hasattr(perf, 'execution_time'):
                            exec_time = perf.execution_time
                        elif isinstance(perf, dict):
                            exec_time = perf.get('execution_time')
                        else:
                            exec_time = None

                status = "✅" if recall >= 90 else "⚠️" if recall >= 70 else "❌"
                print(f"   {status} Инструмент: {tool_name}")
                print(f"      📊 Полнота (recall): {recall:.1f}%")
                fp_display = f"{fp_delta:+d}" if fp_delta != 0 else "0"
                print(f"      📈 Дельта FP: {fp_display}")
                if exec_time is not None:
                    print(f"      ⏱️  Время анализа: {exec_time:.2f} сек")
                else:
                    print(f"      ⏱️  Время анализа: N/A")
                print(f"      🔍 Совпадений: {result.matched_issues}/{result.baseline_issues}")
                print(f"      🆕 Новые: {result.new_issues}, 🚫 Пропущенные: {result.missing_issues}")
                print(f"      ⚖️  F1-мера: {f1:.3f}")
                print()

        # Итоговая таблица
        print("\n📊 Итоговая таблица метрик:")
        print("┌─────────────────────┬──────────────┬────────────┬─────────────┬─────────────┐")
        print("│ Проект              │ Инструмент   │ Полнота(%) │ Дельта FP   │ Время (сек) │")
        print("├─────────────────────┼──────────────┼────────────┼─────────────┼─────────────┤")

        for project_name, project_results in comparison_results.items():
            for tool_name, result in project_results.items():
                recall = f"{result.metrics.get('recall_percentage', 0):.1f}"
                fp_delta_val = result.metrics.get('fp_delta', 0)
                fp = f"{fp_delta_val:+d}" if fp_delta_val != 0 else "0"
                exec_time = "N/A"
                if project_name in test_results and tool_name in test_results[project_name]:
                    perf = test_results[project_name][tool_name].get('performance')
                    if perf:
                        if hasattr(perf, 'execution_time'):
                            exec_time = f"{perf.execution_time:.2f}"
                        elif isinstance(perf, dict) and 'execution_time' in perf:
                            exec_time = f"{perf['execution_time']:.2f}"
                # Обрезаем длинные имена, чтобы таблица не разъезжалась
                project_short = project_name[:19] if len(project_name) > 19 else project_name
                tool_short = tool_name[:12] if len(tool_name) > 12 else tool_name
                print(f"│ {project_short:<19} │ {tool_short:<12} │ {recall:>10} │ {fp:>11} │ {exec_time:>11} │")

        print("└─────────────────────┴──────────────┴────────────┴─────────────┴─────────────┘")

    # Шаг 3: Анализ метрик производительности
    print("\n📊 Шаг 3: Анализ метрик производительности...")
    perf_collector = PerformanceCollector()
    perf_report = perf_collector.generate_performance_report()

    if perf_report and 'tools_performance' in perf_report:
        print("\n⏱️  Метрики производительности (средние по всем запускам):")
        print("=" * 60)
        for tool, metrics in perf_report['tools_performance'].items():
            avg_time = metrics.get('avg_execution_time', 0)
            avg_issues = metrics.get('avg_issues_found', 0)
            print(f"   🛠️  {tool}:")
            print(f"      Среднее время сканирования: {avg_time:.2f} сек")
            print(f"      Среднее количество срабатываний: {avg_issues:.1f}")
            if avg_time > 0:
                print(f"      Скорость: {avg_issues/avg_time:.2f} срабатываний/сек")
        print("=" * 60)

    # Шаг 4: Сохранение итогового отчёта
    print("\n📊 Шаг 4: Формирование итогового отчёта...")
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "test_results_summary": {},
        "comparison_summary": {},
        "performance_summary": perf_report.get('tools_performance', {}) if perf_report else {}
    }
    for project_name, tools_results in test_results.items():
        final_report["test_results_summary"][project_name] = {}
        for tool_name, data in tools_results.items():
            perf = data.get('performance')
            exec_time = None
            if perf:
                if hasattr(perf, 'execution_time'):
                    exec_time = perf.execution_time
                elif isinstance(perf, dict):
                    exec_time = perf.get('execution_time')
            final_report["test_results_summary"][project_name][tool_name] = {
                "success": data.get('success', False),
                "issues_count": data.get('issues_count', 0),
                "execution_time": exec_time
            }
    if comparison_results:
        for project_name, project_results in comparison_results.items():
            final_report["comparison_summary"][project_name] = {}
            for tool_name, result in project_results.items():
                final_report["comparison_summary"][project_name][tool_name] = {
                    "recall_percentage": result.metrics.get('recall_percentage', 0),
                    "fp_delta": result.metrics.get('fp_delta', 0),
                    "matched": result.matched_issues,
                    "new": result.new_issues,
                    "missing": result.missing_issues,
                    "f1_score": result.metrics.get('f1_score', 0)
                }

    final_report_path = "results/final_report.json"
    with open(final_report_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    print(f"✅ Итоговый отчёт сохранён: {final_report_path}")
    print(f"📝 Логи сохранены в файле: {log_filename}")
    print("\n🎉 Процесс сравнения завершен!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск полного цикла тестирования и сравнения")
    parser.add_argument("--force", action="store_true", help="Принудительно пересоздать baseline перед сравнением")
    args = parser.parse_args()
    main(force_baseline=args.force)