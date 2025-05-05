#!/bin/bash


if [[ $# < 1 ]]; then
    echo "missing parameter: BT MAC address (eg. 00:11:22:33:44:55) or iface name (eg. hci0)"
    echo "available ifaces and mac addresses:"

    IFACES_LIST=$(hciconfig | awk '
/^hci[0-9]+/ { iface=$1 }
/BD Address:/ { print iface, $3 }
' | sort -u)

    echo "${IFACES_LIST}"
    exit 1
fi


INTERFACE_DATA="$1"

BT_DEVICE_MAC=""
IFACE=""


if [[ $INTERFACE_DATA =~ ^([A-Fa-f0-9]{2}:){5}[A-Fa-f0-9]{2}$ ]]; then
    ## given input is MAC address
    BT_DEVICE_MAC="$INTERFACE_DATA"
else
    ## assume that given input is interface name
    IFACE="$INTERFACE_DATA"
fi


if [[ -z ${IFACE+x} ]] || [[ -z "${IFACE}" ]]; then
    if [[ -z ${BT_DEVICE_MAC+x} ]]; then
        echo "missing IFACE or BT_DEVICE_MAC variables"
        echo "set one of them is required"
        exit 1
    fi

    ## hci device not given -- find it using MAC
    for hci_item in $(hciconfig | grep ^hci | cut -d: -f1); do
        MAC=$(hciconfig "$hci_item" | grep "BD Address" | awk '{print $3}')
        MAC=${MAC,,}    ## lowercase
        if [[ "$MAC" == "${BT_DEVICE_MAC,,}" ]]; then
            echo "Found interface: $hci_item mac: ${BT_DEVICE_MAC}"
            IFACE="${hci_item}"
            break
        fi
    done

    if [[ -z "${IFACE}" ]]; then
        echo "No matching HCI device for MAC: $BT_DEVICE_MAC"
        exit 1
    fi
fi


FAILED=0
hciconfig | grep "$IFACE" > /dev/null|| FAILED=1
#btmgmt info | grep "$IFACE" || FAILED=1

if [[ FAILED -eq 1 ]]; then
    echo "current devices:"
    #btmgmt info
    hciconfig -a
    echo "could not find device: $IFACE"
    exit 1
fi


#####################################################################


## for btmgmt
validate_btmgmt_iface() {
    local IFACENAME="$1"

    if [[ "${IFACENAME}" != "hci0" ]]; then
        echo "bad interface, current interfaces:"
        #btmgmt info
        hciconfig -a
    
        echo "there is bug in 'btmgmt' that causes application to ignore -i parameter, so it always uses 'hci0'"
        echo "workaround is to turn off other devices"
        exit 1
    fi
}


#####################################################################


## reset state of device
reset_device() {
    local interface="$1"

    FAILED=0
    sudo hciconfig $interface down || FAILED=1
    sudo hciconfig $interface up || FAILED=1
    
    #sudo hciconfig $IFACE reset || FAILED=1
    
    if [[ FAILED -eq 1 ]]; then
        echo "device down/up failure"
        sudo hciconfig -a
        exit 1
    fi
}


## $1 - hcitool output
check_event_status() {
    local output=$1
    
    data_line=$(echo "$output" | grep -A 1 "> HCI Event" | tail -n 1)
    
    # Check if event_line and data_line are found
    if [[ -z "$data_line" ]]; then
        echo "Error: HCI Event data not found in input"
        exit 1
    fi
    
    # Extract the status byte (4th byte in the event data)
    # Event data format: "02 36 20 0C 00" -> status is "0C"
    status_byte=$(echo "$data_line" | awk '{print $4}')
    
    # Check if status_byte is extracted
    if [[ -z "$status_byte" ]]; then
        echo "Error: Status byte not found"
        exit 1
    fi
    
    echo "Status Byte: $status_byte"
    
    if [[ "$status_byte" != "00" ]]; then
        echo "operation failed"
        exit 1
    fi

    echo "operation succeed"
}


## $1 - command and data
hcitool_cmd() {
    local data="$1"
    local output=$(sudo hcitool -i $IFACE cmd $data)   
    echo -e "output:\n${output}"
    check_event_status "${output}"
}


#########################################################


ascii_to_hex() {
    local input="$1"
    local output=$(echo -n "$input" | xxd -p | sed 's/../& /g')
    echo "${output::-1}"
}


get_data_length() {
    local data_length=$(echo "$1" | tr -cd ' ' | wc -c)
    local data_length=$((data_length + 1))
    echo "${data_length}"
}


add_length() {
    local data_length=$(get_data_length "$1")
    local data_length_hex=$(printf "0x%02x" "${data_length}")       ## dec to hex
    local data_string="${data_length_hex} $1"
    echo "${data_string}"
}


add_field_to_data() {
    local data="$1"
    local new_field=$(add_length "${2}")
    if [[ "${data}" == "" ]]; then
        ## empty string
        echo "${new_field}"
    else
        echo "${1} ${new_field}"
    fi
}


## remove spaces and "0x" prefixes
remove_hex_prefix() {
    local data="${1}"
    data="${data// /}"
    data="${data//0x/}"
    echo "${data}"
}
