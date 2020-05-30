﻿CAPASM installation instructions
=================================

Index
-----

* [General](#general)
* [Installation with the ANACONDA platform](#installation-with-the-anaconda-platform)
* [Installation without the ANACONDA platform](#installation-without-the-anaconda-platform)
* [Installation of development versions from the GitHub Repository](#installation-of-development-versions-from-the-GitHub-Repository)

General
-------

CAPASM requires a Python interpreter version 3.6 or higher. 

It is recommended to use the [ANACONDA platform](https://www.continuum.io) 
to install CAPASM and the required Python software and keep them up to date.

Note: dependent on the operating systems the python version 3 interpreter may becalled either *python* or *python3*.


Installation with the ANACONDA platform
---------------------------------------

Anaconda is a Python distribution widely used in Data Science applications.
It provides an Python environment that is easy to install and maintain
on Windows, mac OS and Linux. The Anaconda cloud gives access to more than
1000 Python applications.

The Anaconda distribution installs more then 150 Python packages on your
computer which are not needed to run CAPASM. Therefore it is recommended
to use the Miniconda installer instead which only provides Python and the
Anaconda package manager.

You need approximately 700MB free disk space for CAPASM and the Python 
runtime environment. Everything is installed as a local user and thus no 
administrator privileges are needed. 

Note: CAPASM is available for Python 3.7 and Python 3.8 for the Anaconda/Miniconda platform at the moment. Future versions of CAPASM will only support 
Python 3.8 if that version becomes default of the Anaconda/Miniconda installer.

**Note for Windows**: Due to recent changes in the Anaconda installation
environment it is strongly encouraged to do a clean reinstall of an older
Anaconda/Miniconda environment.

Download the Python 3.x version of [Miniconda](https://docs.conda.io/en/latest/miniconda.html) and follow the [Installation Instructions](https://conda.io/projects/conda/en/latest/user-guide/install/index.html) and install Miniconda first.


**Note for Windows**: Do not instruct the installer to change the PATH. 
Use always the Anaconda Prompt which is available from the start menu.

**Note for Linux and mac OS**: If you install Miniconda the first time
then let the installer modify the PATH variable of your environment.

Reopen a new terminal window (Linux, mac OS) or Anaconda Prompt (Windows) 
and type:

     conda update conda
     conda config --add channels bug400
     conda install capasm

This installs CAPASM. 

To update CAPASM and the Python runtime type:

     conda update --all

in a terminal window (Linux and mac OS) or Anaconda Prompt (Windows).

To start the *capasm* assembler type:

     capasm -h

in a terminal window (Linux and mac OS) or Anaconda Prompt (Windows). This
shows a help screen with a description of the necessary command line parameters
to run the program. That way the other programs of the CAPASM software suite like *caplif* are invoked.

You should issue occasionally:

     conda clean --all

to clean the conda package cache and save disk space.


Installation without the ANACONDA platform
------------------------------------------

The requirements specified above must be available on the system.

On Debian based Linux systems you can install the CAPASM Debian package.

On all other systems unzip the CAPASM source code in an arbitrary
location. You get the CAPASM directory capasm-x.y.z, where x.y.z is
the version number.

Now you can start the assembler with:

      python <Path to the CAPASM directory>/start.py capasm (parameters)

or the *caplif* tool with:

      python <Path to the CAPASM directory>/startup.py caplif (parameters)

If you get the error message "This script requires Python 3.6 or newer!" use python3 instead.

You can call the Python script *start.py* from everywhere in the file system. Because this scripts must not be moved out of the CAPASM directory it is recommended to create short shell- (Linux, Mac os) or CMD- (Windows) helper scripts and put them into a directory which is specified in your search path.


Installation of development versions from the GitHub Repository
---------------------------------------------------------------

To use development versions of CAPASM download the capasm-master.zip file from GitHub [front page of CAPASM](https://github.com/bug400/capasm) ("Download ZIP" button). 

Unzip the downloaded file to an arbitrary location of your file system.

The name of the unzipped CAPASM directory is always capasm-master.

Proceed as specified in the section above.

Note to beta or development versions:
* Beta versions are tested more thoroughly also all supported platforms. They are intended for public testing but should not be used for production.
* The beta or development versions do not affect the configuration of an already installed production version because a different naming convention is used for the configuration files.

To obtain more recent development versions of CAPASM download the capasm-master.zip file again. If you are familiar with a git client you can synchronize a local capasm-master directory with the remote GitHub repository.