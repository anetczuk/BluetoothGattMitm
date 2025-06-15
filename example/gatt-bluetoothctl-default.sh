#!/bin/bash


##
## Legacy advertisement example.
##


set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


## authenticate as root
sudo date > /dev/null


#########################################################


# ##
# ## disable randomized MAC (privacy)
# ##
# sudo btmgmt --index 0 power off
# sudo btmgmt --index 0 privacy off
# sudo btmgmt --index 0 power on


#echo "setting device class"
#sudo hciconfig hci0 class 0x00000000
#sudo hciconfig hci0 class 0x007c010c
#sudo btmgmt --index 0 class 0x0000 0x00


##
## set GATT server
##
echo "setting advertisement and GATT"
sudo bluetoothctl <<EOF
system-alias GATT03
pairable on
discoverable on
menu advertise
clear
name GATTx
back
advertise on
EOF

### does not work
# menu gatt
# register-service e2d36f99-8909-4136-9a49-d825508b297b
# register-characteristic 0x1234 read
# register-characteristic 0x4567 read,write
# register-application
# back


echo "info"

bluetoothctl show

systemctl status bluetooth.service --no-pager


echo "completed"
