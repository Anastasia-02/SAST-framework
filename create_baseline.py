#!/usr/bin/env python3
"""
Скрипт для создания или обновления baseline
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Создаем директорию logs перед импортами
Path("logs").mkdir(exist_ok=True)

# Добавляем корневую директорию в путь Python
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Настраиваем логирование
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

try:
    from test_runner import TestRunner
    from normalizer import Normalizer
    import yaml
except ImportError as e:
    logger.error(f"Import error: {e}")
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что установлены все зависимости: pip install pyyaml docker")
    sys.exit(1)


def create_baseline():
    """Создает baseline для всех проектов"""
    print("📊 Создание baseline...")

    # Создаем необходимые директории
    Path("baseline").mkdir(exist_ok=True)
    Path("results/raw").mkdir(parents=True, exist_ok=True)
    Path("results/normalized").mkdir(parents=True, exist_ok=True)

    # Загружаем конфигурацию
    config_path = "config/projects_config.yaml"

    if not Path(config_path).exists():
        print(f"❌ Конфигурационный файл не найден: {config_path}")
        print("Создайте файл config/projects_config.yaml с конфигурацией проектов")
        sys.exit(1)

    # Инициализируем тестовый раннер
    runner = TestRunner(config_path)
    normalizer = Normalizer()

    # Запускаем тестирование всех проектов
    print("\n🚀 Запуск тестирования для создания baseline...")
    results = runner.run_all_tests()

    if not results:
        print("❌ Нет результатов тестирования. Проверьте конфигурацию и доступность инструментов.")
        sys.exit(1)

    print("\n📁 Сохранение baseline...")
    baseline_dir = Path("baseline")

    successful_projects = 0
    total_issues = 0

    for project_name, tools_results in results.items():
        print(f"\n📂 Проект: {project_name}")

        project_has_success = False

        for tool_name, result in tools_results.items():
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
                print(f"   ✅ {tool_name}: {len(normalized)} срабатываний → {baseline_file}")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"   ❌ {tool_name}: ошибка - {error_msg}")

        if project_has_success:
            successful_projects += 1

    print("\n" + "=" * 60)
    print("📊 Итоги создания baseline:")
    print(f"   Проектов успешно обработано: {successful_projects}/{len(results)}")
    print(f"   Всего срабатываний сохранено: {total_issues}")
    print(f"   Логи сохранены: {log_filename}")
    print("=" * 60)

    if successful_projects == 0:
        print("\n⚠️  Внимание: baseline не создан!")
        print("   Возможные причины:")
        print("   1. Нет конфигурационного файла projects_config.yaml")
        print("   2. Инструменты не установлены или не настроены")
        print("   3. Пути к проектам неверны")
        print("   4. Docker не запущен (для инструментов, использующих Docker)")
        sys.exit(1)
    else:
        print("\n✅ Baseline успешно создан!")
        print("   Теперь можно запускать сравнение с помощью run_comparison.py")


if __name__ == "__main__":
    create_baseline()