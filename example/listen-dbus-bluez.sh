#!/bin/bash

set -eu


sudo dbus-monitor --system "destination='org.bluez'" "sender='org.bluez'"
