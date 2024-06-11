#!/bin/bash


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


src_dir=$SCRIPT_DIR/../src
examples_dir=$SCRIPT_DIR/../example


find $src_dir -name "*.py" | xargs sed -i 's/[ \t]*$//'

find $examples_dir -name "*.py" | xargs sed -i 's/[ \t]*$//'

find $SCRIPT_DIR -name "*.py" | xargs sed -i 's/[ \t]*$//'


echo "done"
