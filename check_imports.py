#!/usr/bin/env python3
"""
Check all imports in the framework
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_import(module_path, class_name=None):
    """Check if a module can be imported"""
    try:
        if class_name:
            exec(f"from {module_path} import {class_name}")
            print(f"✓ {module_path}.{class_name}")
        else:
            exec(f"import {module_path}")
            print(f"✓ {module_path}")
        return True
    except Exception as e:
        print(f"✗ {module_path}{'.' + class_name if class_name else ''}: {e}")
        return False

print("Checking framework imports...")

# Check core modules
check_import("framework.core.config_loader", "ConfigLoader")
check_import("framework.core.test_runner", "RegressionTestRunner")
check_import("framework.core.baseline_manager", "BaselineManager")

# Check normalization modules
check_import("framework.normalization.models", "NormalizedIssue")
check_import("framework.normalization.models", "NormalizedResult")
check_import("framework.normalization.sarif_normalizer", "SARIFNormalizer")
check_import("framework.normalization.tool_parsers.semgrep_parser", "SemgrepParser")
check_import("framework.normalization.tool_parsers.sonarqube_parser", "SonarQubeParser")

# Check module modules
check_import("framework.modules.environment", "EnvironmentManager")
check_import("framework.modules.tool_launcher", "ToolLauncher")
check_import("framework.modules.results_collector", "ResultsCollector")

# Check utils
check_import("framework.utils.logger", "logger")
check_import("framework.utils.docker_utils", "DockerManager")

print("\n" + "="*60)
print("Import check completed")