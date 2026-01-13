import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from ..utils.logger import logger
from ..core.config_loader import ToolConfig
from .environment import EnvironmentManager


class ToolLauncher:
    """Launch SAST tools and collect their output"""

    def __init__(self, environment: EnvironmentManager):
        self.env = environment

    def run_tool(self, tool_config: ToolConfig, project_path: Path,
                 output_dir: Path) -> Tuple[bool, Optional[Path], float, Optional[str]]:
        """
        Run a SAST tool on a project
        """

        start_time = time.time()

        try:
            # Создаем output filename БЕЗ timestamp для простоты
            output_filename = f"{tool_config.name}.sarif"  # ← Убрали timestamp
            output_path = output_dir / output_filename

            logger.info(f"Running {tool_config.name} on {project_path.name}")

            if tool_config.type == "docker":
                return self._run_docker_tool(tool_config, project_path, output_path)
            else:
                return self._run_native_tool(tool_config, project_path, output_path)

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error running {tool_config.name}: {e}"
            logger.error(error_msg)
            return False, None, duration, error_msg

    def _run_docker_tool(self, tool_config: ToolConfig, project_path: Path,
                         output_path: Path) -> Tuple[bool, Optional[Path], float, Optional[str]]:
        """Run tool using Docker"""

        docker_manager = self.env.get_docker_manager()

        # Pull image if needed (in real implementation, check local first)
        image = f"{tool_config.image}:{tool_config.version}"

        # Prepare command parts
        # Split command if it contains spaces (e.g., "semgrep scan")
        cmd_parts = tool_config.command.split()
        args_parts = list(tool_config.args)

        # Combine command and arguments
        full_command = cmd_parts + args_parts

        # Replace placeholders in all parts
        container_command = []
        for arg in full_command:
            arg = arg.replace("{project_path}", tool_config.mount_point)
            arg = arg.replace("{output_file}", f"/output/{output_path.name}")
            container_command.append(arg)

        logger.debug(f"Full container command: {container_command}")

        # Run container
        success, duration, error = docker_manager.run_tool_container(
            image=image,
            command=container_command,  # Pass the full command list
            project_path=project_path,
            output_file=output_path,
            mount_point=tool_config.mount_point,
            env_vars=tool_config.env_vars
        )

        if success and output_path.exists():
            return True, output_path, duration, None
        else:
            return False, None, duration, error

    def _run_native_tool(self, tool_config: ToolConfig, project_path: Path,
                         output_path: Path) -> Tuple[bool, Optional[Path], float, Optional[str]]:
        """Run tool natively (not using Docker)"""

        start_time = time.time()

        try:
            # Prepare command
            cmd = [tool_config.command] + tool_config.args

            # Replace placeholders
            for i, arg in enumerate(cmd):
                cmd[i] = arg.replace("{project_path}", str(project_path))
                cmd[i] = arg.replace("{output_file}", str(output_path))

            # Set environment variables
            env = {**tool_config.env_vars}

            # Run command
            logger.debug(f"Running native command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**os.environ, **env},
                timeout=300  # 5 minute timeout
            )

            duration = time.time() - start_time

            if result.returncode == 0 and output_path.exists():
                logger.info(f"Native tool completed in {duration:.2f}s")
                return True, output_path, duration, None
            else:
                error_msg = f"Native tool failed with code {result.returncode}\n"
                error_msg += f"STDOUT: {result.stdout[:200]}\n"
                error_msg += f"STDERR: {result.stderr[:200]}"
                return False, None, duration, error_msg

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return False, None, duration, "Tool execution timed out"
        except Exception as e:
            duration = time.time() - start_time
            return False, None, duration, f"Error: {e}"