#!/usr/bin/env python3
from cereal import car, arne182, log
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.drive_helpers import EventTypes as ET, create_event, create_event_arne
from selfdrive.controls.lib.vehicle_model import VehicleModel
from selfdrive.car.toyota.carstate import CarState, get_can_parser, get_cam_can_parser, get_can_parser_init
from selfdrive.car.toyota.values import Ecu, ECU_FINGERPRINT, CAR, NO_STOP_TIMER_CAR, TSS2_CAR, FINGERPRINTS
from selfdrive.car import STD_CARGO_KG, scale_rot_inertia, scale_tire_stiffness, is_ecu_disconnected, gen_empty_fingerprint
from selfdrive.swaglog import cloudlog
from selfdrive.car.interfaces import CarInterfaceBase
from common.op_params import opParams
import cereal.messaging as messaging

ButtonType = car.CarState.ButtonEvent.Type
GearShifter = car.CarState.GearShifter

LaneChangeState = log.PathPlan.LaneChangeState

class CarInterface(CarInterfaceBase):
  def __init__(self, CP, CarController):
    self.CP = CP
    self.VM = VehicleModel(CP)
    self.waiting = False
    self.frame = 0
    self.gas_pressed_prev = False
    self.brake_pressed_prev = False
    self.cruise_enabled_prev = False
    self.keep_openpilot_engaged = True
    self.sm = messaging.SubMaster(['pathPlan'])
    # *** init the major players ***
    self.CS = CarState(CP)
    self.op_params = opParams()
    self.alca_min_speed = self.op_params.get('alca_min_speed', default=20.0)
    self.cp = get_can_parser(CP)
    self.cp_init = get_can_parser_init(CP)
    self.cp_cam = get_cam_can_parser(CP)

    self.CC = None
    if CarController is not None:
      self.CC = CarController(self.cp.dbc_name, CP.carFingerprint, CP.enableCamera, CP.enableDsu, CP.enableApgs)

  @staticmethod
  def compute_gb(accel, speed):
    return float(accel) / 4.0

  @staticmethod
  def get_params(candidate, fingerprint=gen_empty_fingerprint(), has_relay=False, car_fw=[]):
    ret = CarInterfaceBase.get_std_params(candidate, fingerprint, has_relay)

    ret.carName = "toyota"
    ret.safetyModel = car.CarParams.SafetyModel.toyota

    ret.steerActuatorDelay = 0.12  # Default delay, Prius has larger delay
    ret.steerLimitTimer = 0.4

    #if ret.enableGasInterceptor:
    #  ret.gasMaxBP = [0., 9., 55]
    #  ret.gasMaxV = [0.2, 0.5, 0.7]
    #  ret.longitudinalTuning.kpV = [0.5, 0.4, 0.3]  # braking tune
    #  ret.longitudinalTuning.kiV = [0.135, 0.1]
    #else:
    ret.gasMaxBP = [0., 9., 55]
    ret.gasMaxV = [0.2, 0.5, 0.7]
    ret.longitudinalTuning.kpV = [0.325, 0.325, 0.325]  # braking tune from rav4h
    ret.longitudinalTuning.kiV = [0.15, 0.10]

    if candidate not in [CAR.PRIUS, CAR.RAV4, CAR.RAV4H]: # These cars use LQR/INDI
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
      ret.lateralTuning.indi.innerLoopGain = 4.0
      ret.lateralTuning.indi.outerLoopGain = 3.0
      ret.lateralTuning.indi.timeConstant = 1.0
      ret.lateralTuning.indi.actuatorEffectiveness = 1.0
      ret.steerActuatorDelay = 0.5

    elif candidate in [CAR.RAV4H]:
      stop_and_go = True if (candidate in CAR.RAV4H) else False
      ret.safetyParam = 73
      ret.wheelbase = 2.65
      ret.steerRatio = 16.88   # 14.5 is spec end-to-end
      tire_stiffness_factor = 0.5533
      ret.mass = 3650. * CV.LB_TO_KG + STD_CARGO_KG  # mean between normal and hybrid
      ret.lateralTuning.init('lqr')

      ret.lateralTuning.lqr.scale = 1500.0
      ret.lateralTuning.lqr.ki = 0.06

      ret.lateralTuning.lqr.a = [0., 1., -0.22619643, 1.21822268]
      ret.lateralTuning.lqr.b = [-1.92006585e-04, 3.95603032e-05]
      ret.lateralTuning.lqr.c = [1., 0.]
      ret.lateralTuning.lqr.k = [-110.73572306, 451.22718255]
      ret.lateralTuning.lqr.l = [0.3233671, 0.3185757]
      ret.lateralTuning.lqr.dcGain = 0.002237852961363602

    elif candidate in [CAR.RAV4]:
      stop_and_go = True if (candidate in CAR.RAV4H) else False
      ret.safetyParam = 73
      ret.wheelbase = 2.65
      ret.steerRatio = 16.88   # 14.5 is spec end-to-end
      tire_stiffness_factor = 0.5533
      ret.mass = 3650. * CV.LB_TO_KG + STD_CARGO_KG  # mean between normal and hybrid
      ret.lateralTuning.init('lqr')

      ret.lateralTuning.lqr.scale = 1500.0
      ret.lateralTuning.lqr.ki = 0.06
      ret.longitudinalTuning.kpV = [0.1, 0.3, 0.3]  # braking tune
      ret.longitudinalTuning.kiV = [0.1, 0.1]
      ret.lateralTuning.lqr.a = [0., 1., -0.22619643, 1.21822268]
      ret.lateralTuning.lqr.b = [-1.92006585e-04, 3.95603032e-05]
      ret.lateralTuning.lqr.c = [1., 0.]
      ret.lateralTuning.lqr.k = [-110.73572306, 451.22718255]
      ret.lateralTuning.lqr.l = [0.3233671, 0.3185757]
      ret.lateralTuning.lqr.dcGain = 0.002237852961363602

    elif candidate == CAR.COROLLA:
      stop_and_go = False
      ret.safetyParam = 100
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

    elif candidate in [CAR.CHR, CAR.CHRH]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.63906
      ret.steerRatio = 13.6
      tire_stiffness_factor = 0.7933
      ret.mass = 3300. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.723], [0.0428]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate in [CAR.CAMRY, CAR.CAMRYH]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.82448
      ret.steerRatio = 13.7
      tire_stiffness_factor = 0.7933
      ret.mass = 3400. * CV.LB_TO_KG + STD_CARGO_KG #mean between normal and hybrid
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate == CAR.HIGHLANDER_TSS2:
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
      ret.mass = 4607. * CV.LB_TO_KG + STD_CARGO_KG #mean between normal and hybrid limited
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.18], [0.015]]  # community tuning
      ret.lateralTuning.pid.kf = 0.00012  # community tuning

    elif candidate == CAR.AVALON:
      stop_and_go = False
      ret.safetyParam = 73
      ret.wheelbase = 2.82
      ret.steerRatio = 14.8 #Found at https://pressroom.toyota.com/releases/2016+avalon+product+specs.download
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
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.mass = 3370. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate == CAR.RAV4H_TSS2:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.68986
      ret.steerRatio = 14.3
      tire_stiffness_factor = 0.7933
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.mass = 3800. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate == CAR.RAV4H_TSS2:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.68986
      ret.steerRatio = 14.3
      tire_stiffness_factor = 0.7933
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.mass = 3800. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate in [CAR.COROLLA_TSS2, CAR.COROLLAH_TSS2]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.63906
      ret.steerRatio = 13.9
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 3060. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate in [CAR.LEXUS_ES_TSS2, CAR.LEXUS_ESH_TSS2]:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.8702
      ret.steerRatio = 16.0 # not optimized
      tire_stiffness_factor = 0.444  # not optimized yet
      ret.mass = 3704. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate == CAR.SIENNA:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 3.03
      ret.steerRatio = 16.0
      tire_stiffness_factor = 0.444
      ret.mass = 4590. * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.3], [0.05]]
      ret.lateralTuning.pid.kf = 0.00007818594

    elif candidate in [CAR.LEXUS_IS, CAR.LEXUS_ISH, CAR.LEXUS_RX]:
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

    elif candidate == CAR.LEXUS_NXH:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.66
      ret.steerRatio = 14.7
      tire_stiffness_factor = 0.444 # not optimized yet
      ret.mass = 4070 * CV.LB_TO_KG + STD_CARGO_KG
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.6], [0.1]]
      ret.lateralTuning.pid.kf = 0.00006

    elif candidate == CAR.LEXUS_NXH:
      stop_and_go = True
      ret.safetyParam = 73
      ret.wheelbase = 2.66
      ret.steerRatio = 14.7
      tire_stiffness_factor = 0.444 # not optimized yet
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

    # no rear steering, at least on the listed cars above
    ret.steerRatioRear = 0.
    ret.steerControlType = car.CarParams.SteerControlType.torque

    # steer, gas, brake limitations VS speed
    ret.steerMaxBP = [16. * CV.KPH_TO_MS, 45. * CV.KPH_TO_MS]  # breakpoints at 1 and 40 kph
    ret.steerMaxV = [1., 1.]  # 2/3rd torque allowed above 45 kph
    ret.brakeMaxBP = [0., 35., 55.]
    ret.brakeMaxV = [1.0, 0.8, 0.7]

    ret.enableCamera = is_ecu_disconnected(fingerprint[0], FINGERPRINTS, ECU_FINGERPRINT, candidate, Ecu.fwdCamera) or has_relay
    # Detect smartDSU, which intercepts ACC_CMD from the DSU allowing openpilot to send it
    smartDsu = 0x2FF in fingerprint[0]
    # In TSS2 cars the camera does long control
    ret.enableDsu = is_ecu_disconnected(fingerprint[0], FINGERPRINTS, ECU_FINGERPRINT, candidate, Ecu.dsu) and candidate not in TSS2_CAR
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

    ret.longitudinalTuning.deadzoneBP = [0., 9.]
    ret.longitudinalTuning.deadzoneV = [0., .15]
    ret.longitudinalTuning.kpBP = [0., 5., 55.]
    ret.longitudinalTuning.kiBP = [0., 55.]
    ret.stoppingControl = False
    ret.startAccel = 0.0

    return ret

  # returns a car.CarState
  def update(self, c, can_strings):
    self.sm.update(0)
    # ******************* do can recv *******************
    self.cp_cam.update_strings(can_strings)
    if self.frame < 1000:
      self.cp_init.update_strings(can_strings)
      self.CS.update(self.cp_init, self.cp_cam, self.frame)
    else:
      self.cp.update_strings(can_strings)
      self.CS.update(self.cp, self.cp_cam, self.frame)

    # create message
    ret = car.CarState.new_message()
    ret_arne182 = arne182.CarStateArne182.new_message()

    ret.canValid = self.cp.can_valid and self.cp_cam.can_valid
    ret.yawRate = self.VM.yaw_rate(ret.steeringAngle * CV.DEG_TO_RAD, ret.vEgo)
    ret.steeringRateLimited = self.CC.steer_rate_limited if self.CC is not None else False
    eventsArne182 = []

    # cruise state
    if not self.cruise_enabled_prev:
      self.waiting = False
      ret.cruiseState.enabled = self.CS.pcm_acc_active
    else:
      if self.keep_openpilot_engaged:
        ret.cruiseState.enabled = bool(self.CS.main_on)
      if not self.CS.pcm_acc_active:
        eventsArne182.append(create_event_arne('longControlDisabled', [ET.WARNING]))
        ret.brakePressed = True
        self.waiting = False
    if self.CS.v_ego < 1 or not self.keep_openpilot_engaged:
      ret.cruiseState.enabled = self.CS.pcm_acc_active
    ret.cruiseState.speed = self.CS.v_cruise_pcm * CV.KPH_TO_MS
    ret.cruiseState.available = bool(self.CS.main_on)
    ret.cruiseState.speedOffset = 0.

    if self.CP.carFingerprint in NO_STOP_TIMER_CAR or self.CP.enableGasInterceptor:
      # ignore standstill in hybrid vehicles, since pcm allows to restart without
      # receiving any special command
      # also if interceptor is detected
      ret.cruiseState.standstill = False
    else:
      ret.cruiseState.standstill = self.CS.pcm_acc_status == 7

    buttonEvents = []
    if self.CS.left_blinker_on != self.CS.prev_left_blinker_on:
      be = car.CarState.ButtonEvent.new_message()
      be.type = ButtonType.leftBlinker
      be.pressed = self.CS.left_blinker_on != 0
      buttonEvents.append(be)

    if self.CS.right_blinker_on != self.CS.prev_right_blinker_on:
      be = car.CarState.ButtonEvent.new_message()
      be.type = ButtonType.rightBlinker
      be.pressed = self.CS.right_blinker_on != 0
      buttonEvents.append(be)

    ret.buttonEvents = buttonEvents
    ret.leftBlinker = bool(self.CS.left_blinker_on)
    ret.rightBlinker = bool(self.CS.right_blinker_on)

    ret.doorOpen = not self.CS.door_all_closed
    ret.seatbeltUnlatched = not self.CS.seatbelt

    ret.genericToggle = self.CS.generic_toggle
    ret.stockAeb = self.CS.stock_aeb

    if ret.cruiseState.enabled and not self.cruise_enabled_prev:  # this lets us modularize which checks we want to turn off op if cc was engaged previoiusly or not
      disengage_event = True
    else:
      disengage_event = False

    # events
    events = self.create_common_events(ret)


    if self.cp_cam.can_invalid_cnt >= 200 and self.CP.enableCamera:
      events.append(create_event('invalidGiraffeToyota', [ET.PERMANENT]))
    if not ret.gearShifter == GearShifter.drive and self.CP.openpilotLongitudinalControl:
      if ret.vEgo < 5:
        eventsArne182.append(create_event_arne('wrongGearArne', [ET.NO_ENTRY, ET.SOFT_DISABLE]))
      else:
        events.append(create_event('wrongGear', [ET.NO_ENTRY, ET.SOFT_DISABLE]))
    if ret.doorOpen and disengage_event:
      events.append(create_event('doorOpen', [ET.NO_ENTRY, ET.SOFT_DISABLE]))
    if ret.seatbeltUnlatched and disengage_event:
      events.append(create_event('seatbeltNotLatched', [ET.NO_ENTRY, ET.SOFT_DISABLE]))
    if self.CS.esp_disabled and self.CP.openpilotLongitudinalControl:
      events.append(create_event('espDisabled', [ET.NO_ENTRY, ET.SOFT_DISABLE]))
    if not self.CS.main_on and self.CP.openpilotLongitudinalControl:
      events.append(create_event('wrongCarMode', [ET.NO_ENTRY, ET.USER_DISABLE]))
    if ret.gearShifter == GearShifter.reverse and self.CP.openpilotLongitudinalControl:
      if ret.vEgo < 5:
        eventsArne182.append(create_event_arne('reverseGearArne', [ET.NO_ENTRY, ET.IMMEDIATE_DISABLE]))
      else:
        events.append(create_event('reverseGear', [ET.NO_ENTRY, ET.IMMEDIATE_DISABLE]))
    if self.CS.steer_error:
      events.append(create_event('steerTempUnavailable', [ET.NO_ENTRY, ET.WARNING]))
    if self.CS.low_speed_lockout and self.CP.openpilotLongitudinalControl:
      events.append(create_event('lowSpeedLockout', [ET.NO_ENTRY, ET.PERMANENT]))
    if ret.vEgo < self.CP.minEnableSpeed and self.CP.openpilotLongitudinalControl:
      events.append(create_event('speedTooLow', [ET.NO_ENTRY]))
      if c.actuators.gas > 0.1:
        # some margin on the actuator to not false trigger cancellation while stopping
        events.append(create_event('speedTooLow', [ET.IMMEDIATE_DISABLE]))
      if ret.vEgo < 0.001:
        # while in standstill, send a user alert
        events.append(create_event('manualRestart', [ET.WARNING]))

    # enable request in prius is simple, as we activate when Toyota is active (rising edge)
    if ret.cruiseState.enabled and not self.cruise_enabled_prev:
      events.append(create_event('pcmEnable', [ET.ENABLE]))
    elif not ret.cruiseState.enabled:
      events.append(create_event('pcmDisable', [ET.USER_DISABLE]))
      try:
        if eventsArne182[0].name == 'longControlDisabled':
          del eventsArne182[0]
      except IndexError:
        pass
    if not self.waiting and ret.vEgo < 0.3 and not ret.gasPressed and self.CP.carFingerprint == CAR.RAV4H:
      self.waiting = True
    if self.waiting:
      if ret.gasPressed:
        self.waiting = False
      else:
        eventsArne182.append(create_event_arne('waitingMode', [ET.WARNING]))
    # disable on pedals rising edge or when brake is pressed and speed isn't zero
    if (((ret.gasPressed and not self.gas_pressed_prev) or \
       (ret.brakePressed and (not self.brake_pressed_prev or ret.vEgo > 0.001))) and disengage_event) or (ret.brakePressed and not self.brake_pressed_prev and ret.vEgo < 0.1):
      events.append(create_event('pedalPressed', [ET.NO_ENTRY, ET.USER_DISABLE]))

    if ret.gasPressed and disengage_event:
      events.append(create_event('pedalPressed', [ET.PRE_ENABLE]))
    if ret.rightBlinker and self.CS.rightblindspot and ret.vEgo > self.alca_min_speed and self.sm['pathPlan'].laneChangeState  == LaneChangeState.preLaneChange:
      eventsArne182.append(create_event_arne('rightALCbsm', [ET.WARNING]))
    if ret.leftBlinker and self.CS.leftblindspot and ret.vEgo > self.alca_min_speed and self.sm['pathPlan'].laneChangeState  == LaneChangeState.preLaneChange:
      eventsArne182.append(create_event_arne('leftALCbsm', [ET.WARNING]))
    ret.events = events
    ret_arne182.events = eventsArne182

    self.gas_pressed_prev = ret.gasPressed
    self.brake_pressed_prev = ret.brakePressed
    self.cruise_enabled_prev = ret.cruiseState.enabled

    return ret.as_reader(), ret_arne182.as_reader()

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
