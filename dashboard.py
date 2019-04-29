#!/usr/bin/env python
import zmq
import time
import os
import json
import selfdrive.messaging as messaging
from selfdrive.services import service_list
from common.params import Params

def dashboard_thread(rate=100):

  kegman_valid = True

  #url_string = 'http://192.168.1.61:8086/write?db=carDB'
  #url_string = 'http://192.168.43.221:8086/write?db=carDB'
  #url_string = 'http://192.168.137.1:8086/write?db=carDB'
  #url_string = 'http://kevo.live:8086/write?db=carDB'

  context = zmq.Context()
  poller = zmq.Poller()
  ipaddress = "127.0.0.1"
  vEgo = 0.0
  live100 = messaging.sub_sock(context, service_list['live100'].port, addr=ipaddress, conflate=False, poller=poller)

  _live100 = None

  frame_count = 0

  #server_address = "tcp://kevo.live"
  server_address = "tcp://gernstation.synology.me"

  context = zmq.Context()
  steerPush = context.socket(zmq.PUSH)
  steerPush.connect(server_address + ":8594")
  tunePush = context.socket(zmq.PUSH)
  tunePush.connect(server_address + ":8595")
  tuneSub = context.socket(zmq.SUB)
  tuneSub.connect(server_address + ":8596")
  poller.register(tuneSub, zmq.POLLIN)

  try:
    if os.path.isfile('/data/kegman.json'):
      with open('/data/kegman.json', 'r') as f:
        config = json.load(f)
        user_id = config['userID']
        tunePush.send_json(config)
        tunePush = None
    else:
        params = Params()
        user_id = params.get("DongleId")
  except:
    params = Params()
    user_id = params.get("DongleId")
    config['userID'] = user_id
    tunePush.send_json(config)
    tunePush = None

  tuneSub.setsockopt_string(zmq.SUBSCRIBE, user_id)
  influxFormatString = user_id + ",sources=capnp apply_steer=;noise_feedback=;ff_standard=;ff_rate=;ff_angle=;angle_steers_des=;angle_steers=;dampened_angle_steers_des=;steer_override=;v_ego=;p=;i=;f=;cumLagMs=; "
  kegmanFormatString = user_id + ",sources=kegman dampMPC=;reactMPC=;dampSteer=;reactSteer=;KpV=;KiV=;rateFF=;angleFF=;delaySteer=;oscFactor=;oscPeriod=; "
  influxDataString = ""
  kegmanDataString = ""

  monoTimeOffset = 0
  receiveTime = 0

  while 1:
    for socket, event in poller.poll(0):
      if socket is tuneSub:
        config = json.loads(tuneSub.recv_multipart()[1])
        print(config)
        with open('/data/kegman.json', 'w') as f:
          json.dump(config, f, indent=2, sort_keys=True)
          os.chmod("/data/kegman.json", 0o764)

      if socket is live100:
        _live100 = messaging.drain_sock(socket)
        for l100 in _live100:
          vEgo = l100.live100.vEgo
          receiveTime = int((monoTimeOffset + l100.logMonoTime) * .0000002) * 5
          if (abs(receiveTime - int(time.time() * 1000)) > 10000):
            monoTimeOffset = (time.time() * 1000000000) - l100.logMonoTime
            receiveTime = int((monoTimeOffset + l100.logMonoTime) * 0.0000002) * 5
          if vEgo > 0:

            influxDataString += ("%d,%0.2f,%0.2f,%0.3f,%0.3f,%0.2f,%0.2f,%0.2f,%d,%0.1f,%0.4f,%0.4f,%0.4f,%0.2f,%d|" %
                (l100.live100.steeringRequested, l100.live100.noiseFeedback, l100.live100.standardFFRatio, 1.0 - l100.live100.angleFFRatio,
                l100.live100.angleFFRatio, l100.live100.angleSteersDes, l100.live100.angleSteers, l100.live100.dampAngleSteersDes,
                l100.live100.steerOverride, vEgo, l100.live100.upSteer, l100.live100.uiSteer, l100.live100.ufSteer, l100.live100.cumLagMs, receiveTime))

            frame_count += 1

    if frame_count >= 100:
      if kegman_valid:
        try:
          if os.path.isfile('/data/kegman.json'):
            with open('/data/kegman.json', 'r') as f:
              config = json.load(f)
              reactMPC = config['reactMPC']
              dampMPC = config['dampMPC']
              reactSteer = config['reactSteer']
              dampSteer = config['dampSteer']
              delaySteer = config['delaySteer']
              steerKpV = config['Kp']
              steerKiV = config['Ki']
              rateFF = config['rateFF']
              oscFactor = config['oscFactor']
              oscPeriod = config['oscPeriod']
              kegmanDataString += ("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s|" % \
                    (dampMPC, reactMPC, dampSteer, reactSteer, steerKpV, steerKiV, rateFF, l100.live100.angleFFGain, delaySteer,
                    oscFactor, oscPeriod, receiveTime))
              insertString = kegmanFormatString + "~" + kegmanDataString + "!"
        except:
          kegman_valid = False

      insertString = insertString + influxFormatString + "~" + influxDataString

      steerPush.send_string(insertString)
      print(len(insertString))
      frame_count = 0
      influxDataString = ""
      kegmanDataString = ""
      insertString = ""
    else:
      time.sleep(0.1)

def main(rate=200):
  dashboard_thread(rate)

if __name__ == "__main__":
  main()
