#!/usr/bin/env python3
from cereal import car, arne182
from selfdrive.swaglog import cloudlog
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.drive_helpers import EventTypes as ET, create_event
from selfdrive.car.ford.values import MAX_ANGLE, Ecu, ECU_FINGERPRINT, FINGERPRINTS
from selfdrive.car import STD_CARGO_KG, scale_rot_inertia, scale_tire_stiffness, is_ecu_disconnected, gen_empty_fingerprint
from selfdrive.car.interfaces import CarInterfaceBase


class CarInterface(CarInterfaceBase):

  @staticmethod
  def compute_gb(accel, speed):
    return float(accel) / 3.0

  @staticmethod
  def get_params(candidate, fingerprint=gen_empty_fingerprint(), has_relay=False, car_fw=[]):
    ret = CarInterfaceBase.get_std_params(candidate, fingerprint, has_relay)
    ret.carName = "ford"
    ret.safetyModel = car.CarParams.SafetyModel.ford
    ret.dashcamOnly = True

    ret.wheelbase = 2.85
    ret.steerRatio = 14.8
    ret.mass = 3045. * CV.LB_TO_KG + STD_CARGO_KG
    ret.lateralTuning.pid.kiBP, ret.lateralTuning.pid.kpBP = [[0.], [0.]]
    ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.01], [0.005]]     # TODO: tune this
    ret.lateralTuning.pid.kf = 1. / MAX_ANGLE   # MAX Steer angle to normalize FF
    ret.steerActuatorDelay = 0.1  # Default delay, not measured yet
    ret.steerLimitTimer = 0.8
    ret.steerRateCost = 1.0
    ret.centerToFront = ret.wheelbase * 0.44
    tire_stiffness_factor = 0.5328

    # TODO: get actual value, for now starting with reasonable value for
    # civic and scaling by mass and wheelbase
    ret.rotationalInertia = scale_rot_inertia(ret.mass, ret.wheelbase)

    # TODO: start from empirically derived lateral slip stiffness for the civic and scale by
    # mass and CG position, so all cars will have approximately similar dyn behaviors
    ret.tireStiffnessFront, ret.tireStiffnessRear = scale_tire_stiffness(ret.mass, ret.wheelbase, ret.centerToFront,
                                                                         tire_stiffness_factor=tire_stiffness_factor)

    ret.steerControlType = car.CarParams.SteerControlType.angle

    ret.enableCamera = is_ecu_disconnected(fingerprint[0], FINGERPRINTS, ECU_FINGERPRINT, candidate, Ecu.fwdCamera) or has_relay
    cloudlog.warning("ECU Camera Simulated: %r", ret.enableCamera)

    ret.stoppingControl = False
    ret.startAccel = 0.0

    ret.longitudinalTuning.deadzoneBP = [0., 9.]
    ret.longitudinalTuning.deadzoneV = [0., .15]
    ret.longitudinalTuning.kpBP = [0., 5., 35.]
    #ret.longitudinalTuning.kpV = [3.6, 2.4, 1.5]
    ret.longitudinalTuning.kiBP = [0., 35.]
    #ret.longitudinalTuning.kiV = [0.54, 0.36]
    ret.longitudinalTuning.kpV = [0.325, 0.325, 0.325]  # braking tune from rav4h
    ret.longitudinalTuning.kiV = [0.15, 0.10]

    return ret

  # returns a car.CarState
  def update(self, c, can_strings):
    # ******************* do can recv *******************
    self.cp.update_strings(can_strings)


    # create message
    ret = self.CS.update(self.cp)
    ret_arne182 = arne182.CarStateArne182.new_message()


    ret.canValid = self.cp.can_valid

    # events
    events = []
    eventsArne182 = []

    if self.CS.steer_error:
      events.append(create_event('steerUnavailable', [ET.NO_ENTRY, ET.IMMEDIATE_DISABLE, ET.PERMANENT]))

    # enable request in prius is simple, as we activate when Toyota is active (rising edge)
    if ret.cruiseState.enabled and not self.cruise_enabled_prev:
      events.append(create_event('pcmEnable', [ET.ENABLE]))
    elif not ret.cruiseState.enabled:
      events.append(create_event('pcmDisable', [ET.USER_DISABLE]))

    if self.CS.lkas_state not in [2, 3] and ret.vEgo > 13.* CV.MPH_TO_MS and ret.cruiseState.enabled:
      events.append(create_event('steerTempUnavailableMute', [ET.WARNING]))

    ret.events = events
    ret_arne182.events = eventsArne182

    self.gas_pressed_prev = ret.gasPressed
    self.brake_pressed_prev = ret.brakePressed
    self.cruise_enabled_prev = ret.cruiseState.enabled
    self.CS.out = ret.as_reader()

    return self.CS.out, ret_arne182.as_reader()

  # pass in a car.CarControl
  # to be called @ 100hz
  def apply(self, c):

    can_sends = self.CC.update(c.enabled, self.CS, self.frame, c.actuators,
                               c.hudControl.visualAlert, c.cruiseControl.cancel)

    self.frame += 1
    return can_sends
