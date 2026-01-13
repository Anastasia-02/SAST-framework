from setuptools import setup, find_packages

setup(
    name="sast-regression-framework",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "PyYAML>=6.0",
        "pydantic>=2.0",
        "docker>=6.0",
        "jsonschema>=4.0",
        "python-dateutil>=2.8",
        "colorlog>=6.0",
        "typer>=0.9",
        "rich>=13.0",
        "urllib3<2.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "sast-regression=framework.main:main",
        ],
    },
)