#!/bin/bash


##
## Show information about local BT adapters.
##


set -eux


hcitool dev 

bluetoothctl list


echo "other info:"

hciconfig -a

btmgmt info
