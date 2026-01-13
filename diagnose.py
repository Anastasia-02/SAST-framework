#!/usr/bin/env python3
# diagnose.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from framework.core.config_loader import ConfigLoader
import subprocess
import json

print("=== ДИАГНОСТИКА SAST ФРЕЙМВОРКА ===")

# 1. Проверка конфигурации
print("\n1. Проверка конфигурации...")
config = ConfigLoader().load()
semgrep_config = config.tools.get("semgrep")
print(f"   Конфигурация Semgrep: {semgrep_config.command} {' '.join(semgrep_config.args)}")

# 2. Проверка тестового проекта
print("\n2. Проверка тестового проекта...")
project = config.get_project_config("simple-test")
if project:
    project_path = Path(project.path)
    print(f"   Путь проекта: {project_path}")
    print(f"   Существует: {project_path.exists()}")
    if project_path.exists():
        py_files = list(project_path.glob("*.py"))
        print(f"   Python файлов: {len(py_files)}")
        for f in py_files:
            print(f"     - {f.name} ({f.stat().st_size} bytes)")

# 3. Запуск Semgrep вручную
print("\n3. Запуск Semgrep вручную...")
test_file = project_path / "guaranteed_vulns.py"
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

    print(f"   Команда: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            issues = len(data.get("results", []))
            print(f"   Semgrep нашел issues: {issues}")
            if issues > 0:
                for i, r in enumerate(data["results"][:3]):
                    print(f"     {i + 1}. {r.get('check_id')}: {r.get('extra', {}).get('message')}")
            else:
                print("   Внимание: Semgrep не нашел уязвимостей!")
                print("   Стандартный вывод:", result.stdout[:500])
        else:
            print(f"   Ошибка Semgrep: {result.stderr}")
    except Exception as e:
        print(f"   Ошибка при запуске: {e}")
else:
    print(f"   Файл {test_file} не найден!")

print("\n=== ДИАГНОСТИКА ЗАВЕРШЕНА ===")