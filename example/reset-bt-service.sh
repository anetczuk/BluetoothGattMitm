#!/bin/bash

set -eu


systemctl status bluetooth.service --no-pager

sudo systemctl restart bluetooth.service


# ##
# ## disable randomized MAC (privacy)
# ##
# echo "disabling privacy"
# sudo btmgmt --index 0 power off
# sudo btmgmt --index 0 privacy off
# sudo btmgmt --index 0 power on
