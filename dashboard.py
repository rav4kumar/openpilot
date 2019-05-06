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
  liveMap = messaging.sub_sock(context, service_list['liveMapData'].port, addr=ipaddress, conflate=False, poller=poller)
  liveStreamData = messaging.sub_sock(context, 8600, addr=ipaddress, conflate=False, poller=poller)
  #gpsNMEA = messaging.sub_sock(context, service_list['gpsNMEA'].port, addr=ipaddress, conflate=True)

  #_live100 = None

  frame_count = 0

  #server_address = "tcp://kevo.live"
  server_address = "tcp://gernstation.synology.me"
  #server_address = "tcp://192.168.1.2"

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

  tuneSub.setsockopt(zmq.SUBSCRIBE, str(user_id))
  influxFormatString = user_id + ",sources=capnp apply_steer=;noise_feedback=;ff_standard=;ff_rate=;ff_angle=;angle_steers_des=;angle_steers=;dampened_angle_steers_des=;steer_override=;v_ego=;p=;i=;f=;cumLagMs=; "
  kegmanFormatString = user_id + ",sources=kegman dampMPC=;reactMPC=;dampSteer=;reactSteer=;KpV=;KiV=;rateFF=;angleFF=;delaySteer=;oscFactor=;oscPeriod=; "
  mapFormatString = "location,user=" + user_id + " latitude=;longitude=;altitude=;speed=;bearing=;accuracy=;speedLimitValid=;speedLimit=;curvatureValid=;curvature=;wayId=;distToTurn=;mapValid=;speedAdvisoryValid=;speedAdvisory=;speedAdvisoryValid=;speedAdvisory=;speedLimitAheadValid=;speedLimitAhead=;speedLimitAheadDistance=; "
  gpsFormatString="gps,user=" + user_id + " "
  liveStreamFormatString = "curvature,user=" + user_id + " l_curv=;p_curv=;r_curv=;map_curv=;map_rcurv=;map_rcurvx=;v_curv=;l_diverge=;r_diverge=; "
  influxDataString = ""
  kegmanDataString = ""
  liveStreamDataString = ""
  mapDataString = ""
  insertString = ""

  lastGPStime = 0
  lastMaptime = 0

  monoTimeOffset = 0
  receiveTime = 0

  while 1:
    for socket, event in poller.poll(0):
      if socket is tuneSub:
        config = json.loads(tuneSub.recv_multipart()[1])
        #print(config)
        with open('/data/kegman.json', 'w') as f:
          json.dump(config, f, indent=2, sort_keys=True)
          os.chmod("/data/kegman.json", 0o764)

      if socket is liveStreamData:
        livestream = liveStreamData.recv_string() + str(receiveTime) + "|"
        if vEgo > 0: liveStreamDataString += livestream

      if socket is liveMap:
        _liveMap = messaging.drain_sock(socket)
        for lmap in _liveMap:
          if vEgo > 0:
            receiveTime = int((monoTimeOffset + lmap.logMonoTime) * .0000002) * 5
            if (abs(receiveTime - int(time.time() * 1000)) > 10000):
              monoTimeOffset = (time.time() * 1000000000) - lmap.logMonoTime
              receiveTime = int((monoTimeOffset + lmap.logMonoTime) * 0.0000002) * 5
            lm = lmap.liveMapData
            lg = lm.lastGps
            #print(lm)
            mapDataString += ("%f,%f,%f,%f,%f,%f,%d,%f,%d,%f,%f,%f,%d,%d,%f,%d,%f,%d,%f,%f,%d|" %
                  (lg.latitude ,lg.longitude ,lg.altitude ,lg.speed ,lg.bearing ,lg.accuracy ,lm.speedLimitValid ,lm.speedLimit ,lm.curvatureValid
                  ,lm.curvature ,lm.wayId ,lm.distToTurn ,lm.mapValid ,lm.speedAdvisoryValid ,lm.speedAdvisory ,lm.speedAdvisoryValid ,lm.speedAdvisory
                  ,lm.speedLimitAheadValid ,lm.speedLimitAhead , lm.speedLimitAheadDistance , receiveTime))

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

    #if lastGPStime + 2.0 <= time.time():
    #  lastGPStime = time.time()
    #  _gps = messaging.recv_one_or_none(gpsNMEA)
    #  print(_gps)
    #if lastMaptime + 2.0 <= time.time():
    #  lastMaptime = time.time()
    #  _map = messaging.recv_one_or_none(liveMap)

    '''liveMapData = (
    speedLimitValid = false,
    speedLimit = 0,
    curvatureValid = false,
    curvature = 0,
    wayId = 0,
    lastGps = (
      flags = 0,
      latitude = 44.7195573,
      longitude = -100.8218663,
      altitude = 10542.853000000001,
      speed = 0,
      bearing = 0,
      accuracy = 4294967.5,
      timestamp = 1556581592999,
      source = ublox,
      vNED = [0, 0, 0],
      verticalAccuracy = 3750000.2,
      bearingAccuracy = 180,
      speedAccuracy = 20.001 ),
    distToTurn = 0,
    mapValid = false,
    speedAdvisoryValid = false,
    speedAdvisory = 0,
    speedLimitAheadValid = false,
    speedLimitAhead = 0,
    speedLimitAheadDistance = 0 ) )
    '''
    #else:
    #  print(time.time())

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
              backlash = config['backlash']
              kegmanDataString += ("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s|" % \
                    (backlash, dampMPC, reactMPC, dampSteer, reactSteer, steerKpV, steerKiV, rateFF, l100.live100.angleFFGain, delaySteer,
                    oscFactor, oscPeriod, receiveTime))
              insertString = kegmanFormatString + "~" + kegmanDataString + "!"
        except:
          kegman_valid = False

      if liveStreamDataString != "":
        insertString = insertString + liveStreamFormatString + "~" + liveStreamDataString + "!"
        #print(insertString)
        liveStreamDataString =""
      insertString = insertString + influxFormatString + "~" + influxDataString + "!"
      insertString = insertString + mapFormatString + "~" + mapDataString
      steerPush.send_string(insertString)
      print(len(insertString))
      frame_count = 0
      influxDataString = ""
      kegmanDataString = ""
      mapDataString = ""
      insertString = ""
    else:
      time.sleep(0.01)

def main(rate=200):
  dashboard_thread(rate)

if __name__ == "__main__":
  main()
