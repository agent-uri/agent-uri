"""
Setup script for the agent-uri package.
"""

from setuptools import setup, find_packages

setup(
    name="agent-uri",
    version="0.1.0",
    description="Agent URI Parser for the agent:// protocol",
    author="Yaswanth Narvaneni",
    author_email="yaswanth@gmail.com",
    packages=find_packages(),
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
