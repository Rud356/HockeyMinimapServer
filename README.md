# HockeyMinimapServer

## How to install
1. Pre-requirements:
   * Install ninja build system
   * Install ffmpeg > 6.0
   * Install python 3.11 or above
   * Install Visual Studio 2022 with C++ development kit and add `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\<version>\bin\Hostx64\x64` to your Path environment variables
   * Linux pre requirements:
      - Install python3-dev via package manager (for example on ubuntu: `sudo apt-get install python3-dev`)
      - Install detectron2 with --no-build-isolation parameter
2. Install required packages via `pip install -r requirements.txt` in root directory
3. Clone detectron2 using `git clone https://github.com/facebookresearch/detectron2.git` 
into windows drive root directory and run install `python -m pip install -e C:\detectron2` where "C:\\" is your drive path for windows