"""
Setup script for Zoom Recordings Extractor
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt', 'r') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="zoom-recordings-extractor",
    version="1.0.0",
    author="Zoom Extractor Team",
    author_email="",
    description="A comprehensive tool for downloading all cloud recordings from a Zoom account",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/zoom-recordings-extractor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Conferencing",
        "Topic :: System :: Archiving",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "zoom-extract=zoom_extractor.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="zoom recordings download extract archive backup",
    project_urls={
        "Bug Reports": "https://github.com/your-org/zoom-recordings-extractor/issues",
        "Source": "https://github.com/your-org/zoom-recordings-extractor",
        "Documentation": "https://github.com/your-org/zoom-recordings-extractor#readme",
    },
)
