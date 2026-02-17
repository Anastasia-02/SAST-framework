#!/usr/bin/env python3
"""
Скрипт для создания или обновления baseline.
При повторном запуске без флага --force пропускает уже существующие baseline.
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Создаём директорию для логов
Path("logs").mkdir(exist_ok=True)

# Добавляем корень проекта в путь Python
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Настройка логирования
log_filename = f"logs/baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Импортируем модули фреймворка
try:
    from test_runner import TestRunner
    from normalizer import Normalizer
    import yaml
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    print("❌ Ошибка импорта. Убедитесь, что все зависимости установлены: pip install pyyaml docker")
    sys.exit(1)

def create_baseline(force: bool = False):
    """
    Создаёт baseline для всех проектов из конфигурации.

    Args:
        force: Если True, перезаписывает существующие baseline.
    """
    print("📊 Создание baseline...")
    if force:
        print("   Режим: принудительное обновление (--force)")

    # Убедимся, что нужные директории существуют
    Path("baseline").mkdir(exist_ok=True)
    Path("results/raw").mkdir(parents=True, exist_ok=True)
    Path("results/normalized").mkdir(parents=True, exist_ok=True)

    # Загружаем конфигурацию
    config_path = "config/projects_config.yaml"
    if not Path(config_path).exists():
        print(f"❌ Конфигурационный файл не найден: {config_path}")
        sys.exit(1)

    # Инициализируем тестовый раннер
    runner = TestRunner(config_path)
    normalizer = Normalizer()

    # Загружаем список проектов из конфига
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    projects_config = config.get('projects', {})

    if not projects_config:
        print("❌ В конфигурации нет проектов.")
        sys.exit(1)

    # Статистика
    total_projects = len(projects_config)
    processed_projects = 0
    skipped_projects = 0
    total_tools = 0
    processed_tools = 0
    skipped_tools = 0

    print(f"\n🚀 Анализ существующих baseline...")

    # Сначала соберём информацию о том, какие инструменты нужно запустить
    tools_to_run = {}  # project_name -> list of tool_names
    for project_name, project_info in projects_config.items():
        project_tools = project_info.get('tools', [])
        tools_needed = []
        for tool_name in project_tools:
            baseline_file = Path("baseline") / project_name / f"{tool_name}_baseline.json"
            if baseline_file.exists() and not force:
                logger.info(f"Baseline уже существует: {baseline_file} (пропускаем)")
                skipped_tools += 1
            else:
                tools_needed.append(tool_name)
                if force and baseline_file.exists():
                    logger.info(f"Baseline будет перезаписан: {baseline_file}")
                else:
                    logger.info(f"Будет создан baseline для {project_name}/{tool_name}")
        if tools_needed:
            tools_to_run[project_name] = tools_needed
            processed_projects += 1
        else:
            skipped_projects += 1
        total_tools += len(project_tools)

    if not tools_to_run:
        print("\n✅ Все baseline уже существуют. Для пересоздания используйте флаг --force")
        return

    print(f"\n🚀 Запуск тестирования для создания baseline (проектов: {len(tools_to_run)})...")
    results = runner.run_all_tests()  # запускаем все проекты, но потом выборочно сохраняем

    print("\n📁 Сохранение baseline...")
    baseline_dir = Path("baseline")

    successful_projects = 0
    total_issues = 0

    for project_name, project_info in projects_config.items():
        if project_name not in tools_to_run:
            continue  # этот проект пропущен

        project_tools = tools_to_run[project_name]
        project_has_success = False
        print(f"\n📂 Проект: {project_name}")

        for tool_name in project_tools:
            # Получаем результат из запуска
            result = results.get(project_name, {}).get(tool_name, {})
            if result.get('success'):
                # Нормализуем результаты
                normalized = normalizer.normalize(result['raw_result'])

                # Сохраняем baseline
                project_baseline_dir = baseline_dir / project_name
                project_baseline_dir.mkdir(exist_ok=True)

                baseline_file = project_baseline_dir / f"{tool_name}_baseline.json"

                baseline_data = {
                    'project': project_name,
                    'tool': tool_name,
                    'timestamp': datetime.now().isoformat(),
                    'issues_count': len(normalized),
                    'issues': normalized,
                    'metadata': {
                        'framework_version': '1.0.0',
                        'created_with': 'create_baseline.py'
                    }
                }

                with open(baseline_file, 'w', encoding='utf-8') as f:
                    json.dump(baseline_data, f, indent=2, ensure_ascii=False)

                total_issues += len(normalized)
                project_has_success = True
                processed_tools += 1
                action = "обновлён" if force and Path(baseline_file).exists() else "создан"
                print(f"   ✅ {tool_name}: {len(normalized)} срабатываний → {baseline_file} ({action})")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"   ❌ {tool_name}: ошибка - {error_msg}")

        if project_has_success:
            successful_projects += 1

    # Итоговая статистика
    print("\n" + "=" * 60)
    print("📊 Итоги создания baseline:")
    print(f"   Проектов всего: {total_projects}")
    print(f"   Проектов обработано (требовали обновления): {processed_projects}")
    print(f"   Проектов пропущено (уже есть baseline): {skipped_projects}")
    print(f"   Инструментов всего: {total_tools}")
    print(f"   Инструментов обработано: {processed_tools}")
    print(f"   Инструментов пропущено: {skipped_tools}")
    print(f"   Всего срабатываний сохранено: {total_issues}")
    print(f"   Логи сохранены: {log_filename}")
    print("=" * 60)

    if processed_tools == 0:
        print("\n⚠️  Baseline не обновлён: все baseline уже существуют. Для пересоздания используйте --force")
    else:
        print("\n✅ Baseline успешно создан/обновлён!")
        print("   Теперь можно запускать сравнение с помощью run_comparison.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создание эталонных результатов (baseline)")
    parser.add_argument("-f", "--force", action="store_true", help="Принудительно пересоздать baseline, даже если они уже существуют")
    args = parser.parse_args()
    create_baseline(force=args.force)