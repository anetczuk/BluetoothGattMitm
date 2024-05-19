#!/bin/bash

##
## Script installs copy of package into Python's user directory.
##

set -eu

## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


## creates "*.egg-info" and "build" directory along package dir

pip3 install --user "$SCRIPT_DIR" 
