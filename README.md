# HockeyMinimapServer
[RU версия README.md](README_ru.md)

This project is designed for partial automation of player tracking on an ice hockey field based on video recordings from a stationary camera.

## Prerequisites
### System Requirements:
| Parameter                  | Minimum Requirements                     | Recommended Requirements                     |
|----------------------------|------------------------------------------|----------------------------------------------|
| **Platform**               | Windows 10, Linux                        | Windows 10, Linux                            |
| **Architecture**           | 64-bit                                   | 64-bit                                       |
| **Processor**              | At least 3.8 GHz with 4 cores            | 4 GHz or faster with 8 or more cores         |
| **GPU**                    | -                                        | Nvidia RTX 3050 8GB                          |
| **RAM**                    | 8 GB                                     | 16 GB of RAM                                 |
| **Controller**             | Keyboard and mouse                       | Keyboard and mouse                           |
| **Disk Space**             | 50 GB of free space                      | 120 GB of free space                         |

**System disk requirements include space for storing project files.**

**Internet connection is required to download the pre-trained ResNet18 model from the PyTorch library during the first run, as well as for installing the project.**

### Required Software
   * Git;
   * Ninja build system;
   * FFMpeg > 6.0 (for Windows: `winget install ffmpeg` is one of the installation options);
   * Python 3.11 or higher (preferably 3.11) depending on library support for newer versions;
   * Windows Terminal running in PowerShell mode.

#### Software Specific to Windows
   * Visual Studio 2022 with C++ development kit.

#### Software Specific to Linux
   * g++ and gcc compilers;
   * For Nvidia GPU hardware acceleration, proprietary drivers need to be installed;
   * Installed Python language developer packages (`python3-dev` for Debian-based distributions). 

