#!/bin/bash


##
## Legacy advertisement example.
##


set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


source "${SCRIPT_DIR}/_lib.bash"

read_iface_mac $@


## authenticate as root
sudo date > /dev/null


#########################################################


validate_btmgmt_iface "${IFACE}"


INSTANCE=2

ADV_DEV_NAME="TH0xyz"


### this does not work
# echo "=== disabling random address ==="
# # sudo systemctl disable bluetooth
# # sudo systemctl stop bluetooth
# 
# ## disable randomized MAC (privacy)
# sudo btmgmt --index ${IFACE} power off
# # sudo btmgmt --index ${IFACE} le on
# sudo btmgmt --index ${IFACE} bredr off
# sudo btmgmt --index ${IFACE} privacy off
# sudo btmgmt --index ${IFACE} power on
# 
# # sudo systemctl enable bluetooth
# # sudo systemctl start bluetooth


#  ## set random address
# ## requires disabled advertising and scanning
# sudo hcitool -i hci0 cmd 0x08 0x0005   F6 E5 D4 C3 B2 A2


DEVICE_MAC="11:22:33:44:55:66"

if [[ "${DEVICE_MAC}" != "" ]]; then
    echo "=== changing MAC ==="
    echo "setting new mac address: ${DEVICE_MAC}"
    sudo btmgmt --index ${IFACE} power off
    sudo btmgmt --index ${IFACE} public-addr "${DEVICE_MAC}"
    sudo btmgmt --index ${IFACE} power on
fi


echo "=== enabling advertising ==="
sudo btmgmt --index ${IFACE} le on

## disble default advertisement - "add-adv" will activate advertisement automatically with custom data
sudo btmgmt --index ${IFACE} advertising off


# echo "=== setting name ==="
#sudo btmgmt --index ${IFACE} name "${ADV_DEV_NAME}"


echo "=== setting adv ==="
sudo btmgmt --index ${IFACE} clr-adv || true

adv_data=""

## 0x01 - Flags
adv_data=$(add_field_to_data "${adv_data}" "0x01 0x06")

## 0x09 - device name
echo "advertising name: ${ADV_DEV_NAME}"
hex_string=$(ascii_to_hex "${ADV_DEV_NAME}")
adv_data=$(add_field_to_data "${adv_data}" "0x09 ${hex_string}")

## 0x02 - Incomplete List of 16-bit Services UUIDS
adv_data=$(add_field_to_data "${adv_data}" "0x02 0x50 0xFD")

## 0x16 - Service data
service_data="0x16 0x50 0xFD 0x41 0x00 0x00 0x08 0x63 0x63 0x71 0x68 0x76 0x66 0x6A 0x78"
adv_data=$(add_field_to_data "${adv_data}" "${service_data}")

adv_data_length=$(get_data_length "${adv_data}")
echo "advertising data length: ${adv_data_length}"

adv_data=$(remove_hex_prefix "${adv_data}")


echo "=== setting scan response"

scanresp_data=""

# 0xFF - manufacturer name
manufacturer_data="0xFF d0 07 00 00 01 04 96 1c 64 ff 53 ed 16 10 e1 91 1c f1 bf 03 b5 f8"
scanresp_data=$(add_field_to_data "${scanresp_data}" "${manufacturer_data}")

scanresp_data_length=$(get_data_length "${scanresp_data}")
echo "scan response data length: ${scanresp_data_length}"

scanresp_data=$(remove_hex_prefix "${scanresp_data}")

echo "adv data: ${adv_data}"
echo "scanresp data: ${scanresp_data}"

services_uuids=""
# services_uuids="-u 99112233-3344-1024-8899-001122334455"

sudo btmgmt --index ${IFACE} add-adv \
            ${services_uuids} \
            -d "${adv_data}" -s "${scanresp_data}" ${INSTANCE}


echo "=== info ==="
# sudo btmgmt --index ${IFACE} advinfo
# sudo btmgmt --index ${IFACE} advsize ${INSTANCE}
sudo btmgmt --index ${IFACE} info


if [[ "${DEVICE_MAC}" != "" ]]; then
    echo "=== setting public mac ==="
    echo "setting new mac address: ${DEVICE_MAC}"
    # at least works, but better to disable privacy instead of setting MAC directly
    REVERSED_MAC=$(echo $DEVICE_MAC | tr ':' '\n' | tac | paste -sd' ' -)
    ## important, MAC without quotes!
    sudo hcitool -i hci0 cmd 0x08 0x0035   02   ${REVERSED_MAC}
    
    hcitool dev
fi


echo "completed"
