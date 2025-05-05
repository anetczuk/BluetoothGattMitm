#!/bin/bash

set -eu


HELPER_PATH=$(find ~ -name bluepy-helper)


if [[ -z ${HELPER_PATH+x} ]] || [[ -z "${HELPER_PATH}" ]]; then
    echo "unable to find 'bluepy-helper'"
    exit 1
fi


sudo setcap cap_net_raw+e ${HELPER_PATH}
sudo setcap cap_net_admin+eip ${HELPER_PATH}


echo "completed"
