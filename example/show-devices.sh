#!/bin/bash

set -eux


hcitool dev 

bluetoothctl list


echo "other info:"

hciconfig -a

btmgmt info
