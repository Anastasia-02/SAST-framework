#!/usr/bin/env python3
# full_diagnostic.py

import sys
import os
import json
import subprocess
from pathlib import Path

print("=== ПОЛНАЯ ДИАГНОСТИКА SAST ФРЕЙМВОРКА ===\n")

# 1. Проверим структуру проекта
print("1. СТРУКТУРА ПРОЕКТА:")
project_path = Path("./projects/simple-test")
if project_path.exists():
    print(f"   Папка проекта существует: {project_path}")
    files = list(project_path.glob("*"))
    print(f"   Файлов в проекте: {len(files)}")
    for f in files:
        print(f"   - {f.name} ({f.stat().st_size} байт)")
        if f.name.endswith('.py'):
            print(f"     Первые 200 символов: {f.read_text()[:200]}...")
else:
    print(f"   ОШИБКА: Папка проекта не существует: {project_path}")

# 2. Проверим конфигурацию
print("\n2. КОНФИГУРАЦИЯ:")
config_path = Path("./config/tools.yaml")
if config_path.exists():
    with open(config_path) as f:
        content = f.read()
        if "semgrep" in content:
            print("   Конфигурация Semgrep найдена")
            # Извлечем аргументы semgrep
            import yaml

            config = yaml.safe_load(content)
            semgrep_args = config['tools']['semgrep']['args']
            print(f"   Аргументы Semgrep: {' '.join(semgrep_args)}")
        else:
            print("   ОШИБКА: Конфигурация Semgrep не найдена в tools.yaml")

# 3. Запустим Docker вручную
print("\n3. РУЧНОЙ ЗАПУСК DOCKER:")
test_file = project_path / "test.py"
if test_file.exists():
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{project_path.absolute()}:/src",
        "returntocorp/semgrep:latest",
        "semgrep", "scan",
        "--config", "auto",
        "--json",
        "/src"
    ]

    print(f"   Команда: {' '.join(cmd[:10])}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"   Код возврата: {result.returncode}")

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                issues = len(data.get("results", []))
                print(f"   Semgrep нашел issues: {issues}")

                if issues > 0:
                    print(f"   Первые 3 issues:")
                    for i, r in enumerate(data["results"][:3]):
                        print(f"     {i + 1}. {r.get('check_id', 'Unknown')}")
                        print(f"        {r.get('extra', {}).get('message', 'No message')[:50]}...")
                else:
                    print("   ВНИМАНИЕ: Semgrep не нашел ни одной уязвимости!")

                    # Покажем сырой вывод для отладки
                    print(f"\n   Сырой вывод (первые 500 символов):")
                    print(result.stdout[:500])

            except json.JSONDecodeError:
                print(f"   ОШИБКА: Semgrep вернул не JSON:")
                print(result.stderr[:500] if result.stderr else result.stdout[:500])
        else:
            print(f"   Semgrep не вернул stdout. Stderr: {result.stderr[:500]}")

    except subprocess.TimeoutExpired:
        print("   Таймаут при запуске Docker")
    except Exception as e:
        print(f"   Ошибка: {e}")

# 4. Проверим SARIF файл
print("\n4. ПРОВЕРКА SARIF ФАЙЛА:")
sarif_path = Path("results/raw/simple-test/semgrep.json")
if sarif_path.exists():
    print(f"   SARIF файл существует: {sarif_path}")
    print(f"   Размер: {sarif_path.stat().st_size} байт")

    try:
        with open(sarif_path) as f:
            data = json.load(f)

        print(f"   SARIF версия: {data.get('version')}")

        runs = data.get('runs', [])
        print(f"   Количество runs: {len(runs)}")

        if runs:
            run = runs[0]
            tool = run.get('tool', {}).get('driver', {})
            print(f"   Инструмент: {tool.get('name', 'Unknown')}")
            print(f"   Версия: {tool.get('version', 'Unknown')}")

            results = run.get('results', [])
            print(f"   Количество результатов: {len(results)}")

            if results:
                print(f"   Первый результат:")
                first = results[0]
                print(f"     Rule ID: {first.get('ruleId')}")
                print(f"     Message: {first.get('message', {}).get('text', 'No message')[:50]}...")
            else:
                print("   ВНИМАНИЕ: В SARIF файле НЕТ результатов!")

                # Выведем другие ключи для анализа
                print(f"\n   Другие ключи в run: {list(run.keys())}")

                # Проверим, нет ли результатов в другом месте
                for key in run:
                    if key != 'results' and isinstance(run[key], list):
                        print(f"   {key}: список из {len(run[key])} элементов")

    except json.JSONDecodeError as e:
        print(f"   ОШИБКА: SARIF файл не является валидным JSON: {e}")
    except Exception as e:
        print(f"   ОШИБКА при чтении SARIF: {e}")
else:
    print(f"   ОШИБКА: SARIF файл не существует: {sarif_path}")

print("\n=== ДИАГНОСТИКА ЗАВЕРШЕНА ===")