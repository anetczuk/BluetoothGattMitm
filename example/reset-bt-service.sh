#!/bin/bash

set -eu


systemctl status bluetooth.service

sudo systemctl restart bluetooth.service
