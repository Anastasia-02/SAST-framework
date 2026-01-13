import tempfile
import shutil
from pathlib import Path
from typing import Optional
from ..utils.logger import logger
from ..utils.docker_utils import DockerManager


class EnvironmentManager:
    """Manage test environment (setup and cleanup)"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.docker_manager: Optional[DockerManager] = None
        self.temp_dirs = []

    def setup(self) -> bool:
        """Setup test environment"""
        try:
            # Create output directories
            self.output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / "raw").mkdir(exist_ok=True)
            (self.output_dir / "normalized").mkdir(exist_ok=True)

            # Initialize Docker manager
            self.docker_manager = DockerManager()

            logger.info("Environment setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup environment: {e}")
            return False

    def create_temp_dir(self) -> Path:
        """Create a temporary directory"""
        temp_dir = tempfile.mkdtemp(prefix="sast_test_")
        self.temp_dirs.append(temp_dir)
        return Path(temp_dir)

    def cleanup(self):
        """Cleanup test environment"""
        try:
            # Cleanup temporary directories
            for temp_dir in self.temp_dirs:
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir)
            self.temp_dirs.clear()

            # Cleanup Docker containers
            if self.docker_manager:
                self.docker_manager.cleanup_containers()

            logger.info("Environment cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_docker_manager(self) -> DockerManager:
        """Get Docker manager instance"""
        if not self.docker_manager:
            self.docker_manager = DockerManager()
        return self.docker_manager