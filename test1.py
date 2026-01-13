#!/usr/bin/env python3
# run_all_projects.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from framework.core.test_runner import RegressionTestRunner
from framework.core.config_loader import ConfigLoader


def test_all_projects():
    """Тестируем все проекты по очереди для диагностики"""

    config = ConfigLoader().load()

    print("=== ПОЭТАПНОЕ ТЕСТИРОВАНИЕ ПРОЕКТОВ ===")

    all_success = True

    for project in config.projects:
        print(f"\n🧪 Тестируем проект: {project.name} ({project.language})")
        print(f"   Инструменты: {project.analyzers}")
        print(f"   Путь: {project.path}")

        # Проверяем существование проекта
        project_path = Path(project.path)
        if not project_path.exists():
            print(f"   ❌ Папка проекта не существует: {project_path}")
            all_success = False
            continue

        # Считаем файлы
        files = list(project_path.rglob("*"))
        print(f"   Файлов в проекте: {len(files)}")

        # Запускаем тестирование проекта
        runner = RegressionTestRunner()
        if runner.setup():
            success = runner.run_project(project.name, save_baseline=True)
            runner.cleanup()

            if success:
                print(f"   ✅ Проект успешно протестирован")
            else:
                print(f"   ❌ Ошибка при тестировании проекта")
                all_success = False
        else:
            print(f"   ❌ Не удалось инициализировать фреймворк")
            all_success = False

    return all_success


if __name__ == "__main__":
    success = test_all_projects()

    if success:
        print("\n🎉 Все проекты успешно протестированы!")

        # Покажем итоговую статистику
        print("\n=== ИТОГОВАЯ СТАТИСТИКА ===")
        baseline_dir = Path("./baseline")
        if baseline_dir.exists():
            total_issues = 0
            for project_dir in baseline_dir.iterdir():
                if project_dir.is_dir():
                    issues = 0
                    for baseline_file in project_dir.glob("*_baseline.json"):
                        import json

                        with open(baseline_file) as f:
                            data = json.load(f)
                            issues += data.get("issue_count", 0)
                    print(f"📁 {project_dir.name}: {issues} issues")
                    total_issues += issues
            print(f"\n📊 Всего issues: {total_issues}")
    else:
        print("\n⚠ Некоторые проекты завершились с ошибками")
        sys.exit(1)
