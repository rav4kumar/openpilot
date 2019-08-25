from selfdrive.controls.lib.pid import PIController
from selfdrive.controls.lib.future_angle import future_angle
from selfdrive.controls.lib.drive_helpers import get_steer_max
from selfdrive.kegman_conf import kegman_conf
from common.numpy_fast import interp, clip
from cereal import log
from common.realtime import sec_since_boot
from common.params import Params
import json
import numpy as np

class LatControlLIF(object):
  def __init__(self, CP):
    kegman_conf(CP)
    self.frame = 0
    self.pid = PIController((CP.lateralTuning.pid.kpBP, CP.lateralTuning.pid.kpV),
                            (CP.lateralTuning.pid.kiBP, CP.lateralTuning.pid.kiV),
                            k_f=CP.lateralTuning.pid.kf, pos_limit=1.0)
    self.future_angle = future_angle(CP)
    self.angle_steers_des = 0.
    self.total_poly_projection = max(0.0, CP.lateralTuning.pid.polyReactTime + CP.lateralTuning.pid.polyDampTime)
    self.poly_smoothing = max(1.0, CP.lateralTuning.pid.polyDampTime * 100.)
    self.poly_factor = CP.lateralTuning.pid.polyFactor
    self.path_error = 0.0
    self.p_poly = [0., 0., 0., 0.]
    self.s_poly = [0., 0., 0., 0.]
    self.c_prob = 1.0
    self.damp_angle_steers = 0.
    self.damp_time = 0.1
    self.react_mpc = 0.0
    self.damp_mpc = 0.1
    self.angle_ff_ratio = 0.0
    self.gernbySteer = True
    self.standard_ff_ratio = 0.0
    self.angle_ff_gain = 1.0
    self.rate_ff_gain = CP.lateralTuning.pid.rateFFGain
    self.angle_ff_bp = [[0.5, 5.0],[0.0, 1.0]]
    self.calculate_rate = True
    self.prev_angle_steers = 0.0
    self.rough_steers_rate = 0.0
    self.steer_counter = 1
    self.steer_counter_prev = 1
    self.params = Params()
    self.prev_override = False
    self.driver_assist_offset = 0.0
    self.driver_assist_hold = False
    self.angle_bias = 0.
    self.p_scale = 0.

    try:
      lateral_params = self.params.get("LateralParams")
      lateral_params = json.loads(lateral_params)
      self.angle_ff_gain = max(1.0, float(lateral_params['angle_ff_gain']))
      self.future_angle.torque_gain_outward = np.array(lateral_params['torque_gain_outward'])
      self.future_angle.torque_gain_outward_count = np.array(lateral_params['torque_gain_outward_count'])
      self.future_angle.torque_gain_inward = np.array(lateral_params['torque_gain_inward'])
      self.future_angle.torque_gain_inward_count = np.array(lateral_params['torque_gain_inward_count'])
    except:
      self.angle_ff_gain = 1.0

  def live_tune(self, CP):
    self.frame += 1
    if self.frame % 6000 == 0:
      self.params.put("LateralParams", json.dumps({'angle_ff_gain': self.angle_ff_gain,
                                                    "torque_gain_outward": list(self.future_angle.torque_gain_outward),
                                                    "torque_gain_inward": list(self.future_angle.torque_gain_inward),
                                                    "torque_gain_outward_count": list(self.future_angle.torque_gain_outward_count),
                                                    "torque_gain_inward_count": list(self.future_angle.torque_gain_inward_count),
                                                    "inverted:": self.future_angle.inverted}))
    if self.frame % 300 == 0:
      # live tuning through /data/openpilot/tune.py overrides interface.py settings
      kegman = kegman_conf()
      self.pid._k_i = ([0.], [float(kegman.conf['Ki'])])
      self.pid._k_p = ([0.], [float(kegman.conf['Kp']) * 0.5])
      self.pid.k_f = (float(kegman.conf['Kf']))
      self.damp_time = (float(kegman.conf['dampTime']))
      self.react_mpc = (float(kegman.conf['reactMPC']))
      self.damp_mpc = (float(kegman.conf['dampMPC']))
      self.total_poly_projection = max(0.0, float(kegman.conf['polyReact']) + float(kegman.conf['polyDamp']))
      self.poly_smoothing = max(1.0, float(kegman.conf['polyDamp']) * 100.)
      self.poly_factor = float(kegman.conf['polyFactor'])

  def get_projected_path_error(self, v_ego, angle_feedforward, angle_steers, live_params, path_plan, VM):
    curv_factor = interp(abs(angle_feedforward), [1.0, 5.0], [0.0, 1.0])
    self.p_poly[3] += (path_plan.pPoly[3] - self.p_poly[3]) # / 1.0
    self.p_poly[2] += curv_factor * (path_plan.pPoly[2] - self.p_poly[2]) # / (1.5)
    self.p_poly[1] += curv_factor * (path_plan.pPoly[1] - self.p_poly[1]) # / (3.0)
    self.p_poly[0] += curv_factor * (path_plan.pPoly[0] - self.p_poly[0]) # / (4.5)
    self.s_poly[1] = curv_factor * float(np.tan(VM.calc_curvature(np.radians(angle_steers - live_params.angleOffsetAverage - self.angle_bias), float(v_ego))))
    x = int(float(v_ego) * self.total_poly_projection * interp(abs(angle_feedforward), [0., 5.], [0.25, 1.0]))
    self.p_pts = np.polyval(self.p_poly, np.arange(0, x))
    self.s_pts = np.polyval(self.s_poly, np.arange(0, x))
    path_error = path_plan.cProb * (np.sum(self.p_pts) - np.sum(self.s_pts))
    if abs(path_error) < abs(self.path_error):
      path_error *= 0.25
    return path_error

  def reset(self):
    self.pid.reset()

  def adjust_angle_gain(self):
    if ((self.pid.f > 0) == (self.pid.i > 0) and (abs(self.pid.i) >= abs(self.previous_integral))):
      #if not abs(self.pid.f + self.pid.i + self.pid.p) > 1: self.angle_ff_gain *= 1.0001
      if (self.path_error >= 0) == (self.pid.f >= 0) and abs(self.pid.f) < 1.0: self.angle_ff_gain *= 1.0001
    elif self.angle_ff_gain > 1.0:
      self.angle_ff_gain *= 0.9999
    self.previous_integral = self.pid.i

  def update(self, active, v_ego, angle_steers, angle_steers_rate, steering_torque, steer_override, blinkers_on, CP, VM, path_plan, live_params, live_mpc):

    if angle_steers_rate == 0.0 and self.calculate_rate:
      if angle_steers != self.prev_angle_steers:
        self.steer_counter_prev = self.steer_counter
        self.rough_steers_rate = (self.rough_steers_rate + 100.0 * (angle_steers - self.prev_angle_steers) / self.steer_counter_prev) / 2.0
        self.steer_counter = 0.0
      elif self.steer_counter >= self.steer_counter_prev:
        self.rough_steers_rate = (self.steer_counter * self.rough_steers_rate) / (self.steer_counter + 1.0)
      self.steer_counter += 1.0
      angle_steers_rate = self.rough_steers_rate
      self.prev_angle_steers = float(angle_steers)
    else:
      # If non-zero angle_rate is provided, stop calculating rate
      self.calculate_rate = False

    pid_log = log.ControlsState.LateralPIDState.new_message()
    pid_log.steerAngle = float(angle_steers)
    pid_log.steerRate = float(angle_steers_rate)

    max_bias_change = 0.002  #min(0.001, 0.0002 / (abs(self.angle_bias) + 0.000001))
    max_bias_change *= interp(abs(angle_steers - live_params.angleOffsetAverage - self.angle_bias), [0.0, 5.0], [0.25, 1.0])
    max_bias_change *= interp(abs(path_plan.rateSteers), [0.0, 5.0], [0.25, 1.0])
    max_bias_change = max(0.0005, max_bias_change)
    self.angle_bias = float(np.clip(live_params.angleOffset - live_params.angleOffsetAverage, self.angle_bias - max_bias_change, self.angle_bias + max_bias_change))
    self.live_tune(CP)
    advance_angle = self.future_angle.update(v_ego, angle_steers - path_plan.angleOffset, angle_steers_rate, steering_torque, steer_override or not active)

    if v_ego < 0.3 or not active:
      output_steer = 0.0
      self.lane_changing = 0.0
      self.previous_integral = 0.0
      self.damp_angle_steers = 0.0
      self.damp_rate_steers_des = 0.0
      self.damp_angle_steers_des = 0.0
      pid_log.active = False
      self.pid.reset()
    else:
      self.angle_steers_des = path_plan.angleSteers
      if not self.driver_assist_hold:
        if len(live_mpc.delta) > 0 and (live_mpc.delta[2] - live_mpc.delta[1]) > 0 != (live_mpc.delta[19] - live_mpc.delta[1]) > 0 and abs(live_mpc.delta[19]) > abs(live_mpc.delta[2]):
          counter_steer = abs(live_mpc.delta[2] / live_mpc.delta[19])
        else:
          counter_steer = 1.0
        self.damp_angle_steers_des += counter_steer * (interp(sec_since_boot() + self.damp_mpc + self.react_mpc, path_plan.mpcTimes, path_plan.mpcAngles) - self.damp_angle_steers_des) / max(1.0, self.damp_mpc * 100.)
        self.damp_rate_steers_des += counter_steer * (interp(sec_since_boot() + self.damp_mpc + self.react_mpc, path_plan.mpcTimes, path_plan.mpcRates) - self.damp_rate_steers_des) / max(1.0, self.damp_mpc * 100.)
        self.damp_angle_steers += (angle_steers + self.damp_time * angle_steers_rate - self.damp_angle_steers) / max(1.0, self.damp_time * 100.)
      else:
        self.damp_angle_steers_des = self.damp_angle_steers + self.driver_assist_offset
        self.damp_angle_steers = angle_steers - self.angle_bias

      if steer_override and abs(self.damp_angle_steers) > abs(self.damp_angle_steers_des) and self.pid.saturated:
        self.damp_angle_steers_des = self.damp_angle_steers

      steers_max = get_steer_max(CP, v_ego)
      self.pid.pos_limit = steers_max
      self.pid.neg_limit = -steers_max
      angle_feedforward = float(self.damp_angle_steers_des - path_plan.angleOffset)
      self.angle_ff_ratio = interp(abs(angle_feedforward), self.angle_ff_bp[0], self.angle_ff_bp[1])
      rate_feedforward = (1.0 - self.angle_ff_ratio) * self.rate_ff_gain * self.damp_rate_steers_des
      steer_feedforward = float(v_ego)**2 * (rate_feedforward + angle_feedforward * self.angle_ff_ratio * self.angle_ff_gain)

      if CP.carName == "honda" and steer_override and not self.prev_override and not self.driver_assist_hold and self.pid.saturated and abs(angle_steers) < abs(self.damp_angle_steers_des) and not blinkers_on:
        self.driver_assist_hold = True
        self.driver_assist_offset = self.damp_angle_steers_des - self.damp_angle_steers
      else:
        self.driver_assist_hold = steer_override and self.driver_assist_hold

      self.path_error += (float(v_ego) * float(self.get_projected_path_error(v_ego, angle_feedforward, angle_steers, live_params, path_plan, VM)) \
                          * self.poly_factor * self.angle_ff_gain - self.path_error) / (self.poly_smoothing)
      if self.driver_assist_hold and not steer_override and abs(angle_steers) > abs(self.damp_angle_steers_des):
        driver_opposing_i = False

      driver_opposing_i = steer_override and self.pid.i * self.pid.p > 0 and not self.pid.saturated and not self.driver_assist_hold

      deadzone = 0.
      #if abs(self.damp_angle_steers_des) >= abs(self.damp_angle_steers):
      #  self.p_scale -= self.p_scale / 10.0
      #else:
      #  self.p_scale += (self.angle_ff_ratio - self.p_scale) / 10.0

      output_steer = self.pid.update(self.damp_angle_steers_des + self.path_error, self.damp_angle_steers + advance_angle - self.angle_bias, check_saturation=(v_ego > 10), override=driver_opposing_i,
                                     feedforward=steer_feedforward, speed=v_ego, deadzone=deadzone)  #, p_scale=self.p_scale)

      pid_log.active = True
      pid_log.p = float(self.pid.p)
      pid_log.i = float(self.pid.i)
      pid_log.f = float(self.pid.f)
      pid_log.p2 = float(self.pid._k_p[1][0]) * self.path_error
      pid_log.output = float(output_steer)
      pid_log.saturated = bool(self.pid.saturated)
      pid_log.angleFFRatio = self.angle_ff_ratio
      pid_log.angleBias = self.angle_bias

      if self.gernbySteer and not steer_override and v_ego > 10.0:
        if abs(angle_steers) > (self.angle_ff_bp[0][1] / 2.0):
          self.adjust_angle_gain()
        else:
          self.previous_integral = self.pid.i
    self.prev_angle_steers = angle_steers
    self.prev_override = steer_override
    self.sat_flag = self.pid.saturated
    return output_steer, float(self.angle_steers_des), pid_log
