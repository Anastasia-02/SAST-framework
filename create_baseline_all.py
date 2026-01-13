#!/usr/bin/env python3
# create_baseline_all.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from framework.core.test_runner import RegressionTestRunner
from framework.core.baseline_manager import BaselineManager
from framework.utils.logger import logger
import json


def create_baseline_for_all():
    """Создать baseline для всех проектов"""

    print("=== СОЗДАНИЕ БАЗОВЫХ ЛИНИЙ ДЛЯ ВСЕХ ПРОЕКТОВ ===")

    runner = RegressionTestRunner()

    if not runner.setup():
        print("❌ Не удалось инициализировать фреймворк")
        return False

    try:
        # Запускаем все проекты с сохранением baseline
        success = runner.run_all(save_baseline=True)

        if success:
            print("\n✅ Baseline успешно созданы для всех проектов")

            # Создаем summary отчет
            baseline_dir = Path("./baseline")
            manager = BaselineManager(baseline_dir)
            summary = manager.generate_baseline_summary()

            print("\n=== СВОДКА ПО BASELINE ===")
            for project_name, project_data in summary["projects"].items():
                print(f"\n📁 Проект: {project_name}")
                print(f"   Всего уязвимостей: {project_data['total_issues']}")

                for tool_name, tool_data in project_data["tools"].items():
                    print(f"   🔧 {tool_name}: {tool_data['issue_count']} issues")
                    print(f"      По серьезности: {tool_data['by_severity']}")

            # Сохраняем сводку в файл
            summary_file = baseline_dir / "baseline_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            print(f"\n📊 Полная сводка сохранена в: {summary_file}")

            return True
        else:
            print("\n⚠ Создание baseline завершилось с предупреждениями")
            return False

    except Exception as e:
        print(f"❌ Ошибка при создании baseline: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        runner.cleanup()


if __name__ == "__main__":
    success = create_baseline_for_all()
    sys.exit(0 if success else 1)