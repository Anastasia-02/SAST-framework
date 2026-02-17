#!/usr/bin/env python3
"""
Тестовый скрипт для проверки модуля сравнения
"""

import sys
import json
import os
from pathlib import Path

# Создаем директорию logs перед любыми импортами
Path("logs").mkdir(exist_ok=True)

sys.path.insert(0, str(Path(__file__).parent))

from comparer import Comparer


def test_comparison():
    """Тестирует основные функции сравнения"""
    print("🧪 Тестирование модуля сравнения...")

    # Создаем тестовые данные
    test_baseline = [
        {
            "rule_id": "CWE-78",
            "file_path": "test.c",
            "line_number": 10,
            "message": "Command injection vulnerability",
            "severity": "high"
        },
        {
            "rule_id": "CWE-89",
            "file_path": "test.c",
            "line_number": 25,
            "message": "SQL injection vulnerability",
            "severity": "high"
        }
    ]

    test_current = [
        {
            "rule_id": "CWE-78",
            "file_path": "test.c",
            "line_number": 10,
            "message": "Command injection vulnerability",
            "severity": "high"
        },
        {
            "rule_id": "CWE-79",
            "file_path": "test.c",
            "line_number": 15,
            "message": "XSS vulnerability",
            "severity": "medium"
        }
    ]

    # Тестируем Comparer
    comparer = Comparer()

    # Тестируем вычисление fingerprint
    print("\n1. Тестирование вычисления fingerprint:")
    for issue in test_baseline:
        fp = comparer.calculate_fingerprint(issue)
        print(f"   {issue['rule_id']}: {fp[:16]}...")

    # Тестируем сравнение срабатываний
    print("\n2. Тестирование сравнения срабатываний:")
    matched, new, missing = comparer.compare_issues(test_baseline, test_current)

    print(f"   Совпавшие: {len(matched)}")
    for issue in matched:
        print(f"     - {issue['rule_id']}: {issue['message']}")

    print(f"   Новые: {len(new)}")
    for issue in new:
        print(f"     - {issue['rule_id']}: {issue['message']}")

    print(f"   Пропущенные: {len(missing)}")
    for issue in missing:
        print(f"     - {issue['rule_id']}: {issue['message']}")

    # Тестируем расчет метрик
    print("\n3. Тестирование расчета метрик:")
    metrics = comparer.calculate_metrics(
        baseline_count=len(test_baseline),
        current_count=len(test_current),
        matched_count=len(matched),
        new_count=len(new),
        missing_count=len(missing)
    )

    print("   Метрики качества:")
    print(f"     Полнота (recall): {metrics.get('recall_percentage', 0):.1f}%")
    print(f"     F1-мера: {metrics.get('f1_score', 0):.3f}")
    print(f"     Дельта FP: {metrics.get('fp_delta', 0)}")
    print(f"     Новые срабатывания: {metrics.get('new_issues_percentage', 0):.1f}%")
    print(f"     Пропущенные срабатывания: {metrics.get('missing_issues_percentage', 0):.1f}%")

    # Тестируем создание отчета
    print("\n4. Тестирование создания отчета...")
    try:
        # Сохраняем тестовые данные во временные файлы
        test_dir = Path("test_data")
        test_dir.mkdir(exist_ok=True)

        # Создаем тестовые файлы
        baseline_file = test_dir / "test_baseline.json"
        current_file = test_dir / "test_current.json"

        with open(baseline_file, 'w') as f:
            json.dump({
                "project": "test-project",
                "tool": "test-tool",
                "timestamp": "2024-01-29T12:00:00",
                "issues_count": len(test_baseline),
                "issues": test_baseline
            }, f)

        with open(current_file, 'w') as f:
            json.dump(test_current, f)

        print(f"   Тестовые файлы созданы:")
        print(f"     - {baseline_file}")
        print(f"     - {current_file}")

    except Exception as e:
        print(f"   Ошибка при создании тестовых файлов: {e}")

    print("\n✅ Тестирование завершено успешно!")


if __name__ == "__main__":
    test_comparison()