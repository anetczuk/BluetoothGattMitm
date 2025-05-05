#!/bin/bash


##
## Legacy advertisement with scan response allowing to use 62 bytes of data.
##


set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


source "${SCRIPT_DIR}/_lib.bash"


## authenticate as root
sudo date > /dev/null


#########################################################


sudo hciconfig $IFACE name "ble_dongle"


echo "using interface: $IFACE"

reset_device "${IFACE}"


echo "=== setting advertisement parameters"

# 0x20 0x00       -> Advertising_Interval_Min (0x0020 = 32 * 0.625ms = 20ms)
# 0x20 0x00       -> Advertising_Interval_Max (same as min: 20ms)
# 0x00            -> Advertising_Type (0 = ADV_IND, connectable undirected advertising)
# 0x00            -> Own_Address_Type (0 = Public Device Address)
# 0x00            -> Peer_Address_Type (ignored for ADV_IND, typically 0)
# 0x00 0x00 0x00 0x00 0x00 0x00 -> Peer_Address (ignored here)
# 0x07            -> Advertising_Channel_Map (bitmask: 0x07 = all three channels: 37, 38, 39)
# 0x00            -> Advertising_Filter_Policy (0 = allow any device to connect/scan)

hcitool_cmd "0x08 0x0006  20 00  20 00  00 00 00  00 00 00 00 00 00  07 00"


echo "=== setting advertisement data"

adv_data=""

## 0x01 - Flags
adv_data=$(add_field_to_data "${adv_data}" "0x01 0x06")

## 0x02 - Incomplete List of 16-bit Services UUIDS
incomplete_services="0x02 0x50 0xFD"
adv_data=$(add_field_to_data "${adv_data}" "${incomplete_services}")

## 0x09 - device name
hex_string=$(ascii_to_hex "TH09")
adv_data=$(add_field_to_data "${adv_data}" "0x09 ${hex_string}")

## 0x16 - Service data
service_data="0x16 0x50 0xFD 0x41 0x00 0x00 0x08 0x63 0x63 0x71 0x68 0x76 0x66 0x6A 0x78"
adv_data=$(add_field_to_data "${adv_data}" "${service_data}")

## add total length
adv_data_length=$(get_data_length "${adv_data}")
adv_data=$(add_length "${adv_data}")

adv_cmd_string="0x08 0x0008  ${adv_data}"

echo "executing hcitool command: ${adv_cmd_string} data length: ${adv_data_length}"

hcitool_cmd "$adv_cmd_string"


echo "=== setting scan response"

adv_data=""

# ## 0x09 - device name
# hex_string=$(ascii_to_hex "TH09")
# adv_data=$(add_field_to_data "${adv_data}" "0x09 ${hex_string}")

## 0xFF - manufacturer name
manufacturer_data="0xFF d0 07 00 00 01 04 96 1c 64 ff 53 ed 16 10 e1 91 1c f1 bf 03 b5 f8"
adv_data=$(add_field_to_data "${adv_data}" "${manufacturer_data}")

## add total length
adv_data_length=$(get_data_length "${adv_data}")
adv_data=$(add_length "${adv_data}")

adv_cmd_string="0x08 0x0009  ${adv_data}"

echo "executing hcitool command: ${adv_cmd_string} data length: ${adv_data_length}"

hcitool_cmd "$adv_cmd_string"


echo "=== enabling advertisement"

# Enable advertising
hcitool_cmd "0x08 0x000A 01"


## disable
# sudo hcitool -i "${IFACE}" cmd 0x08 0x000A 00


echo "completed"
