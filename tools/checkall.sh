#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


cd $SCRIPT_DIR


./codecheck.sh
./doccheck.sh
./typecheck.sh
./mdcheck.sh


echo -e "\neverything is fine"
