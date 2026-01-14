"""PULSAR SENTINEL - Post-Quantum Cryptography Security Framework."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="pulsar-sentinel",
    version="1.0.0",
    author="Angel Cloud",
    author_email="security@angelcloud.io",
    description="Post-Quantum Cryptography Security Framework for Angel Cloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thebardchat/pulsar_sentinel",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=24.1.0",
            "mypy>=1.8.0",
            "ruff>=0.1.0",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pulsar-sentinel=api.server:main",
        ],
    },
)
