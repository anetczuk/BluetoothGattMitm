#!/bin/bash

set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


hciconfig hci0 features

echo

bluetoothctl show
