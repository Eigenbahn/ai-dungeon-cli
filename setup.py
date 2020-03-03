import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ai-dungeon-cli",
    version="0.1.3",
    author="Jordan Besly",
    author_email="",
    description="Play ai dungeon from your terminal",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Eigenbahn/ai-dungeon-cli",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    install_requires=[
        "requests>=2.23.0",
        "PyYAML>=5.1.2",
        "pyreadline >= 2.1;platform_system=='Windows'"
    ],


    entry_points={
        "console_scripts": [
            "ai-dungeon-cli = ai_dungeon_cli.__init__:main",
        ],
    },
    package_data={
        "": ["*.txt"]
    },
    python_requires='>=3.3',
)
