#!/bin/bash


##
## Legacy advertisement example.
##


set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


source "${SCRIPT_DIR}/_lib.bash"


## authenticate as root
sudo date > /dev/null


#########################################################


validate_btmgmt_iface "${IFACE}"


INSTANCE=2

ADV_DEV_NAME="TH09"


echo "=== enabling advertising ==="
sudo btmgmt --index ${IFACE} le on

## disble default advertisement - "add-adv" will activate advertisement automatically with custom data
sudo btmgmt --index ${IFACE} advertising off


# echo "=== setting name ==="
#sudo btmgmt --index ${IFACE} name "${ADV_DEV_NAME}"
#sudo btmgmt --index ${IFACE} public-addr "${BT_DEVICE_MAC}"


echo "=== setting adv ==="
sudo btmgmt --index ${IFACE} clr-adv || true

adv_data=""

## 0x01 - Flags
adv_data=$(add_field_to_data "${adv_data}" "0x01 0x06")

## 0x09 - device name
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

sudo btmgmt --index ${IFACE} add-adv -d "${adv_data}" ${INSTANCE}


# echo "=== info ==="
# sudo btmgmt --index ${IFACE} advinfo
# sudo btmgmt --index ${IFACE} advsize ${INSTANCE}

echo "completed"
