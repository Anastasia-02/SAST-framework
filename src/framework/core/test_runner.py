import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..utils.logger import logger
from ..core.config_loader import ConfigLoader, FrameworkConfig, ProjectConfig, ToolConfig
from ..modules.environment import EnvironmentManager
from ..modules.tool_launcher import ToolLauncher
from ..modules.results_collector import ResultsCollector
from ..normalization.sarif_normalizer import SARIFNormalizer
from ..normalization.models import NormalizedResult
from .baseline_manager import BaselineManager


class RegressionTestRunner:
    """Main test runner for regression testing"""

    def __init__(self, config_dir: str = "./config", results_dir: str = "./results"):
        self.config_loader = ConfigLoader(config_dir)
        self.config: Optional[FrameworkConfig] = None

        # Setup paths
        self.results_dir = Path(results_dir)
        self.baseline_dir = Path("./baseline")

        # Initialize components
        self.env = EnvironmentManager(self.results_dir)
        self.results_collector = ResultsCollector(self.results_dir)
        self.normalizer = SARIFNormalizer()
        self.baseline_manager = BaselineManager(self.baseline_dir)

        # Statistics
        self.stats = {
            "projects_tested": 0,
            "tools_executed": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_duration": 0.0,
            "start_time": None,
            "end_time": None
        }

    def setup(self) -> bool:
        """Setup the test runner"""
        try:
            # Load configuration
            self.config = self.config_loader.load()

            # Setup environment
            if not self.env.setup():
                return False

            logger.info("Test runner setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup test runner: {e}")
            return False

    def run_tool_on_project(self, project: ProjectConfig, tool_name: str) -> Tuple[bool, Optional[NormalizedResult]]:
        """Run a specific tool on a specific project"""

        # Get tool configuration
        tool_config = self.config_loader.get_tool_config(tool_name)
        if not tool_config:
            logger.error(f"Tool configuration not found: {tool_name}")
            return False, None

        # Create tool launcher
        launcher = ToolLauncher(self.env)

        # Run tool
        project_path = Path(project.path)
        output_dir = self.results_dir / "raw" / project.name

        success, output_path, duration, error = launcher.run_tool(
            tool_config, project_path, output_dir
        )

        if not success or not output_path:
            logger.error(f"Tool {tool_name} failed on project {project.name}: {error}")
            return False, None

        # Load and normalize results
        raw_data = self.results_collector.load_raw_result(output_path)
        if not raw_data:
            return False, None

        # Normalize results
        normalized_result = self.normalizer.normalize_file(
            output_path, tool_name, project.name, duration
        )

        # Update statistics
        self.stats["tools_executed"] += 1
        if success:
            self.stats["successful_runs"] += 1
        else:
            self.stats["failed_runs"] += 1
        self.stats["total_duration"] += duration

        return True, normalized_result

    def run_project(self, project_name: str, save_baseline: bool = False) -> bool:
        """Run all configured tools on a specific project"""

        project_config = self.config_loader.get_project_config(project_name)
        if not project_config:
            logger.error(f"Project configuration not found: {project_name}")
            return False

        logger.info(f"Starting testing for project: {project_name}")

        all_success = True

        for tool_name in project_config.analyzers:
            logger.info(f"  Running {tool_name}...")

            success, result = self.run_tool_on_project(project_config, tool_name)

            if success and result:
                # Save normalized result
                result_data = result.to_dict()
                self.results_collector.save_normalized_result(
                    result_data, project_name, tool_name
                )

                # Save as baseline if requested
                if save_baseline:
                    self.baseline_manager.save_baseline(result, tool_name)

                logger.info(f"    Found {result.issue_count} issues")
            else:
                all_success = False
                logger.error(f"    Tool {tool_name} failed")

        if all_success:
            logger.info(f"Completed testing for project: {project_name}")
            self.stats["projects_tested"] += 1
        else:
            logger.warning(f"Some tools failed for project: {project_name}")

        return all_success

    def run_all(self, save_baseline: bool = False) -> bool:
        """Run regression tests on all projects"""

        if not self.config:
            logger.error("Configuration not loaded")
            return False

        self.stats["start_time"] = datetime.now()
        logger.info(f"Starting regression testing for {len(self.config.projects)} projects")

        all_success = True

        for project in self.config.projects:
            success = self.run_project(project.name, save_baseline)
            if not success:
                all_success = False

        self.stats["end_time"] = datetime.now()

        # Generate baseline summary if we saved baselines
        if save_baseline:
            self.baseline_manager.generate_baseline_summary()

        # Print summary
        self._print_summary()

        return all_success

    def _print_summary(self):
        """Print test execution summary"""

        if not self.stats["start_time"] or not self.stats["end_time"]:
            logger.warning("Cannot print summary: test times not recorded")
            return

        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        logger.info("=" * 60)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total projects tested: {self.stats['projects_tested']}")
        logger.info(f"Total tools executed: {self.stats['tools_executed']}")
        logger.info(f"Successful runs: {self.stats['successful_runs']}")
        logger.info(f"Failed runs: {self.stats['failed_runs']}")
        logger.info(f"Total duration: {duration:.2f} seconds")

        if self.stats['tools_executed'] > 0:
            logger.info(f"Average per tool: {duration / self.stats['tools_executed']:.2f} seconds")

        if self.stats['failed_runs'] > 0:
            logger.warning("Some test runs failed!")
        else:
            logger.info("All test runs completed successfully")

    def cleanup(self):
        """Cleanup test environment"""
        self.env.cleanup()
        logger.info("Test runner cleanup completed")
