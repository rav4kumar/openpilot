import numpy as np
from common.realtime import sec_since_boot
from selfdrive.controls.lib.pid import PIController
from common.numpy_fast import interp
from selfdrive.kegman_conf import kegman_conf
from cereal import car

_DT = 0.01    # 100Hz


def get_steer_max(CP, v_ego):
  return interp(v_ego, CP.steerMaxBP, CP.steerMaxV)

class LatControl(object):
  def __init__(self, CP):

    kegman = kegman_conf(CP)
    self.gernbySteer = True
    self.mpc_frame = 0
    self.total_desired_projection = max(0.0, CP.steerMPCReactTime + CP.steerMPCDampTime)
    self.desired_smoothing = max(1.0, CP.steerMPCDampTime / _DT)
    self.angle_ff_gain = -1.0
    self.rate_ff_gain = -1.0
    self.angle_ff_bp = [[0.5, 5.0],[0.0, 1.0]]
    self.dampened_actual_angle = 0.0
    self.dampened_desired_angle = 0.0
    self.dampened_desired_rate = 0.0
    self.angle_steers_noise = 0.4
    self.rate_mode = 0.0
    self.angle_mode = 0.0

    KpV = [interp(25.0, CP.steerKpBP, CP.steerKpV)]
    KiV = [interp(25.0, CP.steerKiBP, CP.steerKiV)]
    self.pid = PIController(([0.], KpV),
                            ([0.], KiV),
                            k_f=CP.steerKf, pos_limit=1.0)

  def adjust_angle_gain(self):
    if self.pid.i > self.previous_integral:
      if self.pid.f > 0 and self.pid.i > 0:
        self.angle_ff_gain *= 1.0001
      else:
        self.angle_ff_gain *= 0.9999
    elif self.pid.i < self.previous_integral:
      if self.pid.f < 0 and self.pid.i < 0:
        self.angle_ff_gain *= 1.0001
      else:
        self.angle_ff_gain *= 0.9999
    self.previous_integral = self.pid.i

  def adjust_rate_gain(self, angle_steers):
    self.angle_steers_noise += 0.0001 * ((angle_steers - self.dampened_actual_angle)**2 - self.angle_steers_noise)
    #self.angle_steers_noise += 0.0001 * (steer_rate**2 - self.angle_steers_noise)
    if self.angle_steers_noise**0.5 > 0.4:
      self.rate_ff_gain *= 0.9999
    else:
      self.rate_ff_gain *= 1.0001

  def live_tune(self, CP):
    self.mpc_frame += 1
    if self.mpc_frame % 300 == 0:
      # live tuning through /data/openpilot/tune.py overrides interface.py settings
      kegman = kegman_conf()
      if kegman.conf['tuneGernby'] == "1":
        self.steerKpV = np.array([float(kegman.conf['Kp'])])
        self.steerKiV = np.array([float(kegman.conf['Ki'])])
        self.total_desired_projection = max(0.0, float(kegman.conf['dampMPC']) + float(kegman.conf['reactMPC']))
        self.desired_smoothing = max(1.0, float(kegman.conf['dampMPC']) / _DT)
        self.gernbySteer = (self.total_desired_projection > 0 or self.desired_smoothing > 1)

        # Eliminate break-points, since they aren't needed (and would cause problems for resonance)
        KpV = [interp(25.0, CP.steerKpBP, self.steerKpV)]
        KiV = [interp(25.0, CP.steerKiBP, self.steerKiV)]
        self.pid._k_i = ([0.], KiV)
        self.pid._k_p = ([0.], KpV)
        print(self.angle_ff_gain, self.rate_ff_gain, self.total_desired_projection, self.desired_smoothing, self.gernbySteer)
      else:
        self.gernbySteer = False
      self.mpc_frame = 0


  def reset(self):
    self.pid.reset()

  def update(self, active, v_ego, angle_steers, rate_steers, steer_override, CP, VM, path_plan):

    self.live_tune(CP)

    if v_ego < 0.3 or not active:
      output_steer = 0.0
      self.pid.reset()
      self.dampened_desired_angle = float(angle_steers)
      self.rate_ff_gain = VM.rG
      self.angle_ff_gain = VM.aG
      #self.angle_ff_counter = 0
      #self.rate_ff_counter = 0
      #self.desired_rate_noise = 0.0
      #self.angle_steers_noise = 0.0
      #self.last_angle = 0.0
    else:
      if self.gernbySteer == False:
        self.dampened_desired_angle = float(path_plan.angleSteers)

      else:
        cur_time = sec_since_boot()
        projected_desired_angle = interp(cur_time + self.total_desired_projection, path_plan.mpcTimes, path_plan.mpcAngles)
        self.dampened_desired_angle += ((projected_desired_angle - self.dampened_desired_angle) / self.desired_smoothing)
        projected_desired_rate = interp(cur_time + self.total_desired_projection, path_plan.mpcTimes, path_plan.mpcRates)
        self.dampened_desired_rate += ((projected_desired_rate - self.dampened_desired_rate) / self.desired_smoothing)

      if CP.steerControlType == car.CarParams.SteerControlType.torque:
        steers_max = get_steer_max(CP, v_ego)
        self.pid.pos_limit = steers_max
        self.pid.neg_limit = -steers_max
        deadzone = 0.0

        ff_target_angle = self.dampened_desired_angle - path_plan.angleOffset
        self.angle_mode = interp(abs(ff_target_angle), self.angle_ff_bp[0], self.angle_ff_bp[1])
        self.rate_mode = 1.0 - self.angle_mode
        angle_feedforward = self.angle_mode * self.angle_ff_gain * ff_target_angle
        rate_feedforward = self.rate_mode * self.rate_ff_gain * self.dampened_desired_rate
        feed_forward = v_ego**2 * (rate_feedforward + angle_feedforward)

        output_steer = self.pid.update(self.dampened_desired_angle, angle_steers, check_saturation=(v_ego > 10),
                                      override=steer_override, feedforward=feed_forward, speed=v_ego, deadzone=deadzone)

        if not steer_override and v_ego > 10.0:
          if abs(angle_steers) > (self.angle_ff_bp[0][1] / 2.0):
            self.adjust_angle_gain()
          else:
            self.previous_integral = 0.0
            self.adjust_rate_gain(angle_steers)

    self.sat_flag = self.pid.saturated
    self.dampened_actual_angle += 0.05 * (angle_steers - self.dampened_actual_angle)

    if CP.steerControlType == car.CarParams.SteerControlType.torque:
      return float(output_steer), float(path_plan.angleSteers)
    else:
      return float(self.dampened_desired_angle), float(path_plan.angleSteers)
