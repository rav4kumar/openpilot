#!/usr/bin/bash

if [ $1 -eq 1 ]; then
  printf %s "1" > /data/params/d/dp_jetson
  printf %s "0" > /data/params/d/dp_uploader
  printf %s "0" > /data/params/d/dp_logger
  printf %s "0" > /data/params/d/dp_athenad

fi
if [ $1 -eq 0 ]; then
  printf %s "0" > /data/params/d/dp_jetson
  cd /data/openpilot || exit
  git reset --hard @{u}
  git clean -xdf
fi
reboot
