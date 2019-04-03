import numpy as np
from common.realtime import sec_since_boot
from selfdrive.controls.lib.pid import PIController
from common.numpy_fast import interp
from selfdrive.kegman_conf import kegman_conf
from cereal import car

_DT = 0.01    # 100Hz


def get_steer_max(CP, v_ego):
  return interp(v_ego, CP.steerMaxBP, CP.steerMaxV)

def apply_deadzone(angle, deadzone):
  if angle > deadzone:
    angle -= deadzone
  elif angle < - deadzone:
    angle += deadzone
  else:
    angle = 0.
  return angle


class LatControl(object):
  def __init__(self, CP):

    kegman = kegman_conf()
    self.write_conf = False
    self.gernbySteer = True
    kegman.conf['tuneGernby'] = str(1)
    self.write_conf = True
    if kegman.conf['tuneGernby'] == "-1":
      kegman.conf['tuneGernby'] = str(1)
      self.write_conf = True
    if kegman.conf['reactSteer'] == "-1":
      kegman.conf['reactSteer'] = str(round(CP.steerReactTime,3))
      self.write_conf = True
    if kegman.conf['dampSteer'] == "-1":
      kegman.conf['dampSteer'] = str(round(CP.steerDampTime,3))
      self.write_conf = True
    if kegman.conf['reactMPC'] == "-1":
      kegman.conf['reactMPC'] = str(round(CP.steerMPCReactTime,3))
      self.write_conf = True
    if kegman.conf['dampMPC'] == "-1":
      kegman.conf['dampMPC'] = str(round(CP.steerMPCDampTime,3))
      self.write_conf = True
    if kegman.conf['Kp'] == "-1":
      kegman.conf['Kp'] = str(round(CP.steerKpV[0],3))
      self.write_conf = True
    if kegman.conf['Ki'] == "-1":
      kegman.conf['Ki'] = str(round(CP.steerKiV[0],3))
      self.write_conf = True

    if self.write_conf:
      kegman.write_config(kegman.conf)

    self.mpc_frame = 0
    self.total_desired_projection = max(0.0, CP.steerMPCReactTime + CP.steerMPCDampTime)
    self.total_actual_projection = max(0.0, CP.steerReactTime + CP.steerDampTime)
    self.actual_smoothing = max(1.0, CP.steerDampTime / _DT)
    self.desired_smoothing = max(1.0, CP.steerMPCDampTime / _DT)
    self.ff_angle_factor = 0.5
    self.ff_rate_factor = 1.0
    self.dampened_desired_angle = 0.0
    self.steer_counter = 1.0
    self.steer_counter_prev = 0.0
    self.rough_steers_rate = 0.0
    self.prev_angle_steers = 0.0
    self.calculate_rate = True
    self.lane_prob_reset = False
    self.feed_forward = 0.0

    KpV = [interp(25.0, CP.steerKpBP, CP.steerKpV)]
    KiV = [interp(25.0, CP.steerKiBP, CP.steerKiV)]
    self.pid = PIController(([0.], KpV),
                            ([0.], KiV),
                            k_f=CP.steerKf, pos_limit=1.0)

  def live_tune(self, CP):
    self.mpc_frame += 1
    if self.mpc_frame % 300 == 0:
      # live tuning through /data/openpilot/tune.py overrides interface.py settings
      kegman = kegman_conf()
      if kegman.conf['tuneGernby'] == "1":
        self.steerKpV = np.array([float(kegman.conf['Kp'])])
        self.steerKiV = np.array([float(kegman.conf['Ki'])])
        self.total_actual_projection = max(0.0, float(kegman.conf['dampSteer']) + float(kegman.conf['reactSteer']))
        self.total_desired_projection = max(0.0, float(kegman.conf['dampMPC']) + float(kegman.conf['reactMPC']))
        self.actual_smoothing = max(1.0, float(kegman.conf['dampSteer']) / _DT)
        self.desired_smoothing = max(1.0, float(kegman.conf['dampMPC']) / _DT)
        self.gernbySteer = (self.total_actual_projection > 0 or self.actual_smoothing > 1 or self.total_desired_projection > 0 or self.desired_smoothing > 1)

        # Eliminate break-points, since they aren't needed (and would cause problems for resonance)
        KpV = [interp(25.0, CP.steerKpBP, self.steerKpV)]
        KiV = [interp(25.0, CP.steerKiBP, self.steerKiV)]
        self.pid._k_i = ([0.], KiV)
        self.pid._k_p = ([0.], KpV)
        print(self.total_desired_projection, self.desired_smoothing, self.total_actual_projection, self.actual_smoothing, self.gernbySteer)
      else:
        self.gernbySteer = False
      self.mpc_frame = 0


  def reset(self):
    self.pid.reset()

  def update(self, active, v_ego, angle_steers, angle_rate, steer_override, CP, VM, path_plan):

    self.live_tune(CP)
    if angle_rate == 0.0 and self.calculate_rate:
      if angle_steers != self.prev_angle_steers:
        self.steer_counter_prev = self.steer_counter
        self.rough_steers_rate = (self.rough_steers_rate + 100.0 * (angle_steers - self.prev_angle_steers) / self.steer_counter_prev) / 2.0
        self.steer_counter = 0.0
      elif self.steer_counter >= self.steer_counter_prev:
        self.rough_steers_rate = (self.steer_counter * self.rough_steers_rate) / (self.steer_counter + 1.0)
      self.steer_counter += 1.0
      angle_rate = self.rough_steers_rate
      self.prev_angle_steers = float(angle_steers)
    else:
      # If non-zero angle_rate is provided, stop calculating rate
      self.calculate_rate = False

    if v_ego < 0.3 or not active:
      output_steer = 0.0
      self.pid.reset()
      self.dampened_angle_steers = float(angle_steers)
      self.dampened_desired_angle = float(angle_steers)
    else:

      if self.gernbySteer == False:
        self.dampened_angle_steers = float(angle_steers)
        self.dampened_desired_angle = float(path_plan.angleSteers)

      else:
        projected_desired_angle = interp(sec_since_boot() + self.total_desired_projection, path_plan.mpcTimes, path_plan.mpcAngles)
        self.dampened_desired_angle += ((projected_desired_angle - self.dampened_desired_angle) / self.desired_smoothing)

        projected_angle_steers = float(angle_steers) + self.total_actual_projection * float(angle_rate)
        if not steer_override:
          self.dampened_angle_steers += ((projected_angle_steers - self.dampened_angle_steers) / self.actual_smoothing)

      if path_plan.laneProb == 0.0 and self.lane_prob_reset == False:
        if path_plan.lPoly[3] - path_plan.rPoly[3] > 3.9:
          print(self.dampened_desired_angle, path_plan.angleSteers)
          self.dampened_desired_angle = path_plan.angleSteers
        self.lane_prob_reset = True
      elif path_plan.laneProb > 0.0:
        self.lane_prob_reset = False

      if CP.steerControlType == car.CarParams.SteerControlType.torque:

        steers_max = get_steer_max(CP, v_ego)
        self.pid.pos_limit = steers_max
        self.pid.neg_limit = -steers_max
        deadzone = 0.0

        angle_feedforward = apply_deadzone(self.ff_angle_factor * (self.dampened_desired_angle - path_plan.angleOffset), 0.5) * v_ego**2
        rate_feedforward = self.ff_rate_factor * path_plan.rateSteers * v_ego**2
        rate_more_significant = (abs(rate_feedforward) > abs(angle_feedforward))
        rate_same_direction = (rate_feedforward > 0) == (angle_feedforward > 0)
        rate_away_from_zero = ((angle_steers - path_plan.angleOffset) > 0 == (rate_feedforward > 0))

        if rate_more_significant and rate_same_direction: # and rate_away_from_zero:
          self.feed_forward += ((rate_feedforward - self.feed_forward) / self.desired_smoothing)
          #print(self.feed_forward)
        else:
          self.feed_forward += ((angle_feedforward - self.feed_forward) / self.desired_smoothing)

        output_steer = self.pid.update(self.dampened_desired_angle, self.dampened_angle_steers, check_saturation=(v_ego > 10),
                                      override=steer_override, feedforward=self.feed_forward, speed=v_ego, deadzone=deadzone)

    self.sat_flag = self.pid.saturated
    self.prev_angle_steers = float(angle_steers)

    if CP.steerControlType == car.CarParams.SteerControlType.torque:
      return float(output_steer), float(path_plan.angleSteers)
    else:
      return float(self.dampened_desired_angle), float(path_plan.angleSteers)
