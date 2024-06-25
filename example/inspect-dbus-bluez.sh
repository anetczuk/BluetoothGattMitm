#!/bin/bash

set -eu


gdbus introspect -y -d "org.bluez" -o "/org/bluez/hci0"
