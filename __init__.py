"""
SAST Framework - Framework for SAST tools regression testing
"""

__version__ = "1.0.0"
__author__ = "Student"

from test_runner import TestRunner
from comparer import Comparer
from normalizer import Normalizer
from environment import Environment
from performance_metrics import PerformanceCollector
from tools_registry import ToolsRegistry

__all__ = [
    'TestRunner',
    'Comparer',
    'Normalizer',
    'Environment',
    'PerformanceCollector',
    'ToolsRegistry'
]