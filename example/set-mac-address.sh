#!/bin/bash

set -eux


if [ $# -ne 1 ]; then 
    echo "expected one argument - mac address of BL device"
    exit 1
fi


MAC="$1"


hcitool dev 

sudo btmgmt --index 0 power off

sudo btmgmt --index 0 public-addr "${MAC}"

sudo btmgmt --index 0 power on


# sudo hciconfig hci0 down
# 
# sudo bdaddr -i hci0 "${MAC}"
# 
# sudo hciconfig hci0 up

hcitool dev
