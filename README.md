# HockeyMinimapServer
[RU версия README.md](README_ru.md)
## How to install
1. Pre-requirements:
   * Install git
   * Install ninja build system
   * Install ffmpeg > 6.0 (for Windows `winget install ffmpeg` can work)
   * Install python 3.11 or above
   * Create virtual environment via `python -m venv venv`
   * Windows pre-requirements:
      - Activate virtual environment with `./venv/Scripts/activate`
      - Install Visual Studio 2022 with C++ development kit and add `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\<version>\bin\Hostx64\x64` to your Path environment variables
   * Linux pre requirements:
      - Activate virtual environment with `source ./venv/bin/activate`
      - Install python3-dev via package manager (for example on ubuntu: `sudo apt-get install python3-dev`)
      - 
2. Install required packages via `pip install -r requirements.txt` in root directory
3. Clone detectron2 using `git clone https://github.com/facebookresearch/detectron2.git` (install detectron2 with --no-build-isolation parameter)
into windows drive root directory and run install `python -m pip install -e C:\detectron2` where "C:\\" is your drive path for windows

## Alternative automated installation
1. Pre-requirements are same as previous one
2. In root of project run command `pip install -e .`
3. Run post-install script to install additional dependencies `python post_install.py`