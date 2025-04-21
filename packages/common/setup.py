#!/usr/bin/env python

from setuptools import setup, find_namespace_packages

setup(
    name="agent-common",
    version="0.1.0",
    description="Common utilities for agent:// protocol",
    author="Agent URI Team",
    author_email="info@agent-uri.org",
    url="https://github.com/agent-uri/agent-uri",
    packages=find_namespace_packages(include=["agent_common", "agent_common.*"]),
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
    install_requires=[],
)
