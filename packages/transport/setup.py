from setuptools import setup, find_namespace_packages

setup(
    name="agent-transport",
    version="0.1.0",
    description="Transport binding layer for agent:// protocol",
    author="Agent URI Team",
    packages=find_namespace_packages(include=["agent_transport", "agent_transport.*"]),
    install_requires=[
        "requests>=2.25.0",
        "sseclient-py>=1.7.0",
        "websocket-client>=1.2.0",
        "agent-uri>=0.1.0",      # URI Parser package
        "agent-descriptor>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "flake8>=3.8.0",
            "black>=20.8b1",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
