"""
Normalizer for SAST tool results
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Normalizer:
    """Нормализует результаты разных SAST-инструментов к единому формату"""

    def __init__(self):
        self.normalized_fields = [
            "rule_id",
            "file_path",
            "line_number",
            "severity",
            "message",
            "partialFingerprints"
        ]

    def normalize(self, sarif_data: Dict, execution_time: Optional[float] = None) -> List[Dict]:
        """
        Нормализует SARIF данные в единый формат

        Args:
            sarif_data: SARIF данные от инструмента
            execution_time: Время выполнения инструмента

        Returns:
            List[Dict]: Нормализованные срабатывания
        """
        normalized_issues = []

        try:
            # Проверяем структуру SARIF
            if not isinstance(sarif_data, dict):
                logger.error(f"Invalid SARIF data type: {type(sarif_data)}")
                return []

            # Получаем runs из SARIF
            runs = sarif_data.get("runs", [])
            if not runs:
                logger.warning("No runs in SARIF data")
                return []

            # Обрабатываем каждый run
            for run in runs:
                # Получаем результаты
                results = run.get("results", [])

                # Получаем информацию о инструменте
                tool_info = run.get("tool", {}).get("driver", {})
                tool_name = tool_info.get("name", "unknown")
                tool_version = tool_info.get("version", "unknown")

                logger.debug(f"Processing results from {tool_name} v{tool_version}: {len(results)} issues")

                # Нормализуем каждое срабатывание
                for result in results:
                    normalized = self._normalize_result(result, tool_name)
                    if normalized:
                        # Добавляем метаинформацию
                        normalized["metadata"] = {
                            "tool": tool_name,
                            "tool_version": tool_version,
                            "normalization_timestamp": datetime.now().isoformat()
                        }

                        if execution_time is not None:
                            normalized["metadata"]["execution_time"] = execution_time

                        normalized_issues.append(normalized)

            logger.info(f"Normalized {len(normalized_issues)} issues")

        except Exception as e:
            logger.error(f"Error normalizing SARIF data: {e}")

        return normalized_issues

    def _normalize_result(self, result: Dict, tool_name: str) -> Optional[Dict]:
        """
        Нормализует одно срабатывание

        Args:
            result: Срабатывание из SARIF
            tool_name: Имя инструмента

        Returns:
            Dict: Нормализованное срабатывание
        """
        try:
            normalized = {}

            # Rule ID
            normalized["rule_id"] = result.get("ruleId", "unknown")

            # Message
            message_obj = result.get("message", {})
            if isinstance(message_obj, dict):
                normalized["message"] = message_obj.get("text", "")
            else:
                normalized["message"] = str(message_obj)

            # Severity
            normalized["severity"] = result.get("level", "warning").lower()

            # Location
            locations = result.get("locations", [])
            if locations:
                location = locations[0].get("physicalLocation", {})

                # File path
                artifact_location = location.get("artifactLocation", {})
                file_path = artifact_location.get("uri", "")

                # Убираем префикс /src/ если есть
                if file_path.startswith("/src/"):
                    file_path = file_path[5:]
                elif file_path.startswith("file://"):
                    file_path = file_path[7:]

                normalized["file_path"] = file_path

                # Line number
                region = location.get("region", {})
                normalized["line_number"] = region.get("startLine", 1)

                # Column (опционально)
                start_column = region.get("startColumn")
                if start_column:
                    normalized["start_column"] = start_column

                end_line = region.get("endLine")
                if end_line:
                    normalized["end_line"] = end_line

                end_column = region.get("endColumn")
                if end_column:
                    normalized["end_column"] = end_column

            # Partial fingerprints
            partial_fingerprints = result.get("partialFingerprints", {})
            if partial_fingerprints:
                normalized["partialFingerprints"] = partial_fingerprints

            # Дополнительные свойства
            properties = result.get("properties", {})
            if properties:
                normalized["properties"] = properties

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing result: {e}")
            return None

    def save_normalized(self, normalized_issues: List[Dict], project_name: str, tool_name: str):
        """
        Сохраняет нормализованные результаты в файл

        Args:
            normalized_issues: Нормализованные срабатывания
            project_name: Имя проекта
            tool_name: Имя инструмента
        """
        try:
            output_dir = Path("results/normalized") / project_name
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"{tool_name}_normalized.json"

            output_data = {
                "project": project_name,
                "tool": tool_name,
                "timestamp": datetime.now().isoformat(),
                "issues_count": len(normalized_issues),
                "issues": normalized_issues
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Normalized results saved to {output_file}")

        except Exception as e:
            logger.error(f"Error saving normalized results: {e}")