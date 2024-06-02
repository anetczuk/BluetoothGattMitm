#!/bin/bash

set -eu


if [ $# -ne 1 ]; then 
    echo "expected one argument - mac address of BLE device"
    exit 1
fi


MAC="$1"


sudo hcitool lecc --random "$MAC"
