import json
import os

class kegman_conf():
  def __init__(self, CP=None):
    self.conf = self.read_config()
    if CP is not None:
      self.init_config(CP)

  def init_config(self, CP):
    write_conf = False
    if self.conf['tuneGernby'] != "1":
      self.conf['tuneGernby'] = str(1)
      write_conf = True
    if float(self.conf['reactMPC']) + float(self.conf['dampMPC']) < 0.0:
      self.conf['reactMPC'] = str(round(CP.steerMPCReactTime,3))
      self.conf['dampMPC'] = str(round(CP.steerMPCDampTime,3))
      write_conf = True
    if float(self.conf['reactSteer']) + float(self.conf['dampSteer']) < 0.0:
      self.conf['reactSteer'] = str(round(CP.steerReactTime,3))
      self.conf['dampSteer'] = str(round(CP.steerDampTime,3))
      write_conf = True
    if self.conf['delaySteer'] == "-1":
      self.conf['delaySteer'] = str(round(CP.steerActuatorDelay,3))
      write_conf = True
    if self.conf['longOffset'] == "-1":
      self.conf['longOffset'] = str(round(CP.longOffset,3))
      write_conf = True
    if self.conf['Kp'] == "-1":
      self.conf['Kp'] = str(round(CP.steerKpV[0],3))
      write_conf = True
    if self.conf['Ki'] == "-1":
      self.conf['Ki'] = str(round(CP.steerKiV[0],3))
      write_conf = True
    if self.conf['dampRate'] == "-1":
      self.conf['dampRate'] = str(round(CP.rateDampTime, 3))
      self.conf['reactRate'] = str(round(CP.rateReactTime, 3))
      write_conf = True
    if self.conf['backlash'] == "-1":
      self.conf['backlash'] = str(round(CP.steerBacklash,3))
      write_conf = True
    if self.conf['rateFF'] == "-1":
      self.conf['rateFF'] = str(round(CP.rateFFGain,3))
      write_conf = True
    if self.conf['longOffset'] == "-1":
      self.conf['longOffset'] = str(round(CP.longOffset,3))
      write_conf = True
    if self.conf['oscFactor'] == "-1":
      self.conf['oscFactor'] = str(round(CP.oscillationFactor, 2))
      write_conf = True

    if write_conf:
      self.write_config(self.config)

  def read_config(self):
    self.element_updated = False

    if os.path.isfile('/data/kegman.json'):
      with open('/data/kegman.json', 'r') as f:
        self.config = json.load(f)

      if "battPercOff" not in self.config:
        self.config.update({"battPercOff":"25"})
        self.config.update({"carVoltageMinEonShutdown":"11800"})
        self.config.update({"brakeStoppingTarget":"0.25"})
        self.element_updated = True

      if "tuneGernby" not in self.config:
        self.config.update({"tuneGernby":"1"})
        self.config.update({"Kp":"-1"})
        self.config.update({"Ki":"-1"})
        self.config.update({"dampMPC":"-1"})
        self.config.update({"reactMPC":"-1"})
        self.element_updated = True

      if "rateFF" not in self.config:
        self.config.update({"rateFF":"-1"})
        self.element_updated = True

      if "backlash" not in self.config:
        self.config.update({"backlash":"-1"})
        self.element_updated = True

      if "delaySteer" not in self.config:
        self.config.update({"delaySteer":"-1"})
        self.element_updated = True

      if "dampRate" not in self.config:
        self.config.update({"dampSteer":"-1"})
        self.config.update({"dampRate":"-1"})
        self.config.update({"reactRate":"-1"})
        self.config.update({"longOffset":"-1"})
        self.config.update({"delaySteer":"-1"})
        self.element_updated = True

      if "oscFactor" not in self.config:
        self.config.update({"oscFactor":"-1"})
        self.element_updated = True

      if "dampSteer" not in self.config:
        self.config.update({"dampSteer":"-1"})
        self.config.update({"reactSteer":"-1"})
        self.element_updated = True


      # Force update battery charge limits to higher values for Big Model
      #if self.config['battChargeMin'] != "75":
      #  self.config.update({"battChargeMin":"75"})
      #  self.config.update({"battChargeMax":"80"})
      #  self.element_updated = True

      if self.element_updated:
        print("updated")
        self.write_config(self.config)

    else:
      self.config = {"cameraOffset":"0.06", "lastTrMode":"1", "battChargeMin":"60", "battChargeMax":"70", \
                     "wheelTouchSeconds":"180", "battPercOff":"25", "carVoltageMinEonShutdown":"11800", \
                     "brakeStoppingTarget":"0.25", "tuneGernby":"1", "reactMPC":"-1", "reactSteer":"-1","reactRate":"-1", \
                     "dampMPC":"-1", "dampSteer":"-1", "dampRate":"-1", "Kp":"-1", "Ki":"-1", "rateFF":"-1", "delaySteer":"-1", \
                     "oscFactor":"-1", "backlash":"-1", "longOffset":"-1"}

      self.write_config(self.config)
    return self.config

  def write_config(self, config):
    with open('/data/kegman.json', 'w') as f:
      json.dump(self.config, f, indent=2, sort_keys=True)
      os.chmod("/data/kegman.json", 0o764)
