#!/bin/bash

set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


source "${SCRIPT_DIR}/_lib.bash"


## authenticate as root
sudo date > /dev/null


#########################################################


# OGF = 0x08 -> LE Controller commands

sudo hciconfig -a

btmgmt info

sudo hciconfig $IFACE features



sudo btmon -i $IFACE &

btmon_pid=$!

sleep 1


echo "using interface: $IFACE"

# print local features
echo "adapter local supported commands:"
# "7.4.2. Read Local Supported Commands command" from bluetooth code spec
sudo hcitool -i $IFACE cmd 0x04 0x0002 > /dev/null

echo "adapter ble features:"
sudo hcitool -i $IFACE cmd 0x08 0x0003 > /dev/null

## kill subprocesses
pkill -P $$

