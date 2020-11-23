#!/usr/bin/env python3
import datetime
from common.params import Params
from selfdrive.data_collection import gps_uploader

print("Don't forget to pray!")

params = Params()
t = datetime.datetime.utcnow().isoformat()
params.put("LastUpdateTime", t.encode('utf8'))

if params.get("IsOffroad") == b"1":
  print("Please wait for gps to upload to aviod this in future!")
  gps_uploader.upload_data()
else:
  print("Please switch off car and try again!")
  
