from setuptools import setup, find_namespace_packages

setup(
    name="agent-server",
    version="0.1.0",
    description="Server SDK for implementing agents conforming to the agent:// protocol",
    author="Agent URI Team",
    packages=find_namespace_packages(include=["agent_server*"]),
    install_requires=[
        "agent_uri",
        "agent_descriptor",
        "agent_resolver",
        "agent_transport",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.8.2",
        "requests>=2.25.0",
        "jsonschema>=4.0.0",
        "websockets>=10.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.15.0",
            "black>=21.5b2",
            "isort>=5.9.1",
            "mypy>=0.812",
            "httpx>=0.18.0",  # For async HTTP testing
        ]
    },
    python_requires=">=3.8",
)
