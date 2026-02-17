#!/usr/bin/env python3
"""
Скрипт для запуска полного цикла тестирования и сравнения с эталоном
"""

import sys
import json
from pathlib import Path
import logging
from datetime import datetime

# Добавляем корневую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Основная функция запуска сравнения"""

    # 1. Сначала создаем все необходимые директории
    print("📁 Создание необходимых директорий...")
    Path("logs").mkdir(exist_ok=True)
    Path("results/comparison").mkdir(parents=True, exist_ok=True)
    Path("results/metrics").mkdir(parents=True, exist_ok=True)
    Path("results/raw").mkdir(parents=True, exist_ok=True)
    Path("results/normalized").mkdir(parents=True, exist_ok=True)
    Path("baseline").mkdir(exist_ok=True)

    # 2. Настраиваем логирование ПОСЛЕ создания директорий
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

    print(f"📝 Логирование настроено: {log_filename}")
    print("🚀 Запуск полного цикла тестирования и сравнения")

    # 3. Импортируем модули после настройки логирования
    try:
        from test_runner import TestRunner
        from comparer import Comparer
        from performance_metrics import PerformanceCollector
        import yaml

    except ImportError as e:
        logger.error(f"Ошибка импорта модулей: {e}")
        print(f"❌ Ошибка импорта модулей: {e}")
        print("Убедитесь, что все зависимости установлены:")
        print("pip install pyyaml")
        sys.exit(1)

    try:
        # 1. Запускаем тестирование
        print("\n📊 Шаг 1: Запуск тестирования проектов...")
        config_path = "config/projects_config.yaml"

        if not Path(config_path).exists():
            logger.error(f"Конфигурационный файл не найден: {config_path}")
            print(f"❌ Конфигурационный файл не найден: {config_path}")
            print("Создайте файл config/projects_config.yaml")
            sys.exit(1)

        runner = TestRunner(config_path)
        test_results = runner.run_all_tests()

        if not test_results:
            logger.warning("Нет результатов тестирования")
            print("⚠️  Нет результатов тестирования")
        else:
            logger.info(f"Тестирование завершено. Проектов: {len(test_results)}")
            print(f"✅ Тестирование завершено. Проектов: {len(test_results)}")

            # Выводим краткую статистику
            for project_name, tools_results in test_results.items():
                success_tools = [t for t, r in tools_results.items() if r.get('success')]
                issues_total = sum(r.get('issues_count', 0) for r in tools_results.values() if r.get('success'))
                print(
                    f"   {project_name}: {len(success_tools)}/{len(tools_results)} инструментов, {issues_total} срабатываний")

    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}", exc_info=True)
        print(f"❌ Ошибка при тестировании: {e}")
        sys.exit(1)

    # 2. Сравниваем результаты с эталоном
    print("\n📊 Шаг 2: Сравнение результатов с эталоном...")
    comparer = Comparer()

    try:
        # Загружаем конфигурацию проектов
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        comparison_results = comparer.compare_all(config)

        if not comparison_results:
            logger.warning("Нет результатов для сравнения")
            print("⚠️  Нет результатов для сравнения")
        else:
            # Генерируем отчеты
            summary = comparer.generate_summary_report()
            comparer.generate_detailed_report()

            print("\n📋 Сводка сравнения:")
            print("=" * 60)

            for project_name, project_results in comparison_results.items():
                print(f"\n📁 Проект: {project_name}")
                print("-" * 40)

                for tool_name, result in project_results.items():
                    recall_pct = result.metrics.get('recall_percentage', 0)
                    fp_delta = result.metrics.get('fp_delta', 0)
                    f1_score = result.metrics.get('f1_score', 0)

                    # Определяем статус
                    if recall_pct >= 90:
                        status = "✅"
                    elif recall_pct >= 70:
                        status = "⚠️ "
                    else:
                        status = "❌"

                    print(f"   {status} Инструмент: {tool_name}")
                    print(f"      📊 Полнота (recall): {recall_pct:.1f}%")
                    print(f"      🔍 Совпадений: {result.matched_issues}/{result.baseline_issues}")
                    print(f"      🆕 Новые: {result.new_issues}")
                    print(f"      🚫 Пропущенные: {result.missing_issues}")
                    print(f"      📈 Дельта FP: {fp_delta:+d}")
                    print(f"      ⚖️  F1-мера: {f1_score:.3f}")
                    print(f"      📁 Baseline: {result.baseline_issues}, Current: {result.current_issues}")
                    print()

            print("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка при сравнении: {e}", exc_info=True)
        print(f"❌ Ошибка при сравнении: {e}")

    # 3. Анализируем метрики производительности
    print("\n📊 Шаг 3: Анализ метрик производительности...")
    perf_collector = PerformanceCollector()

    try:
        perf_report = perf_collector.generate_performance_report()

        if perf_report and 'tools_performance' in perf_report:
            print("\n⏱️  Метрики производительности:")
            print("=" * 60)

            for tool, metrics in perf_report['tools_performance'].items():
                avg_time = metrics.get('avg_execution_time', 0)
                avg_issues = metrics.get('avg_issues_found', 0)
                issues_per_sec = avg_issues / avg_time if avg_time > 0 else 0

                print(f"\n   🛠️  {tool}:")
                print(f"      Среднее время: {avg_time:.1f} сек")
                print(f"      Среднее срабатываний: {avg_issues:.0f}")
                print(f"      Скорость: {issues_per_sec:.1f} срабатываний/сек")

                # Показываем лучший и худший запуск
                best = metrics.get('best_run', {})
                worst = metrics.get('worst_run', {})

                if best:
                    print(f"      🏆 Лучший запуск: {best.get('execution_time', 0):.1f} сек")
                if worst:
                    print(f"      🐌 Худший запуск: {worst.get('execution_time', 0):.1f} сек")

            print("=" * 60)
        else:
            print("ℹ️  Нет данных о производительности")

        # Показываем рекомендации
        recommendations = perf_report.get('recommendations', []) if perf_report else []
        if recommendations:
            print("\n💡 Рекомендации по производительности:")
            for rec in recommendations:
                severity = rec.get('severity', 'info').upper()
                message = rec.get('message', '')
                print(f"   [{severity}] {message}")

    except Exception as e:
        logger.error(f"Ошибка при анализе метрик: {e}", exc_info=True)
        print(f"❌ Ошибка при анализе метрик: {e}")

    # 4. Сохраняем итоговый отчет
    print("\n📊 Шаг 4: Формирование итогового отчета...")
    try:
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "test_results_summary": {},
            "comparison_summary": {},
            "performance_summary": {},
            "metadata": {
                "framework_version": "1.0.0",
                "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        # Собираем статистику по тестированию
        for project_name, tools_results in test_results.items():
            final_report["test_results_summary"][project_name] = {}

            for tool_name, data in tools_results.items():
                final_report["test_results_summary"][project_name][tool_name] = {
                    "success": data.get('success', False),
                    "issues_count": data.get('issues_count', 0),
                    "has_error": 'error' in data,
                    "error_message": data.get('error', None)
                }

        # Собираем статистику по сравнению
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
                        "f1_score": result.metrics.get('f1_score', 0),
                        "status": "good" if result.metrics.get('recall_percentage', 0) >= 90 else
                        "warning" if result.metrics.get('recall_percentage', 0) >= 70 else
                        "bad"
                    }

        # Добавляем метрики производительности
        if perf_report and 'tools_performance' in perf_report:
            final_report["performance_summary"] = {}

            for tool, metrics in perf_report['tools_performance'].items():
                final_report["performance_summary"][tool] = {
                    "avg_execution_time": metrics.get('avg_execution_time', 0),
                    "avg_issues_found": metrics.get('avg_issues_found', 0),
                    "total_runs": metrics.get('total_runs', 0)
                }

        # Сохраняем отчет
        final_report_path = "results/final_report.json"
        with open(final_report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)

        print(f"✅ Итоговый отчет сохранен: {final_report_path}")

        # Показываем краткую сводку
        print("\n📈 Краткая сводка:")
        print("=" * 60)

        total_projects = len(final_report.get("test_results_summary", {}))
        successful_tools = 0
        total_tools = 0

        for project, tools in final_report.get("test_results_summary", {}).items():
            for tool, data in tools.items():
                total_tools += 1
                if data.get("success"):
                    successful_tools += 1

        print(f"   Проектов протестировано: {total_projects}")
        print(f"   Инструментов выполнено: {successful_tools}/{total_tools}")

        if comparison_results:
            avg_recall = 0
            count = 0
            for project, tools in final_report.get("comparison_summary", {}).items():
                for tool, data in tools.items():
                    avg_recall += data.get("recall_percentage", 0)
                    count += 1

            if count > 0:
                avg_recall /= count
                print(f"   Средняя полнота: {avg_recall:.1f}%")

        print("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка при создании итогового отчета: {e}", exc_info=True)
        print(f"❌ Ошибка при создании итогового отчета: {e}")

    print("\n🎉 Процесс сравнения завершен!")
    print(f"📁 Результаты сохранены в директории: results/")
    print(f"📝 Логи сохранены в файле: {log_filename}")


if __name__ == "__main__":
    main()