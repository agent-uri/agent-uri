"""
Setup script for the agent-resolver package.
"""

import os
from setuptools import setup, find_packages

# Read the contents of the README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="agent-resolver",
    version="0.1.0",
    description="Resolution framework for agent:// URIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Agent URI Team",
    author_email="agent-uri@example.com",
    url="https://github.com/example/agent-uri",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "requests-cache>=0.9.0",
        "agent-uri",  # URI Parser package
        "agent-descriptor",
    ],
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
)
