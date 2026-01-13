import docker
import tempfile
import os  # Добавляем импорт os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .logger import logger


class DockerManager:
    """Manage Docker containers for SAST tools"""

    def __init__(self):
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def run_tool_container(self, image: str, command: List[str],
                           project_path: Path, output_file: Path,
                           mount_point: str = "/src",
                           env_vars: Optional[Dict[str, str]] = None,
                           timeout: int = 600) -> Tuple[bool, float, Optional[str]]:
        """
        Run a SAST tool in a Docker container

        Returns: (success, duration_seconds, error_message)
        """

        start_time = time.time()

        try:
            # Prepare volumes
            volumes = {
                str(project_path.absolute()): {
                    'bind': mount_point,
                    'mode': 'ro'
                },
                str(output_file.parent.absolute()): {
                    'bind': '/output',
                    'mode': 'rw'
                }
            }

            # Prepare environment variables
            environment = env_vars or {}

            # Update command with actual paths
            container_command = []
            for arg in command:
                arg = arg.replace("{project_path}", mount_point)
                arg = arg.replace("{output_file}", f"/output/{output_file.name}")
                container_command.append(arg)

            logger.info(f"Running container: {image}")
            logger.debug(f"Command: {' '.join(container_command)}")

            # Run container
            container = self.client.containers.run(
                image=image,
                command=container_command,
                volumes=volumes,
                environment=environment,
                detach=True,
                remove=False  # We'll remove it ourselves after getting logs
            )

            # Wait for container to finish
            result = container.wait(timeout=timeout)
            exit_code = result.get('StatusCode', 1)

            # Get container logs
            logs = container.logs().decode('utf-8', errors='ignore')

            # Remove container
            container.remove()

            duration = time.time() - start_time

            if exit_code == 0:
                logger.info(f"Container completed successfully in {duration:.2f}s")
                return True, duration, None
            else:
                logger.warning(f"Container exited with code {exit_code}")
                # Some tools return non-zero for findings, which might be OK
                # Check if output file was created
                if output_file.exists():
                    logger.info(f"Output file created despite non-zero exit: {output_file}")
                    return True, duration, None
                else:
                    error_msg = f"Container failed with exit code {exit_code}\nLogs:\n{logs[:500]}"
                    return False, duration, error_msg

        except docker.errors.ContainerError as e:
            duration = time.time() - start_time
            error_msg = f"Container error: {e}\n{e.stderr.decode() if e.stderr else ''}"
            return False, duration, error_msg

        except docker.errors.ImageNotFound:
            duration = time.time() - start_time
            error_msg = f"Image not found: {image}"
            return False, duration, error_msg

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error: {e}"
            return False, duration, error_msg

    def pull_image(self, image: str) -> bool:
        """Pull Docker image if not available locally"""
        try:
            logger.info(f"Pulling image: {image}")
            self.client.images.pull(image)
            logger.info(f"Successfully pulled image: {image}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull image {image}: {e}")
            return False

    def cleanup_containers(self, older_than_hours: int = 1):
        """Clean up old containers"""
        try:
            from dateutil import parser  # Добавляем локальный импорт

            cutoff = datetime.now().timestamp() - (older_than_hours * 3600)

            containers = self.client.containers.list(
                all=True,
                filters={'status': 'exited'}
            )

            cleaned = 0
            for container in containers:
                container_info = container.attrs
                finished_at = container_info['State']['FinishedAt']

                # Parse timestamp
                finished_time = parser.parse(finished_at).timestamp()

                if finished_time < cutoff:
                    container.remove()
                    cleaned += 1

            logger.info(f"Cleaned up {cleaned} old containers")

        except Exception as e:
            logger.error(f"Error cleaning up containers: {e}")