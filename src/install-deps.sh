#!/bin/bash

set -eu

## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


# ## system packages 
# sudo apt install python3-gi

# sudo apt install libcairo-dev
# sudo apt install gobject-introspection
# sudo apt install libgirepository-1.0-dev


# ## ensure required version of pip3
# pip3 install --upgrade 'pip>=18.0'


## install requirements
pip3 install -r $SCRIPT_DIR/requirements.txt --break-system-packages


echo -e "\ninstallation done\n"
