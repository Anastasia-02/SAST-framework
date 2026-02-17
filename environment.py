"""
Environment setup and cleanup module
"""

import docker
import logging
from pathlib import Path
import os
import shutil

logger = logging.getLogger(__name__)


class Environment:
    """Класс для управления окружением"""

    def __init__(self):
        self.docker_client = None
        self.containers = []

    def setup(self):
        """Настраивает окружение для тестирования"""
        try:
            # Инициализируем Docker клиент
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")

            # Создаем необходимые директории
            directories = [
                "results",
                "results/raw",
                "results/normalized",
                "results/comparison",
                "results/metrics",
                "baseline",
                "logs"
            ]

            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)
                logger.debug(f"Directory ensured: {directory}")

            logger.info("Environment setup completed")

        except docker.errors.DockerException as e:
            logger.error(f"Docker error during setup: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during environment setup: {e}")
            raise

    def cleanup(self):
        """Очищает окружение после тестирования"""
        try:
            # Останавливаем и удаляем контейнеры
            if self.docker_client:
                for container in self.containers:
                    try:
                        container.stop()
                        container.remove()
                        logger.debug(f"Container stopped and removed: {container.id}")
                    except Exception as e:
                        logger.warning(f"Error cleaning up container {container.id}: {e}")

                self.containers.clear()

            # Очищаем временные файлы
            temp_dirs = ["temp", "tmp"]
            for temp_dir in temp_dirs:
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Temp directory removed: {temp_dir}")

            logger.info("Environment cleanup completed")

        except Exception as e:
            logger.error(f"Error during environment cleanup: {e}")