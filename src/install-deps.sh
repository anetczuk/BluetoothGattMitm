#!/bin/bash

set -eu

## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


# ## system packages 
# sudo apt install python3-gi


# ## ensure required version of pip3
# pip3 install --upgrade 'pip>=18.0'


## install requirements
pip3 install -r $SCRIPT_DIR/requirements.txt


echo -e "\ninstallation done\n"
