from setuptools import setup


setup(
    name="HockeyMinimapServer",
    version="0.0.1",
    description="Server for minimap generation application",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Rud356",
    author_email="rud356github@gmail.com",
    python_requires=">=3.11.0",
    license="MIT License",
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Intended Audience :: System Administrators",
        "Natural Language :: Russian",
    ],
    install_requires=[
        "sqlalchemy[asyncio]~=2.0.36",
        "aiosqlite~=0.20.0",
        "aiofiles~=0.8.0",
        "types-aiofiles~=0.8.11",
        "opencv-python~=4.10.0.84",
        "ffmpeg-python~=0.2.0",
        "fastapi[standard]~=0.115.12",
        "python-multipart~=0.0.20",
        "dishka~=1.5.2",
        "cython~=3.0.11",
        "scipy~=1.15.2",
        "numpy~=2.2.4",
        "scikit-learn~=1.6.0",
        "sort-pip @ git+https://github.com/Rud356/sort-pip.git",
        "pyjwt~=2.10.1",
        "wheel"
    ],
    extras_require={
        "uvicorn": ["uvicorn~=0.34.0"],
        "linters": ["ruff~=0.11.2", "mypy~=1.15.0"],
        "dev": [
            "sphinx~=5.0.2",
            'docxbuilder',
            "sphinx-autodoc-typehints~=3.1.0",
            "sphinx-rtd-theme~=1.0.0",
            "Pygments~=2.12.0",
            "pytest~=8.3.5",
            "pytest_asyncio~=0.26.0",
            "pyinstrument~=5.0.1"
        ],
    },
    packages=[]
)
