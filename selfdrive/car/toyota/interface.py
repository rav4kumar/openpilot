#!/usr/bin/env python3
from cereal import car
from selfdrive.config import Conversions as CV
from selfdrive.car.toyota.values import Ecu, ECU_FINGERPRINT, CAR, TSS2_CAR, NO_DSU_CAR, FINGERPRINTS, CarControllerParams
from selfdrive.car import STD_CARGO_KG, scale_rot_inertia, scale_tire_stiffness, is_ecu_disconnected, gen_empty_fingerprint
from selfdrive.swaglog import cloudlog
from selfdrive.car.interfaces import CarInterfaceBase
from common.op_params import opParams

GearShifter = car.CarState.GearShifter

EventName = car.CarEvent.EventName

op_params = opParams()
prius_pid = op_params.get('prius_pid')
cruise_speed_override_enabled = op_params.get('cruise_speed_override_enabled')
cruise_speed_override = op_params.get('cruise_speed_override')

class CarInterface(CarInterfaceBase):
  def __init__(self, CP, CarController, CarState):
    super().__init__(CP, CarController, CarState)
    self.init_cruise_speed = 0.

  @staticmethod
  def compute_gb(accel, speed):
    return float(accel) / CarControllerParams.ACCEL_SCALE

  @staticmethod
  def get_params(candidate, fingerprint=gen_empty_fingerprint(), car_fw=[]):  # pylint: disable=dangerous-default-value
    ret = CarInterfaceBase.get_std_params(candidate, fingerprint)

    ret.carName = "toyota"
    ret.safetyModel = car.CarParams.SafetyModel.toyota

    ret.steerActuatorDelay = 0.12  # Default delay, Prius has larger delay
    ret.steerLimitTimer = 0.4

    # Improved longitudinal tune
    if candidate in [CAR.COROLLA_TSS2, CAR.COROLLAH_TSS2, CAR.RAV4_TSS2, CAR.RAV4H_TSS2, CAR.PRIUS_TSS2]:
      ret.longitudinalTuning.deadzoneBP = [0., 8.05]
      ret.longitudinalTuning.deadzoneV = [.0, .14]
      ret.longitudinalTuning.kpBP = [0., 5., 20.]
      ret.longitudinalTuning.kpV = [1.3, 1.0, 0.7]
      ret.longitudinalTuning.kiBP = [0., 5., 12., 20., 27.]
      ret.longitudinalTuning.kiV = [.35, .23, .20, .17, .1]
      ret.stoppingBrakeRate = 0.1 # reach stopping target smoothly
      ret.startingBrakeRate = 2.0 # release brakes fast
      ret.startAccel = 1.2 # Accelerate from 0 faster
    else:
      # Default longitudinal tune
      ret.longitudinalTuning.deadzoneBP = [0., 9.]
      ret.longitudinalTuning.deadzoneV = [0., .15]
      #ret.longitudinalTuning.kpBP = [0., 5., 35.]
      ret.longitudinalTuning.kiBP = [0., 35.]
      #ret.longitudinalTuning.kpV = [3.6, 2.4, 1.5]
      ret.longitudinalTuning.kiV = [0.54, 0.36]
      ret.longitudinalTuning.kpV = [0.35, 0.2, 0.05]  # braking tune from rav4h
      ret.longitudinalTuning.kiV = [0.15, 0.010]

    if candidate not in [CAR.PRIUS, CAR.RAV4, CAR.RAV4H]:  # These cars use LQR/INDI
      ret.lateralTuning.init('pid')
      ret.lateralTuning.pid.kiBP, ret.lateralTuning.pid.kpBP = [[0.], [0.]]

    if candidate == CAR.PRIUS:
      stop_and_go = True
      ret.safetyParam = 66  # see conversion factor for STEER_TORQUE_EPS in dbc file
      ret.wheelbase = 2.70
      ret.steerRatio = 15.74   # unknown end-to-end spec
      tire_stiffness_factor = 0.6371   # hand-tune
      ret.mass = 3045. * CV.LB_TO_KG + STD_CARGO_KG

      ret.lateralTuning.init('indi')
      ret.lateralTuning.indi.innerLoopGainBP = [0.]
      ret.lateralTuning.indi.innerLoopGainV = [4.0]
      ret.lateralTuning.indi.outerLoopGainBP = [0.]
      ret.lateralTuning.indi.outerLoopGainV = [3.0]
      ret.lateralTuning.indi.timeConstantBP = [0.]
      ret.lateralTuning.indi.timeConstantV = [1.0]
      ret.lateralTuning.indi.actuatorEffectivenessBP = [0.]
      ret.lateralTuning.indi.actuatorEffectivenessV = [1.0]
      ret.steerActuatorDelay = 0.3

    elif candidate == CAR.PRIUS_TSS2:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.70002  # from toyota online sepc.
      ret.steerRatio = 13.4   # True steerRation from older prius
      tire_stiffness_factor = 0.6371   # hand-tune
      ret.mass = 3115. * CV.LB_TO_KG + STD_CARGO_KG
      if prius_pid:
        ret.steerActuatorDelay = 0.05
        #ret.steerLimitTimer = 0.5
        ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.18], [0.015]]  # community tuning
        ret.lateralTuning.pid.kf = 0.00012  # community tuning
      else:
        ret.steerActuatorDelay = 0
        ret.steerLimitTimer = 5
        ret.lateralTuning.init('indi')
        ret.lateralTuning.indi.innerLoopGainBP = [5.5, 8.3, 11.1, 13.9, 16.7, 19.4, 22.2, 25]
        ret.lateralTuning.indi.innerLoopGainV = [4.2, 5.8, 7.55, 9.3, 11.1, 12.9, 14.7, 15]
        ret.lateralTuning.indi.outerLoopGainBP = [5.5, 8.3, 11.1, 13.9, 16.7, 19.4, 22.2, 25]
        ret.lateralTuning.indi.outerLoopGainV = [3.05, 4.66, 6.32, 8.12, 9.87, 11.72, 13.62, 14.99]
        ret.lateralTuning.indi.timeConstantBP = [5.5, 8.3, 11.1, 13.9, 16.7, 19.4, 22.2, 30.09, 30.1, 33.32, 33.33]
        ret.lateralTuning.indi.timeConstantV = [0.31, 0.46, 0.62, 0.84, 0.97, 1.2, 3.0, 3.0, 6.5, 6.5, 8.0]
        ret.lateralTuning.indi.actuatorEffectivenessBP = [5.5, 8.3, 11.1, 13.9, 16.7, 19.4, 22.2, 25]
        ret.lateralTuning.indi.actuatorEffectivenessV = [4.2, 5.8, 7.55, 9.3, 11.1, 12.9, 14.7, 15]

    elif candidate in [CAR.RAV4, CAR.RAV4H]:
      stop_and_go = True if (candidate in CAR.RAV4H) else False
      ret.safetyParam = 73
      ret.wheelbase = 2.65
      ret.steerRatio = 16.88   # 14.5 is spec end-to-end
      tire_stiffness_factor = 0.5533
      ret.mass = 3650. * CV.LB_TO_KG + STD_CARGO_KG  # mean between normal and hybrid
      ret.lateralTuning.init('lqr')

      ret.lateralTuning.lqr.scale = 1500.0
      ret.lateralTuning.lqr.ki = 0.05

      ret.lateralTuning.lqr.a = [0., 1., -0.22619643, 1.21822268]
      ret.lateralTuning.lqr.b = [-1.92006585e-04, 3.95603032e-05]
      ret.lateralTuning.lqr.c = [1., 0.]
      ret.lateralTuning.lqr.k = [-110.73572306, 451.22718255]
      ret.lateralTuning.lqr.l = [0.3233671, 0.3185757]
      ret.lateralTuning.lqr.dcGain = 0.002237852961363602

    elif candidate == CAR.COROLLA:
      stop_and_go = False
      ret.safetyParam = 88
      ret.wheelbase = 2.70
      ret.steerRatio = 18.27
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 2860. * CV.LB_TO_KG + STD_CARGO_KG  # mean between normal and hybrid
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.2], [0.05]]
      ret.lateralTuning.pid.kf = 0.00003   # full torque for 20 deg at 80mph means 0.00007818594

    elif candidate == CAR.LEXUS_RX:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.79
      ret.steerRatio = 14.8
      tire_stiffness_factor = 0.5533
      ret.mass = 4387. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.05]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate == CAR.LEXUS_RXH:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.79
      ret.steerRatio = 16.  # 14.8 is spec end-to-end
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 4481. * CV.LB_TO_KG + STD_CARGO_KG  # mean between min and max
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00006   # full torque for 10 deg at 80mph means 0.00007818594

    elif candidate == CAR.LEXUS_RX_TSS2:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.79
      ret.steerRatio = 14.8
      tire_stiffness_factor = 0.5533  # not optimized yet
      ret.mass = 4387. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate == CAR.LEXUS_RXH_TSS2:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.79
      ret.steerRatio = 16.0  # 14.8 is spec end-to-end
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 4481.0 * CV.LB_TO_KG + STD_CARGO_KG  # mean between min and max
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.15]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate in [CAR.CHR, CAR.CHRH]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.63906
      ret.steerRatio = 13.6
      tire_stiffness_factor = 0.7933
      ret.mass = 3300. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.723], [0.0428]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate in [CAR.CAMRY, CAR.CAMRYH, CAR.CAMRY_TSS2, CAR.CAMRYH_TSS2]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.82448
      ret.steerRatio = 13.7
      tire_stiffness_factor = 0.7933
      ret.mass = 3400. * CV.LB_TO_KG + STD_CARGO_KG  # mean between normal and hybrid
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate in [CAR.HIGHLANDER_TSS2, CAR.HIGHLANDERH_TSS2]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.84988  # 112.2 in = 2.84988 m
      ret.steerRatio = 16.0
      tire_stiffness_factor = 0.8
      ret.mass = 4700. * CV.LB_TO_KG + STD_CARGO_KG  # 4260 + 4-5 people
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.18], [0.015]]  # community tuning
      ret.lateralTuning.pid.kf = 0.00012  # community tuning

    elif candidate in [CAR.HIGHLANDER, CAR.HIGHLANDERH]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.78
      ret.steerRatio = 16.0
      tire_stiffness_factor = 0.8
      ret.mass = 4607. * CV.LB_TO_KG + STD_CARGO_KG  # mean between normal and hybrid limited
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.18], [0.015]]  # community tuning
      ret.lateralTuning.pid.kf = 0.00012  # community tuning

    elif candidate == CAR.AVALON:
      stop_and_go = False
      ret.safetyParam = 73
      ret.wheelbase = 2.82
      ret.steerRatio = 14.8  # Found at https://pressroom.toyota.com/releases/2016+avalon+product+specs.download
      tire_stiffness_factor = 0.7983
      ret.mass = 3505. * CV.LB_TO_KG + STD_CARGO_KG  # mean between normal and hybrid
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.17], [0.03]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate == CAR.RAV4_TSS2:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.68986
      ret.steerRatio = 14.3
      tire_stiffness_factor = 0.7933
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.15], [0.05]]
      ret.mass = 3370. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kf = 0.00004

      for fw in car_fw:
        if fw.ecu == "eps" and fw.fwVersion == b"8965B42170\x00\x00\x00\x00\x00\x00":
          ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
          ret.lateralTuning.pid.kf = 0.00007818594
          break

    elif candidate == CAR.RAV4H_TSS2:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.68986
      ret.steerRatio = 14.3
      tire_stiffness_factor = 0.7933
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.15], [0.05]]
      ret.mass = 3800. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kf = 0.00004

      for fw in car_fw:
        if fw.ecu == "eps" and fw.fwVersion == b"8965B42170\x00\x00\x00\x00\x00\x00":
          ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
          ret.lateralTuning.pid.kf = 0.00007818594
          break

    elif candidate in [CAR.COROLLA_TSS2, CAR.COROLLAH_TSS2]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.67  # Average between 2.70 for sedan and 2.64 for hatchback
      ret.steerRatio = 13.9
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 3060. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate in [CAR.LEXUS_ES_TSS2, CAR.LEXUS_ESH_TSS2]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.8702
      ret.steerRatio = 16.0  # not optimized
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 3704. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate == CAR.LEXUS_ESH:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.8190
      ret.steerRatio = 16.06
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 3682. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate == CAR.SIENNA:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 3.03
      ret.steerRatio = 15.5
      tire_stiffness_factor = 0.444
      ret.mass = 4590. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.19], [0.02]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate == CAR.LEXUS_IS:
      stop_and_go = False
      ret.safetyParam = 77
      ret.wheelbase = 2.79908
      ret.steerRatio = 13.3
      tire_stiffness_factor = 0.444
      ret.mass = 3736.8 * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.3], [0.05]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate == CAR.LEXUS_CTH:
      stop_and_go = True
      ret.safetyParam = 100
      ret.wheelbase = 2.60
      ret.steerRatio = 18.6
      tire_stiffness_factor = 0.517
      ret.mass = 3108 * CV.LB_TO_KG + STD_CARGO_KG  # mean between min and max
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.3], [0.05]]
      ret.lateralTuning.pid.kf = 0.00007

    elif candidate in [CAR.LEXUS_NXH, CAR.LEXUS_NX]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.66
      ret.steerRatio = 14.7
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 4070 * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00006

    ret.steerRateCost = 1.
    ret.centerToFront = ret.wheelbase * 0.44

    # TODO: get actual value, for now starting with reasonable value for
    # civic and scaling by mass and wheelbase
    ret.rotationalInertia = scale_rot_inertia(ret.mass, ret.wheelbase)

    # TODO: start from empirically derived lateral slip stiffness for the civic and scale by
    # mass and CG position, so all cars will have approximately similar dyn behaviors
    ret.tireStiffnessFront, ret.tireStiffnessRear = scale_tire_stiffness(ret.mass, ret.wheelbase, ret.centerToFront,
                                                                         tire_stiffness_factor=tire_stiffness_factor)

    ret.enableCamera = True
    # Detect smartDSU, which intercepts ACC_CMD from the DSU allowing openpilot to send it
    smartDsu = 0x2FF in fingerprint[0]
    # TODO: use FW query for the enableDsu flag
    # In TSS2 cars the camera does long control
    ret.enableDsu = is_ecu_disconnected(fingerprint[0], FINGERPRINTS, ECU_FINGERPRINT, candidate, Ecu.dsu) and candidate not in NO_DSU_CAR
    ret.enableGasInterceptor = 0x201 in fingerprint[0]
    # if the smartDSU is detected, openpilot can send ACC_CMD (and the smartDSU will block it from the DSU) or not (the DSU is "connected")
    ret.openpilotLongitudinalControl = ret.enableCamera and (smartDsu or ret.enableDsu or candidate in TSS2_CAR)
    cloudlog.warning("ECU Camera Simulated: %r", ret.enableCamera)
    cloudlog.warning("ECU DSU Simulated: %r", ret.enableDsu)
    cloudlog.warning("ECU Gas Interceptor: %r", ret.enableGasInterceptor)

    # min speed to enable ACC. if car can do stop and go, then set enabling speed
    # to a negative value, so it won't matter.
    ret.minEnableSpeed = -1. if (stop_and_go or ret.enableGasInterceptor) else 19. * CV.MPH_TO_MS

    # removing the DSU disables AEB and it's considered a community maintained feature
    # intercepting the DSU is a community feature since it requires unofficial hardware
    ret.communityFeature = ret.enableGasInterceptor or ret.enableDsu or smartDsu

    if ret.enableGasInterceptor:
      ret.gasMaxBP = [0., 9., 35]
      ret.gasMaxV = [0.2, 0.5, 0.7]
    else:
      ret.gasMaxBP = [0., 9., 55]
      ret.gasMaxV = [0.2, 0.5, 0.7]

    return ret

  # returns a car.CarState
  def update(self, c, can_strings):
    # ******************* do can recv *******************
    self.cp.update_strings(can_strings)
    self.cp_cam.update_strings(can_strings)

    self.cruise_speed_override = cruise_speed_override #TODO: add it to the op_edit or better yet setting.

    ret = self.CS.update(self.cp, self.cp_cam)
    if cruise_speed_override_enabled:
      if ret.cruiseState.enabled and ret.cruiseState.speed < 12 and self.CP.openpilotLongitudinalControl:
        if self.cruise_speed_override:
          if self.init_cruise_speed == 0.:
            ret.cruiseState.speed = self.init_cruise_speed = max(2, ret.vEgo)
          else:
            ret.cruiseState.speed = self.init_cruise_speed
        else:
          ret.cruiseState.speed = 2
      else:
        self.init_cruise_speed = 0.

    ret.canValid = self.cp.can_valid and self.cp_cam.can_valid
    ret.steeringRateLimited = self.CC.steer_rate_limited if self.CC is not None else False

    # gear except P, R
    extra_gears = [GearShifter.neutral, GearShifter.eco, GearShifter.manumatic, GearShifter.drive, GearShifter.sport, GearShifter.low, GearShifter.brake, GearShifter.unknown]

    longControlDisabled = False
    if not self.CS.out.cruiseState.enabled:
      ret.cruiseState.enabled = self.CS.pcm_acc_active
    else:
      if self.keep_openpilot_engaged:
        ret.cruiseState.enabled = bool(self.CS.main_on)
      if not self.CS.pcm_acc_active:
        longControlDisabled = True
        ret.brakePressed = True
        self.disengage_due_to_slow_speed = False
    if ret.vEgo < 1 or not self.keep_openpilot_engaged:
      ret.cruiseState.enabled = self.CS.pcm_acc_active
      if self.CS.out.cruiseState.enabled and not self.CS.pcm_acc_active:
        self.disengage_due_to_slow_speed = True
    if self.disengage_due_to_slow_speed and ret.vEgo > 1 and ret.gearShifter != GearShifter.reverse:
      self.disengage_due_to_slow_speed = False
      ret.cruiseState.enabled = bool(self.CS.main_on)

    # events
    events = self.create_common_events(ret, extra_gears)

    #alwaysonkumar
    if longControlDisabled:
      events.add(EventName.longControlDisabled)

    if self.CS.low_speed_lockout and self.CP.openpilotLongitudinalControl:
      events.add(EventName.lowSpeedLockout)
    if ret.vEgo < self.CP.minEnableSpeed and self.CP.openpilotLongitudinalControl:
      events.add(EventName.belowEngageSpeed)
      if c.actuators.gas > 0.1:
        # some margin on the actuator to not false trigger cancellation while stopping
        events.add(EventName.speedTooLow)
      if ret.vEgo < 0.001:
        # while in standstill, send a user alert
        events.add(EventName.manualRestart)

    ret.events = events.to_msg()

    self.CS.out = ret.as_reader()
    return self.CS.out

  # pass in a car.CarControl
  # to be called @ 100hz
  def apply(self, c):

    can_sends = self.CC.update(c.enabled, self.CS, self.frame,
                               c.actuators, c.cruiseControl.cancel,
                               c.hudControl.visualAlert, c.hudControl.leftLaneVisible,
                               c.hudControl.rightLaneVisible, c.hudControl.leadVisible,
                               c.hudControl.leftLaneDepart, c.hudControl.rightLaneDepart)

    self.frame += 1
    return can_sends
