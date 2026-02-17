"""
Registry для управления инструментами SAST
"""

import logging
from typing import Dict, Optional
from .tools.semgrep import SemgrepTool
from .tools.cppcheck import CppcheckTool
from .tools.shellcheck import ShellcheckTool

logger = logging.getLogger(__name__)


class ToolsRegistry:
    """Registry для управления и доступа к инструментам SAST"""

    def __init__(self):
        self.tools: Dict[str, any] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Регистрирует инструменты по умолчанию"""
        # Регистрируем доступные инструменты
        default_tools = [
            SemgrepTool(),
            CppcheckTool(),
            ShellcheckTool()
        ]

        for tool in default_tools:
            self.register_tool(tool)
            logger.info(f"Registered tool: {tool.name}")

    def register_tool(self, tool):
        """
        Регистрирует новый инструмент

        Args:
            tool: Экземпляр инструмента
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, tool_name: str):
        """
        Получает инструмент по имени

        Args:
            tool_name: Имя инструмента

        Returns:
            Инструмент или None если не найден
        """
        tool = self.tools.get(tool_name)
        if not tool:
            logger.warning(f"Tool not found: {tool_name}")
            logger.info(f"Available tools: {list(self.tools.keys())}")
        return tool

    def list_tools(self):
        """
        Возвращает список всех зарегистрированных инструментов

        Returns:
            List[str]: Список имен инструментов
        """
        return list(self.tools.keys())

    def is_tool_available(self, tool_name: str) -> bool:
        """
        Проверяет, доступен ли инструмент

        Args:
            tool_name: Имя инструмента

        Returns:
            bool: True если инструмент доступен
        """
        return tool_name in self.tools

    def get_tool_config(self, tool_name: str, config: Dict) -> Dict:
        """
        Получает конфигурацию для инструмента

        Args:
            tool_name: Имя инструмента
            config: Общая конфигурация

        Returns:
            Dict: Конфигурация инструмента
        """
        tool_config = config.get('tools_config', {}).get(tool_name, {})
        return tool_config or {}