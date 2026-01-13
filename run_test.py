#!/usr/bin/env python3
"""
Simplified test script to verify the framework works
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Проверяем наличие необходимых директорий
config_dir = Path("./config")
if not config_dir.exists():
    print("Creating config directory...")
    config_dir.mkdir(parents=True)

    # Создаем минимальную конфигурацию
    (config_dir / "projects.yaml").write_text("""projects:
  - name: "test-project"
    path: "./projects/test"
    language: "python"
    analyzers: ["semgrep"]
""")

    (config_dir / "tools.yaml").write_text("""tools:
  semgrep:
    type: "docker"
    image: "returntocorp/semgrep"
    version: "latest"
    command: "semgrep"
    args:
      - "scan"
      - "--sarif"
      - "--quiet"
      - "-o"
      - "{output_file}"
      - "{project_path}"
    mount_point: "/src"
    env_vars: {}
""")

# Проверяем наличие projects директории
projects_dir = Path("./projects/test")
projects_dir.mkdir(parents=True, exist_ok=True)

# Создаем простой тестовый файл для проверки
test_file = projects_dir / "test.py"
test_file.write_text("""
# Test file for SAST scanning
import os

def insecure_function(password):
    # Hardcoded password - security issue
    secret = "password123"
    return password == secret

def sql_injection(user_input):
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_input
    return query

# Command injection vulnerability
def run_command(cmd):
    os.system(cmd)
""")

print("Testing framework imports...")

try:
    from framework.utils.logger import setup_logger, logger
    from framework.core.config_loader import ConfigLoader
    from framework.normalization.models import NormalizedIssue, NormalizedResult

    print("✓ All imports successful")

    # Test configuration loading
    print("\nTesting configuration loader...")
    config_loader = ConfigLoader("./config")
    config = config_loader.load()

    print(f"✓ Loaded {len(config.projects)} projects")
    print(f"✓ Loaded {len(config.tools)} tools")

    # Test model creation
    print("\nTesting model creation...")
    issue = NormalizedIssue(
        tool="test",
        rule_id="test-rule",
        file_path="test.py",
        line_number=10,
        severity="warning",
        message="Test issue"
    )
    print(f"✓ Created NormalizedIssue with id: {issue.id}")
    print(f"  Tool: {issue.tool}")
    print(f"  Rule ID: {issue.rule_id}")
    print(f"  File: {issue.file_path}:{issue.line_number}")
    print(f"  Severity: {issue.severity}")

    result = NormalizedResult(
        tool="test-tool",
        project="test-project",
        issues=[issue]
    )
    print(f"✓ Created NormalizedResult with {result.issue_count} issues")

    print("\n" + "=" * 60)
    print("FRAMEWORK IS WORKING CORRECTLY!")
    print("=" * 60)
    print("\nTo run the full framework:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Update config files in ./config/")
    print("3. Add test projects to ./projects/")
    print("4. Run: python -m framework.main list-projects")

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nMake sure you have installed all dependencies:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)