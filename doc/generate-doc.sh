#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


SRC_DIR="$SCRIPT_DIR/../src"

HELP_PATH=$SCRIPT_DIR/help.txt
PROGRAM_COMMAND="btgattmitm/main.py"


cd $SRC_DIR


PROGRM_LABEL="${PROGRAM_COMMAND}"
if [ -f "${PROGRM_LABEL}" ]; then
    PROGRM_LABEL=$(basename "${PROGRM_LABEL}")
fi


generate_help() {
    echo "" > ${HELP_PATH}
    #echo "## <a name=\"main_help\"></a> ${PROGRM_LABEL} --help" > ${HELP_PATH}
    #echo -e "\`\`\`" >> ${HELP_PATH}
    ${PROGRAM_COMMAND} --help >> ${HELP_PATH}
    #echo -e "\`\`\`" >> ${HELP_PATH}
}


generate_help


$SCRIPT_DIR/generate_small.sh
