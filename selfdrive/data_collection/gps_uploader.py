import os
import json
import gzip
import ftplib
import string
import random
import datetime
from common.params import Params
from common.op_params import opParams
op_params = opParams()
uniqueID = op_params.get('uniqueID')

def upload_data():
  filepath = "/data/openpilot/selfdrive/data_collection/gps-data"
  if os.path.isfile(filepath):
    if uniqueID is None:
      op_params.put('uniqueID', ''.join([random.choice(string.ascii_lowercase+string.ascii_uppercase+string.digits) for i in range(15)]))
    try:
      username = op_params.get('uniqueID')
      try:
        with open("/data/data/ai.comma.plus.offroad/files/persistStore/persist-auth", "r") as f:
          auth = json.loads(f.read())
        auth = json.loads(auth['commaUser'])
        if auth and str(auth['username']) != "":
          username = str(auth['username'])
      except Exception:
        pass

      params = Params()
      car = params.get('CachedFingerprint')
      if car is not None:
        car = json.loads(car)
        username+="-{}".format(car[0])

      filename = "gps-data.{}".format(random.randint(1,99999))
      fp = open(filepath,"rb")
      data = fp.read()
      bindata = bytearray(data)
      with gzip.open("/data/" + filename + ".gz", "wb") as f:
        f.write(bindata)
      ftp = ftplib.FTP("arneschwarck.dyndns.org")
      ftp.login("openpilot", "communitypilot")
      with open("/data/" + filename + ".gz", "rb") as f:
        try:
          ftp.mkd("/{}".format(username))
        except Exception:
          pass
        ftp.storbinary("STOR /{}/{}".format(username, filename + ".gz"), f)
      ftp.quit()
      os.remove(filepath)
      os.remove("/data/" + filename + ".gz")
      t = datetime.datetime.utcnow().isoformat()
      params.put("LastUpdateTime", t.encode('utf8'))
      return True
    except Exception:
      return False
  else:
    return False
