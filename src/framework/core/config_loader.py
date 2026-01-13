import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator
from ..utils.logger import logger


class ToolConfig(BaseModel):
    """Configuration for a SAST tool"""
    name: str
    type: str
    image: str
    version: str
    command: str
    args: List[str]
    mount_point: str = "/src"
    env_vars: Dict[str, str] = Field(default_factory=dict)

    @validator('type')
    def validate_type(cls, v):
        if v not in ['docker', 'native']:
            raise ValueError(f"Tool type must be 'docker' or 'native', got '{v}'")
        return v


class ProjectConfig(BaseModel):
    """Configuration for a test project"""
    name: str
    path: str
    language: str
    analyzers: List[str]


class FrameworkConfig(BaseModel):
    """Main framework configuration"""
    projects: List[ProjectConfig]
    tools: Dict[str, ToolConfig]

    class Config:
        extra = "ignore"


class ConfigLoader:
    """Load and manage framework configuration"""

    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self.config: Optional[FrameworkConfig] = None

    def load(self) -> FrameworkConfig:
        """Load configuration from YAML files"""

        # Load projects configuration
        projects_path = self.config_dir / "projects.yaml"
        with open(projects_path, 'r') as f:
            projects_data = yaml.safe_load(f)

        # Load tools configuration
        tools_path = self.config_dir / "tools.yaml"
        with open(tools_path, 'r') as f:
            tools_data = yaml.safe_load(f)

        # Prepare tool configurations with names
        tools_dict = {}
        for tool_name, tool_config in tools_data.get('tools', {}).items():
            tool_config['name'] = tool_name
            tools_dict[tool_name] = ToolConfig(**tool_config)

        # Create framework config
        config_data = {
            'projects': projects_data.get('projects', []),
            'tools': tools_dict
        }

        self.config = FrameworkConfig(**config_data)
        logger.info(f"Loaded configuration: {len(self.config.projects)} projects, "
                    f"{len(self.config.tools)} tools")

        return self.config

    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """Get configuration for a specific tool"""
        if self.config and tool_name in self.config.tools:
            return self.config.tools[tool_name]
        return None

    def get_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Get configuration for a specific project"""
        if self.config:
            for project in self.config.projects:
                if project.name == project_name:
                    return project
        return None