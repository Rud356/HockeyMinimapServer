# HockeyMinimapServer
[EN version of README.md](README.md)

## Установка
1. Предварительные зависимости:
   * Установить git
   * Установить систему сборки ninja build
   * Установить ffmpeg > 6.0 (для Windows `winget install ffmpeg` один из доступных вариантов установки)
   * Установить python 3.11 или выше (желательно 3.11)
   * Создать виртуальное окружение командой `python -m venv venv` или аналог для Linux с указанием версии
   * Подготовка для Windows:
      - Активировать виртуальное окружение с помощью команды `./venv/Scripts/activate`
      - Установить Visual Studio 2022 с C++ development kit, и добавить в системную переменную пути Path `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\<version>\bin\Hostx64\x64`
   * Подготовка Linux:
      - Активировать виртуальное окружение с помощью `source ./venv/bin/activate`
      - Установить python3-dev через пакетный менеджер (для Debian-based дистрибутивов и Ubuntu: `sudo apt-get install python3-dev`)
2. Установить зависимости командой `pip install -r requirements.txt`
3. Склонировать репозиторий `git clone https://github.com/facebookresearch/detectron2.git` (устанавливать detectron2 необходимо параметром pip --no-build-isolation)
в корень диска `python -m pip install -e C:\detectron2` где "C:\\" это путь до корня выбранного диска

## Альтернативная установка
1. Выполнить предварительные требования из прошлого варианта
2. В корне проекта выполнить `pip install -e .`
3. Запустить пост-установочный скрипт командой `python post_install.py` для установки доп. зависимостей