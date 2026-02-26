"""
PerfDiff - Statistical Performance Regression Detection Tool

A production-ready statistical tool for detecting performance regressions with
premium UI, data quality gates, and rigorous statistical methodology.

Features:
- Mann-Whitney U test for statistical significance
- Bootstrap confidence intervals for median differences
- Adaptive tail latency metrics (robust to small samples)
- Quality gates (CV, sample size checks)
- Practical significance override
- Beautiful HTML reports with interactive charts
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else __doc__

setup(
    name="perfdiff",
    version="1.0.0",
    description="Statistical performance regression detection tool with premium UI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Shawky",
    python_requires=">=3.8",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    install_requires=[
        "numpy>=1.20.0",
        "scipy>=1.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "perfdiff=commit_to_commit_comparison.multi_trace_comparison:main",
        ],
    },
    include_package_data=True,
    package_data={
        "commit_to_commit_comparison": ["*.py"],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="performance testing regression detection statistics ci-cd",
    project_urls={
        "Documentation": "https://github.com/your-org/perfdiff/blob/main/README.md",
        "Source": "https://github.com/your-org/perfdiff",
    },
)
