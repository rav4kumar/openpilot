import numpy as np
from common.realtime import sec_since_boot
from selfdrive.controls.lib.pid import PIController
from common.numpy_fast import interp
from selfdrive.kegman_conf import kegman_conf
from cereal import car

def get_steer_max(CP, v_ego):
  return interp(v_ego, CP.steerMaxBP, CP.steerMaxV)

class LatControl(object):
  def __init__(self, CP):

    kegman = kegman_conf(CP)
    self.gernbySteer = True
    self.mpc_frame = 0
    self.total_rate_projection = max(0.0, CP.rateReactTime + CP.rateDampTime)
    self.actual_rate_smoothing = max(1.0, CP.rateDampTime * CP.carCANRate)
    self.total_angle_projection = max(0.0, CP.steerReactTime + CP.steerDampTime)
    self.actual_angle_smoothing = max(1.0, CP.steerDampTime * CP.carCANRate)
    self.total_desired_projection = max(0.0, CP.steerMPCReactTime + CP.steerMPCDampTime)
    self.desired_smoothing = max(1.0, CP.steerMPCDampTime * CP.carCANRate)
    self.delaySteer = CP.steerActuatorDelay
    self.dampened_angle_steers = 0.0
    self.dampened_actual_angle = 0.0
    self.dampened_angle_rate = 0.0
    self.dampened_desired_angle = 0.0
    self.dampened_desired_rate = 0.0
    self.previous_integral = 0.0
    self.last_cloudlog_t = 0.0
    self.angle_steers_des = 0.
    self.angle_ff_ratio = 0.0
    self.standard_ff_ratio = 0.0
    self.angle_ff_gain = 1.0
    self.rate_ff_gain = CP.rateFFGain
    self.average_angle_steers = 0.
    self.angle_ff_bp = [[0.5, 5.0],[0.0, 1.0]]
    self.oscillation_period = CP.oscillationPeriod
    self.oscillation_factor = CP.oscillationFactor
    self.deadzone = -CP.steerBacklash
    self.doScale = True if len(CP.steerPscale) > 0 else False
    self.prev_angle_rate= 0.0
    self.longOffset = 0.0
    self.steer_counter = 1
    self.steer_counter_prev = 0
    self.angle_accel = 0.0

    KpV = [interp(25.0, CP.steerKpBP, CP.steerKpV)]
    KiV = [interp(25.0, CP.steerKiBP, CP.steerKiV)]
    self.pid = PIController(([0.], KpV),
                            ([0.], KiV),
                            k_f=CP.steerKf, pos_limit=1.0, rate=int(CP.carCANRate))

  def live_tune(self, CP):
    self.mpc_frame += 1
    if self.mpc_frame % 300 == 0:
      # live tuning through /data/openpilot/tune.py overrides interface.py settings
      kegman = kegman_conf()
      if kegman.conf['tuneGernby'] == "1":
        self.steerKpV = np.array([float(kegman.conf['Kp'])])
        self.steerKiV = np.array([float(kegman.conf['Ki'])])
        self.total_angle_projection = max(0.0, float(kegman.conf['dampSteer']) + float(kegman.conf['reactSteer']))
        self.total_rate_projection = max(0.0, float(kegman.conf['dampRate']) + float(kegman.conf['reactRate']))
        self.total_desired_projection = max(0.0, float(kegman.conf['dampMPC']) + float(kegman.conf['reactMPC']))
        self.actual_rate_smoothing = max(1.0, float(kegman.conf['dampRate']) * CP.carCANRate)
        self.actual_angle_smoothing = max(1.0, float(kegman.conf['dampSteer']) * CP.carCANRate)
        self.desired_smoothing = max(1.0, float(kegman.conf['dampMPC']) * CP.carCANRate)
        self.rate_ff_gain = float(kegman.conf['rateFF'])
        self.gernbySteer = (self.total_desired_projection > 0 or self.desired_smoothing > 1)
        self.delaySteer = float(kegman.conf['delaySteer'])
        self.oscillation_factor = float(kegman.conf['oscFactor'])
        self.oscillation_period = float(kegman.conf['oscPeriod'])
        self.deadzone = -float(kegman.conf['backlash'])
        self.longOffset = float(kegman.conf['longOffset'])

        # Eliminate break-points, since they aren't needed (and would cause problems for resonance)
        KpV = [interp(25.0, CP.steerKpBP, self.steerKpV)]
        KiV = [interp(25.0, CP.steerKiBP, self.steerKiV)]
        self.pid._k_i = ([0.], KiV)
        self.pid._k_p = ([0.], KpV)
        self.standard_ff_ratio = 0.0
        print(self.rate_ff_gain, self.angle_ff_gain)
      else:
        self.gernbySteer = False
        self.standard_ff_ratio = 1.0
        self.angle_ff_ratio = 0.0
      self.mpc_frame = 0

  def reset(self):
    self.pid.reset()

  def adjust_angle_gain(self):
    if (self.pid.f > 0) == (self.pid.i > 0) and abs(self.pid.i) >= abs(self.previous_integral):
      self.angle_ff_gain *= 1.0001
    elif self.angle_ff_gain > 1.0:
      self.angle_ff_gain *= 0.9999
    self.previous_integral = self.pid.i

  def calc_angle_accel(self, CP, angle_rate):
    if angle_rate != self.prev_angle_rate:
      self.steer_counter_prev = self.steer_counter
      self.angle_accel = CP.carCANRate * (self.prev_angle_rate - angle_rate) / self.steer_counter_prev
      self.prev_angle_rate = angle_rate
      self.steer_counter = 0.0
    elif self.steer_counter >= self.steer_counter_prev:
      self.angle_accel = (self.steer_counter * self.angle_accel) / (self.steer_counter + 1.0)
    self.steer_counter += 1.0
    return self.angle_accel

  def update(self, active, v_ego, angle_steers, angle_rate, torque_clipped, steer_override, CP, VM, path_plan):

    self.live_tune(CP)

    if v_ego < 0.3 or not active:
      output_steer = 0.0
      self.pid.reset()
      self.previous_integral = 0.0
      self.dampened_angle_steers = float(angle_steers)
      self.dampened_desired_angle = float(angle_steers)
      self.dampened_angle_rate = float(angle_rate)
      self.dampened_desired_rate = 0.0
    else:
      if self.gernbySteer == False:
        self.dampened_angle_steers = float(angle_steers)
        self.dampened_desired_angle = float(path_plan.angleSteers)
        self.dampened_desired_rate = float(path_plan.rateSteers)

      else:
        cur_time = sec_since_boot()
        projected_desired_angle = interp(cur_time + self.total_desired_projection, path_plan.mpcTimes, path_plan.mpcAngles)
        self.dampened_desired_angle += ((projected_desired_angle - self.dampened_desired_angle) / self.desired_smoothing)
        projected_desired_rate = interp(cur_time + self.total_desired_projection, path_plan.mpcTimes, path_plan.mpcRates)
        self.dampened_desired_rate += ((projected_desired_rate - self.dampened_desired_rate) / self.desired_smoothing)

        if not steer_override:
          self.angle_accel = self.calc_angle_accel(CP, angle_rate)
          projected_angle_rate = angle_rate + self.total_rate_projection * self.angle_accel
          self.dampened_angle_rate += ((projected_angle_rate - self.dampened_angle_rate) / self.actual_rate_smoothing)
          projected_angle_steers = float(angle_steers) + self.total_angle_projection * self.dampened_angle_rate
          self.dampened_angle_steers += ((projected_angle_steers - self.dampened_angle_steers) / self.actual_angle_smoothing)

      if CP.steerControlType == car.CarParams.SteerControlType.torque:
        steers_max = get_steer_max(CP, v_ego)
        self.pid.pos_limit = steers_max
        self.pid.neg_limit = -steers_max

        angle_feedforward = self.dampened_desired_angle - path_plan.angleOffset
        if self.gernbySteer:
          if self.doScale:
            if abs(self.dampened_desired_angle) > abs(self.dampened_angle_steers):
              p_scale = interp(abs(angle_feedforward), CP.steerPscale[0], CP.steerPscale[1])
            else:
              p_scale = interp(abs(angle_feedforward), CP.steerPscale[0], CP.steerPscale[2])
          else:
            p_scale = 1.0
          self.angle_ff_ratio = interp(abs(angle_feedforward), self.angle_ff_bp[0], self.angle_ff_bp[1])
          angle_feedforward *= self.angle_ff_ratio * self.angle_ff_gain
          rate_feedforward = (1.0 - self.angle_ff_ratio) * self.rate_ff_gain * self.dampened_desired_rate
          steer_feedforward = v_ego**2 * (rate_feedforward + angle_feedforward)
        else:
          p_scale = 1.0
          steer_feedforward = v_ego**2 * angle_feedforward

        output_steer = self.pid.update(self.dampened_desired_angle, self.dampened_angle_steers, check_saturation=(v_ego > 10),
                                    override=steer_override, feedforward=steer_feedforward, speed=v_ego, deadzone=self.deadzone,
                                    p_scale=p_scale)

        if self.gernbySteer and not torque_clipped and not steer_override and v_ego > 10.0:
          if abs(angle_steers) > (self.angle_ff_bp[0][1] / 2.0):
            self.adjust_angle_gain()
          else:
            self.previous_integral = self.pid.i

    self.sat_flag = self.pid.saturated
    self.average_angle_steers += 0.1 * (angle_steers - self.average_angle_steers)

    if CP.steerControlType == car.CarParams.SteerControlType.torque:
      return float(output_steer), float(path_plan.angleSteers), float(self.dampened_desired_rate)
    else:
      return float(self.dampened_desired_angle), float(path_plan.angleSteers), float(self.dampened_desired_rate)
