# Временный парсер для диагностики
# Создайте файл debug_parser.py:

# !/usr/bin/env python3
# debug_parser.py

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Загрузим SARIF
with open("results/raw/simple-test/semgrep.json", 'r') as f:
    data = json.load(f)


# Простой парсер
def simple_parse(sarif_data):
    issues = []

    for run in sarif_data.get("runs", []):
        for result in run.get("results", []):
            # Базовые поля
            rule_id = result.get("ruleId", "")
            message = result.get("message", {})
            if isinstance(message, dict):
                message = message.get("text", "")

            # Location
            file_path = ""
            line_number = 0

            locations = result.get("locations", [])
            if locations:
                loc = locations[0]
                if 'physicalLocation' in loc:
                    phys = loc['physicalLocation']
                    if 'artifactLocation' in phys:
                        file_path = phys['artifactLocation'].get('uri', '')
                    if 'region' in phys:
                        line_number = phys['region'].get('startLine', 0)

            # Severity
            severity = result.get("level", "warning").lower()

            if file_path and line_number > 0:
                issues.append({
                    'rule_id': rule_id,
                    'file_path': file_path,
                    'line_number': line_number,
                    'message': message,
                    'severity': severity
                })

    return issues


# Запустим
issues = simple_parse(data)
print(f"Наш простой парсер нашел {len(issues)} issues")
for i, issue in enumerate(issues[:5]):
    print(f"\n{i + 1}. {issue['rule_id']}")
    print(f"   Файл: {issue['file_path']}:{issue['line_number']}")
    print(f"   Сообщение: {issue['message'][:50]}...")