"""
Setup script for Zoom Recordings Extractor
"""

from setuptools import setup, find_packages
from pathlib import Path
import sys

# Read the README file
this_directory = Path(__file__).parent
try:
    long_description = (this_directory / "README.md").read_text(encoding='utf-8')
except FileNotFoundError:
    long_description = "A comprehensive tool for downloading all cloud recordings from a Zoom account"

# Read requirements
requirements = []
try:
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
except FileNotFoundError:
    # Fallback requirements if requirements.txt is missing
    requirements = [
        'requests>=2.31.0',
        'python-dotenv>=1.0.0',
        'click>=8.1.0',
        'tqdm>=4.66.0',
        'PyJWT>=2.8.0',
        'python-dateutil>=2.8.0',
    ]

# Windows-specific dependencies
if sys.platform.startswith('win'):
    requirements.extend([
        'pywin32>=306; sys_platform == "win32"',
    ])

setup(
    name="zoom-recordings-extractor",
    version="1.0.0",
    author="Zoom Extractor Team",
    author_email="",
    description="A comprehensive tool for downloading all cloud recordings from a Zoom account",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/silicoon84/zoomextractor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Conferencing",
        "Topic :: System :: Archiving",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
            "responses>=0.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "zoom-extract=zoom_extractor.main:main",
            "zoom-extract-all=extract_all_recordings:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="zoom recordings download extract archive backup windows",
    project_urls={
        "Bug Reports": "https://github.com/silicoon84/zoomextractor/issues",
        "Source": "https://github.com/silicoon84/zoomextractor",
        "Documentation": "https://github.com/silicoon84/zoomextractor#readme",
    },
    # Windows-specific options
    options={
        "build_exe": {
            "include_msvcrt": True,
        },
    },
)
