#!/usr/bin/env python3
"""
Setup script for YouTube Subtitle Bot
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="youtube-subtitle-bot",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Telegram bot for extracting and summarizing YouTube subtitles",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/subs-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "youtube-subtitle-bot=bot:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 