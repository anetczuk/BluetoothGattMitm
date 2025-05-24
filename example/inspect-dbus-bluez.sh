#!/bin/bash

set -eu


gdbus introspect -y -d "org.bluez" -o "/org/bluez/hci0"

#gdbus introspect --system --dest org.bluez --object-path /org/bluez --recurse