### Preparation for Windows:
   - Add the following value to the PATH system variable, substituting <version>:
     `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\<version>\bin\Hostx64\x64`;
   - Enable the execution of signed scripts via PowerShell command
     `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.
     > Required for running virtual environments and builds.

### Preparation for Linux:
   - Install python3-dev through the package manager;
     > (for Debian-based distributions and Ubuntu: `sudo apt-get install python3-dev`).

After installing the required software, it is recommended to restart your computer to apply the changes.

## Project Installation
1. Clone the project or download and unzip the archived version of the project containing the HockeyMinimapServer folder, which is the root of the project:
   1. If files with the .pth extension are missing in the models folder, the project cannot be run, so they need to be manually added:
      - The default FieldDetector.pth file is responsible for the Detectron2 model marking field elements;
      - The default PlayersDetector.pth file is responsible for determining player and referee locations on the field.
2. Prepare the environment:
   * Create a virtual environment in the root of the project using the command `python -m venv venv` or its equivalent for Linux `python3 -m venv venv`.
   ### For Windows:
      - Activate the virtual environment with the command `./venv/Scripts/activate`.
   ### For Linux:
      - Activate the virtual environment with the command `source ./venv/bin/activate`.
3. In the root of the project, execute `pip install -e .`.
   > If additional developer dependencies are needed, use 
   > `pip install -e ".[uvicorn,linters,dev]"`.
4. Run the post-installation script with the command `python post_install.py` to install additional dependencies:
   - You will be offered a list of supported backend options for pytorch by your operating system, from which you need to choose using the input number in the list and pressing enter to confirm, after which pytorch and Detectron2 will be installed separately.
   - By default, the selected backend is CPU, which will be chosen if no input or an invalid number is entered.

## Overview of Stored Files and Folders
* `./server` - stores server source code and abstractions for its operation;
* `./models` - contains the default folder for storing Detectron2 models;
* `./static` - contains default static resources, which can be moved to another disk only with preserving its structure:
  * `./static/map.png` - original minimap image used for rendering video and calculations;
  * `./static/videos` - folder for storing processed video resources;
  * `./static/videos/<UUID>` - separate folder for a specific uploaded video and additional processing resources:
    * `./static/videos/<UUID>/source_video.mp4` - the originally uploaded video, transcoded into browser-compatible format;
    * `./static/videos/<UUID>/corrected_video.mp4` - video with corrected barrel distortion;
    * `./static/videos/<UUID>/field_mask.jpeg` - field mask required for obtaining player positions; 
      > Obtained by calling the `/video/{video_id}/map_points/inference` endpoint.
    * `./static/videos/<UUID>/project_data.json` - exported project data.
      > Obtained by calling `/projects/{project_id}/export`.
    * `./static/videos/<UUID>/export.zip` - exported project data and resources.
      > Obtained by calling `/projects/{project_id}/export` and used for full project recovery.
* `./tests` - contains unit tests for repositories
  > Developer dependencies need to be installed, see point 3 of the installation process.
* `./docs` - folder for generating documentation from source code.
  For documentation generation, call `make html` or another output format supported by Sphinx;
  > Added a dependency for generating Word files through docx.
  > Developer dependencies need to be installed.
* `config.toml` - default configuration file,
  not creating a permanent database and used for testing.

## Running the Project
1. Activate the virtual environment as described earlier in point 2, "Project Installation"
2. Run the command `python -m server`
3. To terminate, press CTRL+C in the console

By default, startup is performed with settings assuming local temporary use,
and data will not be saved without changing the configuration.

Launch arguments (follow the regular run command):
* --help -h - outputs a help message on arguments
* --init-db - initializes database tables
* --drop-db - deletes all data from database tables
* --config -c <CONFIG_PATH> - specifies the path to the configuration file with which the application will be started
* --local-mode - runs server in local access mode

Example command: `python -m server --help`

### Local Access Mode
Local access mode is a special mode with one user not entered into the database under the name Admin and without a password. This user has all rights and is required for primary user creation.

**By default, this mode is enabled in configuration, and for network use, it should be disabled for security purposes.**

### Configuration
It is recommended to create a separate configuration file based on the one provided in the repository, copying the initial file and changing parameters in it, after which apply it at startup with the command `python -m server -c ./config.toml`,
where `./config.toml` is replaced with the user's custom file.

#### Configuration Parameters:
* local_mode - Determines whether the server runs in local access mode or not (default true);
* db_connection_string - Database connection string,
  passed to [SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/engines.html);
  > For persistent data storage, replace `:memory:` with a file name,
  > and start the server through the init-db argument `python -m server --init-db`.

  > For databases other than SQLite, additional module installation is required according to async SQLAlchemy documentation since an asynchronous version of queries is used.
* enable_gzip_compression - necessary for enabling data compression on the Python server side (default true);
  > This option should be turned off when using reverse-proxy (e.g., nginx),
  > since they compress data more efficiently and can use fewer resources.
* server_jwt_key - JWT token signing key required to verify access tokens,
  **it is necessary to change it from the default parameter;**
* static_path - path to the folder with static resources (default ./static from project root);
* players_data_extraction_workers - number of player data processing handlers;
* minimap_frame_buffer - number of frames in buffer for disk output;
  > Each frame ~= 1.5 MB RAM * minimap_rendering_workers at peak load.
* prefetch_frame_buffer - number of frames in buffer for video processing;
  > Each frame ~= 1.5 MB RAM * video_processing_workers at peak load.
* minimap_rendering_workers - number of parallel minimap outputs that can be processed;
* video_processing_workers - number of video processors obtaining player shape samples 
  or performing player movement sampling;
##### nn_config Section:
* field_detection_model_path - path to the field element detection model;
* player_detection_model_path - path to the player detection model on the field;
* max_batch_size - maximum number of frames processed in parallel by the neural network;
##### server_settings Section:
* host - restriction from where requests are accepted;
* port - port of the running server;
* reload_dirs - whether to dynamically reload static file directories;
  > When using nginx for file serving from static - set to false.
* allowed_cors_domains - list of trusted domains that are permitted to make requests to the server;
  > Required for browser access.
##### video_processing Section:
* hwaccel - selected hardware accelerator from FFMpeg parameters;
* codec - selected video encoder for FFMpeg;
* hwaccel_output_format - format in which frames are stored;
  > For hardware decoders, a suitable one needs to be chosen,
  > otherwise data transmission through the processor will slow down processing.
* video_width - maximum video width (divisible by 2);
* video_height - maximum video height (divisible by 2);
* preset - quality encoding preset for video (faster - larger file size);
  > Applies only to processors used as encoders.
* crf - quality of re-encoded video (lower is better);
* target_bitrate - target video bitrate;
* maxrate - maximum video bitrate;
* bufsize - period over which FFMpeg tracks bitrate;
* loglevel - FFMpeg console output level;
##### minimap_config Section (minimap key point configuration):
* top_left_field_point - top-left point encompassing the playing field on the map;
* bottom_right_field_point - bottom-right point encompassing the playing field on the map;
* left_goal_zone - center point of the left goal zone;
* right_goal_zone - center point of the right goal zone;
* center_line_top - top point of the center field line;
* center_line_bottom - bottom point of the center field line;
* left_blue_line_top - top point of the left blue line;
* left_blue_line_bottom - bottom point of the left blue line;
* right_blue_line_top - top point of the right blue line;
* right_blue_line_bottom - bottom point of the right blue line;
* left_goal_line_top - top point of the upper half of the left goal zone line;
* left_goal_line_bottom - bottom point of the upper half of the left goal zone line;
* left_goal_line_after_zone_top - top point of the lower half of the left goal zone line;
* left_goal_line_after_zone_bottom - bottom point of the lower half of the left goal zone line;
* right_goal_line_top - top point of the upper half of the right goal zone line;
* right_goal_line_bottom - bottom point of the upper half of the right goal zone line;
* right_goal_line_after_zone_top - top point of the lower half of the right goal zone line;
* right_goal_line_after_zone_bottom - bottom point of the lower half of the right goal zone line;
* red_circle_top_left - center of the left upper red circle;
* red_circle_top_right - center of the right upper red circle;
* red_circle_bottom_left - center of the left lower red circle;
* red_circle_bottom_right - center of the right lower red circle;
* center_circle - center of the central circle.

## Server Behavior Features:
* All frame-related identifiers are indices,
  and thus include both ends [n, n+k] as valid identifiers.
* Data retrieval from sub-datasets about player shapes does not group information by frames but retrieves it as a single list,
  which may require grouping by frames on the client side;
* Information about points retrieved from the server does not save point data to the database. Manual submission is required.
* Description of used enumerations passed as numbers for setting classes or teams is unavailable at the default documentation address
  http://localhost:8000/docs/,
  but available in alternative documentation at http://localhost:8000/redoc.