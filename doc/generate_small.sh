#!/bin/bash

set -eu


##
## Find PNG files and generate small versions suitable for GitHub readmes.
##


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


big_suffix="-big."
small_suffix="-small."

for filename in $(find $SCRIPT_DIR -name "*.png"); do
    if [[ $filename == *"$small_suffix"* ]]; then
        continue
    fi
    small_name=${filename/".png"/"${small_suffix}png"}

    ##if [[ $filename != *"$big_suffix"* ]]; then
    ##    continue
    ##fi
    ##small_name=${filename/$big_suffix/$small_suffix}

    echo "converting: $filename -> $small_name"
    convert $filename -strip -resize 350 $small_name
done
