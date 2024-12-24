# CAPASM installation instructions

Index
-----

* [Requirements](#requirements)
* [Overview of the Installation from PyPi](#overview-of-the-installation-from-pypi)
     * [Installation on Windows](#installation-on-windows)
     * [Installation on macOS](#installation-on-macos)
     * [Installation on Linux](#installation-on-linux)
* [Installation from GitHub](#installation-from-github)
* [Installation of development versions](#installation-of-development-versions)
* [Virtual Environment Maintenance](#virtual-environment-maintenance)


## Requirements

CAPASM requires a Python interpreter version 3.6 or higher. Python version 3.11 is currently recommended.


## Overview of the Installation from PyPi

This installation method of CAPASM requires the following steps:

1. Get a Python interpreter for your system:

* Windows: install it from Microsoft Store (free)
* macOS: download it from the [www.python.org](https://www.python.org) website and install the pkg file
* Linux: install it from system repositories if not already installed on your system


2. Create a virtual Python environment for CAPASM

A virtual environment is a directory tree that contains a dedicated Python runtime version with CAPASM for the current user. This environment must be "activated" (see below) and it works isolated from the operating systems or other environments.

A virtual environment can be removed by simply removing the directory in question.

3. Activate the virtual Python environment

The virtual environment is activated by calling an activation script. An activated environment is indicated
in the prompt string. 

4. Install CAPASM

This step fetches CAPASM from the [Python Package Index](https://pypi.org) (PyPi), which is the official 
third-party software repository for Python. You can also install additional software in the 
environment from the Python Package Index.

<b>Warning: always call the Python interpreter "python3" if you create a virtual environment and "python" after the environment has been activated!!!</b>

5. Maintain the virtual environment

See [Virtual environment maintenance](#virtual-environment-maintenance)


### Installation on Windows

To install the Python interpreter open the Microsoft Store, search for Python and select the recommended version (see above) for installation. Python is installed for the current user.

Example: create a virtual environment "py311" in the home directory of the current user, install and start CAPASM:


     C:\>cd %USERPROFILE%                                  (change to users home directory)
     
     C:\Users\bug400>python3 -m venv py311                 (create environment %USERPROFILE%\py311, use python3 to call the interpreter here!!!)

     C:\Users\bug400>py311\scripts\activate                (activate the environment, the environment name becomes component of the prompt string)
     
     (py311) C:\Users\bug400>python -m pip install capasm  (install CAPASM with the required runtime dependecies)
     Collecting capasm
       Obtaining dependency information for capasm from https://files.pythonhosted.org/packages/3e/
     
     ...
     
     Installing collected packages: capasm
     Successfully installed capasm-1.0.1 
     
     [notice] A new release of pip is available: 23.2.1 -> 23.3.2
     [notice] To update, run: python.exe -m pip install --upgrade pip
     
     (py311) C:\Users\bug400>capasm                        (start CAPASM)



If the Python interpreter is run for the first time, a window opens and requests firewall permissions. To grant permissions for Python applications administrator privileges are needed.

You can invoke CAPASM (or other programs of the CAPASM suite) without activating the environment by calling:

     %USERPROFILE%\py311\scripts\capasm



### Installation on macOS

Install Python for macOS from the [Python website](https://www.python.org/). Choose the recommended Python version (see above) on the Downloads page. Download and install the macOS 64-bit universal installer. You need administrator privileges for that.

See [Using Python on a Mac](https://docs.python.org/3/using/mac.html) for further details.

Example: create a virtual environment "py311" in the home directory of the current user, install and start CAPASM:

     node1-mac:~ bug400$ python3 -m venv py311                  (create virtual environment ~/py311)
     node1-mac:~ bug400$ source py311/bin/activate              (activate virtual environment ~/py311)
     (py311) node1-mac:~ bug400$ python -m pip install capasm   (install CAPASM and required runtime components)
     Collecting capasm
       Obtaining dependency information for capasm from https://files.pythonhosted.org/packages/3e

     ...

     Installing collected packages: capasm
     Successfully installed capasm-1.0.1 
     
     [notice] A new release of pip is available: 23.2.1 -> 23.3.2
     [notice] To update, run: pip install --upgrade pip
     (py311) node1-mac:~ bug400$ capasm                        (start CAPASM)
     
You can invoke CAPASM without activating the environment by calling:

     node1-mac:~ bug400$ ~/py311/bin/capasm


### Installation on Linux

Generally, it is recommended to use the Python Interpreter provided by the Linux distribution. 

Install CAPASM from the Python Package Index. See the macOS installation instructions for details.


## Installation from GitHub

To install CAPASM this way, the above mentioned system requirements must be installed on your computer.

Download the latest source code from the [CAPASM Releases page](https://github.com/bug400/capasm/releases/) and unzip the CAPASM source code in an arbitrary location. You get the CAPASM directory capasm-x.y.z, where x.y.z is the version number.

Now you can start the assembler with:

      python <Path to the CAPASM directory>/start.py capasm (parameters)

or the *caplif* tool with:

      python <Path to the CAPASM directory>/startup.py caplif (parameters)

You can call the Python script *start.py* from everywhere in the file system. Because this scripts must not be moved out of the CAPASM directory it is recommended to create short shell- (Linux, macOs) or CMD- (Windows) helper scripts and put them into a directory which is specified in your search path.

Note: it depends on your Linux distribution and system configuration whether the Python interpreter is invoked as "phyton" or "python3".

The [CAPASM Releases page](https://github.com/bug400/capasm/releases/) provides an installation package for the current Debian release. This package might also be installable on Linux distributions which were derived from the Debian release in question.


## Installation of development versions

To use development versions of CAPASM download the capasm-master.zip file from GitHub [front page of CAPASM](https://github.com/bug400/capasm) ("Download ZIP" button). 

Unzip the downloaded file to an arbitrary location of your file system.

The name of the unzipped CAPASM directory is always capasm-master.

Proceed as specified in the section above.

Note to beta or development versions:
* Beta versions were tested more thoroughly also on all supported platforms. They are intended for public testing but should not be used for production.
* The beta or development versions do not affect the configuration of an already installed production version because a different naming convention is used for the configuration files.

To obtain more recent development versions of CAPASM download the capasm-master.zip file again. If you are familiar with a git client you can synchronize a local capasm-master directory with the remote GitHub repository.


## Virtual Environment Maintenance

Generally, it is recommended to check whether a new version of CAPASM exists and to upgrade that package only.

Note: To upgrade the python interpreter itself it is safest to uninstall the old interpreter, remove the environment and reinstall/recreate interpreter and environment.

To do virtual environment maintenance you have to activate it first:

     <path to venv directory>/scripts/activate (Windows)
     or
     source <path to venv directory>/bin/activate (macOS, Linux)


Deactivate an environment:

     deactivate

Check for packages that can be updated:

     python -m pip list -o

Update CAPASM

     python -m pip install --upgrade capasm


Further maintenance commands:

List installed packages:

     python -m pip list

Install a package:

     python -m pip install <packagename>

Show details of a package:

     python -m pip show <packagename>

Remove a package:

     python -m pip uninstall <packagename>

Check for new versions of a package

     python -m pip list -o

Upgrade a package (pip itself can be upgraded with pip)

     python -m pip install --upgrade <packagename>

Clear package cache (saves space on disk):

     python -m pip cache  purge

Remove an environment:

     delete the entire directory tree of the environment

