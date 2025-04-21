#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="agent-client",
    version="0.1.0",
    description="Client SDK for the agent:// protocol",
    author="Agent URI Project",
    author_email="info@agent-uri.org",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "requests-cache>=0.9.0",
        "websocket-client>=1.2.0",
        "sseclient-py>=1.7.2",
        "pyjwt>=2.4.0",  # For JWT authentication
        "agent-uri",         # URI Parsing package
        "agent-descriptor",  # Descriptor handling package
        "agent-resolver",    # Resolution package
        "agent-transport",   # Transport package
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.1.0",
            "isort>=5.10.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
