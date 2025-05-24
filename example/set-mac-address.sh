#!/bin/bash

set -eux


hcitool dev 

sudo hciconfig hci0 down

sudo bdaddr -i hci0 DC:23:4F:DD:48:3E

sudo hciconfig hci0 up

hcitool dev
