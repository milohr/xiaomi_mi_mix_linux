#!/bin/sh
# Xiaomi Mi MIX (lithium). Input names as reported by evdev/xinput on the device.
export SXMO_POWER_BUTTON="0:0:pm8941_pwrkey"
export SXMO_VOLUME_BUTTON="1:1:gpio-keys 0:0:pm8941_resin"
export SXMO_TOUCHSCREEN_ID="generic ft5x06 (3b)"
export SXMO_SWAY_SCALE="2.5"
# No modem support in this port yet.
export SXMO_NO_MODEM=1
