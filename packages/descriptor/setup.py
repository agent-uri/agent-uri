from setuptools import setup, find_packages

setup(
    name="agent_descriptor",
    version="0.1.0",
    description="Library for parsing and validating agent.json descriptors",
    author="Agent URI Team",
    author_email="info@example.com",
    url="https://github.com/agent-uri/agent-descriptor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "jsonschema>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "flake8>=3.8.0",
            "mypy>=0.800",
        ],
    },
)
