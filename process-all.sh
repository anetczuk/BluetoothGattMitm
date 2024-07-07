#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


$SCRIPT_DIR/doc/generate-doc.sh

$SCRIPT_DIR/tools/mdpreproc.py $SCRIPT_DIR/README.md

$SCRIPT_DIR/tools/checkall.sh


echo "processing completed"
