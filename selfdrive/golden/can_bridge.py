#!/usr/bin/env python3
import os
import time
import math
import atexit
import numpy as np
import threading
import random
import cereal.messaging as messaging
import argparse
from common.params import Params
from common.realtime import Ratekeeper
from selfdrive.golden.can import can_function, sendcan_function
import queue
import subprocess

import sys
import signal

def main():
  os.system('echo 1 > /tmp/op_simulation')
  os.system('echo 1 > /tmp/force_calibration')
  os.system('service call audio 3 i32 3 i32 0 i32 1')

  global pm

  pm = messaging.PubMaster(['can', 'health'])
  gps = messaging.sub_sock('gpsLocation')
  live_params = messaging.sub_sock('liveParameters')
  #live_calibartion = messaging.sub_sock('liveCalibration')

  # can loop
  sendcan = messaging.sub_sock('sendcan')
  rk = Ratekeeper(100, print_delay_threshold=None)
  steer_angle = 0.0

  gps_speed = 30.0 / 3.6
  cal_status = 0
  posenet_speed = 0.0
  btn_list = []

  while 1:
    gps_data = messaging.recv_sock(gps)
    params = messaging.recv_sock(live_params)
    calibration = None
    #calibration = messaging.recv_sock(live_calibartion)

    if gps_data:
      gps_speed = gps_data.gpsLocation.speed

    if params:
      posenet_speed = params.liveParameters.posenetSpeed
      #print ('posenet_speed=' + str(posenet_speed*3.6) + ' kph')

    if calibration:
      cal_status = calibration.liveCalibration.calStatus

    engage = False
    if rk.frame != 0 and rk.frame % 500 == 0:
      engage = cal_status == 1

    speed = gps_speed
    if speed < 0.00001:
      speed = posenet_speed
    #can_function(pm, speed, steer_angle, rk.frame, rk.frame%500 == 499)

    if os.path.exists('/tmp/op_start'):
      if len(btn_list) == 0:
        for x in range(10):
          btn_list.append(3)
        os.system('rm /tmp/op_start')

    if os.path.exists('/tmp/op_stop'):
      if len(btn_list) == 0:
        for x in range(10):
          btn_list.append(2)
      os.system('rm /tmp/op_stop')

    btn = 0
    if len(btn_list) > 0:
      btn = btn_list[0]
      btn_list.pop(0)

    can_function(pm, speed * 3.6, steer_angle, rk.frame, cruise_button=btn, is_engaged=1)
    #if rk.frame%5 == 0:
    #  throttle, brake, steer = sendcan_function(sendcan)
    #  steer_angle += steer/10000.0 # torque
    #  # print(speed * 3.6, steer, throttle, brake)

    dat = messaging.new_message('health')
    dat.valid = True
    dat.health = {
      'ignitionLine': True,
      'hwType': "blackPanda",
      'controlsAllowed': True
    }
    pm.send('health', dat)

    rk.keep_time()

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')

    global pm

    dat = messaging.new_message('health')
    dat.valid = True
    dat.health = {
      'ignitionLine': False,
      'hwType': "greyPanda",
      'controlsAllowed': True
    }

    for seq in range(10):
      pm.send('health', dat)
      time.sleep(0.1)

    print ("exiting")
    sys.exit(0)

if __name__ == "__main__":
  signal.signal(signal.SIGINT, signal_handler)
  main()

