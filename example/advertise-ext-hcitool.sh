#!/bin/bash


##
## Extended advertisement example.
##


set -eu


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


source "${SCRIPT_DIR}/_lib.bash"

read_iface_mac $@


## authenticate as root
sudo date > /dev/null


#########################################################


sudo hciconfig $IFACE name "ble_dongle"


echo "using interface: $IFACE"

reset_device "${IFACE}"


## advertisement data instance (must be greater than 0)
ADV_HANDLE="0x01"


echo "=== setting extended advertisement parameters"

## extended advertising parameters command
#   0x00 \                        # Advertising Handle = 0  
#   0x10 0x00 \                   # Properties: Extended, non-connectable, non-scannable
#   0xA0 0x00 0x00 \              # Min interval = 0x00A0 = 160 (160 * 0.625ms = 100ms)
#   0xA0 0x00 0x00 \              # Max interval = 100ms
#   0x07 \                        # Channel map: 37, 38, 39 (all advertising channels)
#   0x00 \                        # Own address type: Public
#   0x00 \                        # Peer address type: Public (not used here)
#   0x00 0x00 0x00 0x00 0x00 0x00 \ # Peer address: (not used, directed only)
#   0x00 \                        # Filter policy: Allow Scan Request from Any, Allow Connect Request from Any
#   0x7F \                        # TX power: Host has no preference (let controller decide)
#   0x01 \                        # Primary PHY: 1M (0x01)
#   0x00 \                        # Secondary max skip: 0 (no skip)
#   0x01 \                        # Secondary PHY: 1M (0x01)
#   0x00 \                        # Advertising SID: 0
#   0x00                          # Scan request notification: disabled

hcitool_cmd "0x08 0x0036  ${ADV_HANDLE} 0x00 0x00  0xA0 0x00 0x00  0xA0 0x00 0x00  0x07 0x00 0x00  0x00 0x00 0x00 0x00 0x00 0x00  0x00 0x7F 0x01 0x00 0x01 0x00 0x00"


echo "=== setting extended advertisement data"

adv_data=""

## 0x01 - Flags
#flags=$(add_length "0x01 0x06")
#adv_data="${flags}"
adv_data=$(add_field_to_data "${adv_data}" "0x01 0x06")

## 0x02 - Incomplete List of 16-bit Services UUIDS
incomplete_services="0x02 0x50 0xFD"
adv_data=$(add_field_to_data "${adv_data}" "${incomplete_services}")

## 0x16 - Service data
service_data="0x16 0x50 0xFD 0x41 0x00 0x00 0x08 0x63 0x63 0x71 0x68 0x76 0x66 0x6A 0x78"
adv_data=$(add_field_to_data "${adv_data}" "${service_data}")

# 0xFF - manufacturer name
manufacturer_data="0xFF d0 07 00 00 01 04 96 1c 64 ff 53 ed 16 10 e1 91 1c f1 bf 03 b5 f8"
adv_data=$(add_field_to_data "${adv_data}" "${manufacturer_data}")

## 0x09 - device name
hex_string=$(ascii_to_hex "TH09")
adv_data=$(add_field_to_data "${adv_data}" "0x09 ${hex_string}")

## add total length
adv_data_length=$(get_data_length "${adv_data}")
adv_data=$(add_length "${adv_data}")

## extended advertising data command
#   0x00 \                      # Advertising Handle
#   0x03 \                      # Operation: Complete extended advertising data (0x03 = complete)
#   0x01 \                      # Fragment preference: Minimize fragmentation (0x01)
#   0x1F \                      # Data length = 31 bytes
#   0xF8 0x00 0x00 ... (31 bytes total)

adv_cmd_string="0x08 0x0037  ${ADV_HANDLE} 0x03 0x01   ${adv_data}"

echo "executing hcitool command: ${adv_cmd_string} data length: ${adv_data_length}"

hcitool_cmd "$adv_cmd_string"


echo "=== enabling extended advertisement" 
# extended Advertising enable command
hcitool_cmd "0x08 0x0039 0x01 0x01 ${ADV_HANDLE} 0x00 0x00 0x00"

# sudo hciconfig $IFACE leadv 1


## disable
# sudo hcitool -i "${IFACE}" cmd 0x08 0x000A 00


echo "completed"
