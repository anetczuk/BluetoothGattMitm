#!/bin/bash

set -eu


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

SRC_DIR=$(realpath "$SCRIPT_DIR/../src")


ARGS=()
NO_PROMPT=false

while :; do
    if [ -z "${1+x}" ]; then
        ## end of arguments (prevents unbound argument error)
        break
    fi

    case "$1" in
      --no-prompt)  NO_PROMPT=true 
                    shift ;;
      *)  ARGS+=($1)
          shift ;;
    esac
done


VENV_SUBDIR=""
if [ "${#ARGS[@]}" -gt 0 ]; then
    VENV_SUBDIR=${ARGS[0]}
fi

VENV_DIR="$SCRIPT_DIR/../venv/$VENV_SUBDIR"


### if directory exists then prompt to delete

if [ -d "$VENV_DIR" ]; then
    if [ "$NO_PROMPT" = false ]; then
        read -p "Directory [$VENV_DIR] exists. Do You want to remove it (y/N)? " -n 1 -r
        echo    # (optional) move to a new line
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Given target directory [$VENV_DIR] exists, remove it and restart the script"
            exit 1
        fi
    fi
    # do dangerous stuff
    echo "Removing directory [$VENV_DIR]"
    rm -rf "$VENV_DIR"
fi


mkdir -p "$VENV_DIR"

VENV_DIR=$(realpath "$VENV_DIR")
    

echo "Creating virtual environment in $VENV_DIR"

python3.8 -m venv $VENV_DIR
# python3 -m venv $VENV_DIR
# python2 -m virtualenv $VENV_DIR


### creating venv start script

SCRIPT_CONTENT='#!/bin/bash

##
## File was generated automatically. Any change will be lost. 
##

set -eu

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

VENV_DIR="$VENV_ROOT_DIR"


START_COMMAND=
if [ "$#" -ge 1 ]; then
    START_COMMAND=$(cat <<EOL
## executing command
echo "executing: $@"
eval "$@"
EOL
)
fi


### create temporary file
tmpfile=$(mktemp venv.run.XXXXXX.sh --tmpdir)

### write content to temporary
cat > $tmpfile <<EOL
source $VENV_DIR/bin/activate
if [ \$? -ne 0 ]; then
    echo -e "Unable to activate virtual environment, exiting"
    exit 1
fi

$START_COMMAND

exec </dev/tty 
EOL


echo "Starting virtual env"

bash -i <<< "source $tmpfile"


rm $tmpfile
'

SCRIPT_CONTENT="${SCRIPT_CONTENT//'$VENV_ROOT_DIR'/$VENV_DIR}"
SCRIPT_PATH="$VENV_DIR/activatevenv.sh"
START_VENV_SCRIPT_PATH="$SCRIPT_PATH"
echo "$SCRIPT_CONTENT" > "$SCRIPT_PATH"
chmod +x "$SCRIPT_PATH"


## create shortcut script inside venv directory
## 1 -- command
## 2 -- output scritpt
create_venv_shortcut() {
    local COMMAND="$1"
    local SCRIPT_PATH="$2"
    
    local SCRIPT_CONTENT='#!/bin/bash
##
## File was generated automatically. Any change will be lost. 
##

set -eu

'

    ## concatenate command
    local SCRIPT_CONTENT="${SCRIPT_CONTENT}${COMMAND}"
    
    echo "$SCRIPT_CONTENT" > "$SCRIPT_PATH"
    chmod +x "$SCRIPT_PATH"
}


### creating project start script
create_venv_shortcut "$VENV_DIR/activatevenv.sh \"set -eu; $SRC_DIR/testastgraph/runtests.py \$@; exit\"" "$VENV_DIR/runtests.py"


### install required packages
echo "Installing dependencies"
$START_VENV_SCRIPT_PATH "$SCRIPT_DIR/../src/install-deps.sh; exit"


echo "to activate environment run: $VENV_DIR/activatevenv.sh"
