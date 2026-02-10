#!/bin/bash


##
## Connect to nearby BT devices and read services and characteristics.
##


set -eu


if [ $# -ne 1 ]; then 
    echo "expected one argument - mac address of BLE device"
    exit 1
fi


MAC="$1"


sudo bluetoothctl connect "$MAC"

sleep 3

sudo bluetoothctl gatt.list-attributes

sudo bluetoothctl disconnect

echo "Done"
