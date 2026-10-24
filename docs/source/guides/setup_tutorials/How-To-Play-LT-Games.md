# How to Play LT Games

_last updated 2026-10-18_

This guide gives step-by-step instructions on how to start playing LT games on different operating systems.

## Windows

1. Extract the game folder from the .zip/archive file and store it in any folder you wish, !!AS LONG AS THAT FOLDER IS NOT BACKED UP BY ONEDRIVE OR OTHER CLOUD STORAGE!!.
2. Double-click "GAMENAME.exe" or "double_click_to_play.bat" to start the game. Both options do the same thing.

## Linux - Proton
No terminal required. Recommended method.

1. Extract the game folder from the .zip/archive file and store it in any folder you wish, !!AS LONG AS THAT FOLDER IS NOT BACKED UP BY CLOUD STORAGE!!.
2. Install the Steam client via your preferred package manager or from the Steam website.
3. In the lower left corner of your Steam library, click the "Add a Game" button, and select "Add a non-Steam game...".
4. Click "Browse...", navigate to the folder where you stored the game, and select "GAMENAME.exe". Then, click "Add selected programs" and the game now shows up in your Steam library.

## Linux - Wine 
Requires terminal.

1. Extract the game folder from the .zip/archive file and store it in any folder you wish, !!AS LONG AS THAT FOLDER IS NOT BACKED UP BY CLOUD STORAGE!!.
2. Install your preferred version of Wine from the WineHQ website
https://www.winehq.org/
It is recommended to install Wine manually, as the package distributed by many package managers are outdated. Version 11.0 is known to run LT games in a stable manner. Older versions are untested.
3. Open "GAMENAME.exe" with Wine.

## ITCH.IO
LT-games running in a web browser should run natively on all systems. No additional setup is required, though do note the first boot may take 10-20 seconds, due to the browser installing Python.

## Linux - Build from Source
NOTE: Most creators will ship the blank .exe engine with their game files attached. If this is the case, you can build the game from source. However, if the creator has included engine hacking in their project, this method WILL NOT WORK. If you are unsure, please contact the developer(s) of the LT game you want to play. If the developer(s) have a native version for linux available for download, you can skip step 3.

1. Install the following programs (preferred versions if possible):
```
python==3.12
python3pip
pygame-ce==2.5.7
pyinstaller==6.2.0
PyQt5==5.15.10
mypy==1.8.0
mypy-extensions==1.0.0
```
* LT is tested only on Python 3.12, and is potentially unstable or will not boot on other versions. Many current Linux distributions already come with Python 3.12 (type "python3 --version" to see yours); others can install it beside their own with pyenv (https://github.com/pyenv/pyenv). With your system's own Python, install the programs above in a virtual environment inside the lt-maker folder ("python3 -m venv venv", then "source venv/bin/activate" in each new terminal), as most distributions refuse pip installs into the system's Python.
* Some Linux distributions (mainly Ubuntu and Ubuntu-based distributions) may have trouble installing PyQt5. In that case, try: "sudo apt-get install python3-pyqt5".

2. Clone the following repository to your prefered storage location;
```
https://gitlab.com/rainlash/lt-maker.git
```
* If the creator has their own repository set up, clone that instead.

3. Grab the folder named "GAMETITLE.ltproj" from the windows version and put it inside the "lt-maker" folder. Delete the "default.ltproj" folder.

4. Open a terminal window in the folder and type "python3 run_engine.py". The engine should now boot up with the desired game. You can also create a script to perform this command. It is recommended to run this script in the terminal, as the game uses the terminal as a log.

* If the desired game does not boot up, change the command to "python3 run_editor.py", click the "Open other" button and select the "GAMENAME.ltproj" folder. Once the editor opens, click the play icon in the icon bar and then select the "Test Full Game..." option. From there, you can play as normal.

## MacOS - Wine
NOTE: Most creators will ship the blank .exe engine with their game files attached. For maximum stability, the MacOS version needs the python version of the engine to run in Wine. If you are unsure, please contact the developer(s) of the LT game you want to play.

1. Download and extract the game folder from its archive file to a desired location.

* If the developer(s) have a python version available, you can skip steps 2 and 3.

2. Download the LT repository and place it in desired location:
```
https://gitlab.com/rainlash/lt-maker.git
```

3. Grab the "GAMENAME.ltproj" folder and place it into the "lt-maker" folder. Remove the "default.ltproj" folder from the "lt-maker" folder.

4. Install Homebrew
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

5. Install Wine
```
brew install wine-stable
```

6. Install Miniconda
```
brew install --cask miniconda
```

7. Initialize conda in your shell
```
conda init "$(basename "${SHELL}")"
```

8. Perform the following steps before first boot;
```
cd lt-maker
conda create -n fe-i-lt python=3.12.10
conda activate fe-i-ltproj
```

9. Setup Windows Python;
```
curl -O https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
wine python-3.12.10-amd64.exe
```

10. Install the following requirements IN Wine Python;
```
wine pip install -r
python3pip
pygame-ce==2.5.7
pyinstaller==6.2.0
PyQt5==5.15.10
mypy==1.8.0
mypy-extensions==1.0.0
```

11. Execute the following commands;
```
cd lt-maker
conda activate fe-i-lt
wine python run_engine.py
```

## Android
Refer to the following links;
* https://feuniverse.us/t/lex-talionis-on-android-its-time/28374
* https://feuniverse.us/t/lex-talionis-on-android-its-time/28374/6