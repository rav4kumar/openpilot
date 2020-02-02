#!/usr/bin/env python3
import os
import psutil
import signal
import subprocess
import sys
import time
from panda import Panda

serials = Panda.list()
num_pandas = len(serials)

if serials:
  # If panda is found, kill boardd, if boardd is flapping, and UsbPowerMode is CDP when shutdown,
  # device has a possibility of rebooting. Also, we need control of USB so we can force UsbPowerMode to client.
  for proc in psutil.process_iter():
    if proc.name() == 'boardd':
      os.kill(proc.pid, signal.SIGKILL)
      time.sleep(1)
      break
  # set usb power to client
  for serial in serials:
    panda = Panda(serial)
    panda.set_usb_power(1)
# execute system shutdown
os.system('LD_LIBRARY_PATH="" svc power shutdown')
