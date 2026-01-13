#!/usr/bin/env python3
# analyze_sarif_structure.py

import json
from pathlib import Path


def analyze_sarif_structure(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    print("=== ГЛУБОКИЙ АНАЛИЗ СТРУКТУРЫ SARIF ===")

    runs = data.get('runs', [])
    if not runs:
        print("Нет runs в файле")
        return

    run = runs[0]
    results = run.get('results', [])

    print(f"Всего результатов: {len(results)}")

    for i, result in enumerate(results[:2]):  # Анализируем только первые 2
        print(f"\n--- Результат {i + 1} ---")

        # Рекурсивно выведем всю структуру
        def print_structure(obj, indent=0, max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                print("  " * indent + "...")
                return

            if isinstance(obj, dict):
                for key, value in obj.items():
                    print("  " * indent + f"{key}: ", end="")
                    if isinstance(value, (dict, list)) and value:
                        print()
                        print_structure(value, indent + 1, max_depth, current_depth + 1)
                    else:
                        print(f"{value}")
            elif isinstance(obj, list):
                if obj:
                    print(f"list[{len(obj)}]")
                    if len(obj) > 0:
                        print_structure(obj[0], indent + 1, max_depth, current_depth + 1)

        print_structure(result, max_depth=4)


# Запустим анализ
analyze_sarif_structure("results/raw/simple-test/semgrep.json")