# SAST Regression Testing Framework

Automated regression testing framework for SAST tools in CI/CD pipelines.

## Features

- **Multi-tool Support**: Works with Semgrep, SonarQube, Cppcheck, PVS-Studio, Shellcheck, and more
- **Docker-based Execution**: Runs tools in isolated Docker containers
- **Normalized Output**: Converts all tool outputs to a unified format
- **Baseline Management**: Creates and compares against reference results
- **Extensible Architecture**: Easy to add new tools and parsers

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd sast-regression-framework

# Install dependencies
pip install -e .

# Or using pip directly
pip install -r requirements.txt