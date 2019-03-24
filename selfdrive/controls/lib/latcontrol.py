from common.realtime import sec_since_boot
from selfdrive.controls.lib.pid import PIController
from common.numpy_fast import interp
from cereal import car

_DT = 0.01    # 100Hz


def get_steer_max(CP, v_ego):
  return interp(v_ego, CP.steerMaxBP, CP.steerMaxV)


class LatControl(object):
  def __init__(self, CP):

    self.mpc_frame = 0
    self.actual_projection = CP.steerDampenTime
    self.desired_projection = CP.steerMPCDampenTime
    self.actual_smoothing = max(1.0, self.actual_projection / _DT)
    self.desired_smoothing = max(1.0, (self.desired_projection - CP.steerMPCOffsetTime) / _DT)
    self.dampened_angle_steers = 0.0
    self.dampened_desired_angle = 0.0
    self.steer_counter = 1.0
    self.steer_counter_prev = 0.0
    self.rough_steers_rate = 0.0
    self.prev_angle_steers = 0.0
    self.calculate_rate = True

    KpV = [interp(25.0, CP.steerKpBP, CP.steerKpV)]
    KiV = [interp(25.0, CP.steerKiBP, CP.steerKiV)]
    self.pid = PIController(([0.], KpV),
                            ([0.], KiV),
                            k_f=CP.steerKf, pos_limit=1.0)

  def reset(self):
    self.pid.reset()

  def update(self, active, v_ego, angle_steers, angle_rate, steer_override, CP, VM, path_plan):

    if angle_rate == 0.0 and self.calculate_rate:
      if angle_steers != self.prev_angle_steers:
        self.steer_counter_prev = self.steer_counter
        self.rough_steers_rate = (self.rough_steers_rate + 100.0 * (angle_steers - self.prev_angle_steers) / self.steer_counter_prev) / 2.0
        self.steer_counter = 0.0
      elif self.steer_counter >= self.steer_counter_prev:
        self.rough_steers_rate = (self.steer_counter * self.rough_steers_rate) / (self.steer_counter + 1.0)
      self.steer_counter += 1.0
      angle_rate = self.rough_steers_rate
      self.prev_angle_steers = angle_steers
    else:
      # If non-zero angle_rate is provided, stop calculating rate
      self.calculate_rate = False

    if v_ego < 0.3 or not active:
      output_steer = 0.0
      self.pid.reset()
      self.dampened_angle_steers = angle_steers
      self.dampened_desired_angle = angle_steers
    else:
      projected_desired_angle = interp(sec_since_boot() + self.desired_projection, path_plan.mpcTimes, path_plan.mpcAngles)
      self.dampened_desired_angle = (((self.desired_smoothing - 1.) * self.dampened_desired_angle) + projected_desired_angle) / self.desired_smoothing

      if CP.steerControlType == car.CarParams.SteerControlType.torque:
        projected_angle_steers = float(angle_steers) + self.actual_projection * float(angle_rate)
        if not steer_override:
          self.dampened_angle_steers = (((self.actual_smoothing - 1.) * self.dampened_angle_steers) + projected_angle_steers) / self.actual_smoothing

        steers_max = get_steer_max(CP, v_ego)
        self.pid.pos_limit = steers_max
        self.pid.neg_limit = -steers_max
        deadzone = 0.0

        feed_forward = v_ego**2 * self.dampened_desired_angle
        output_steer = self.pid.update(self.dampened_desired_angle, self.dampened_angle_steers, check_saturation=(v_ego > 10),
                                      override=steer_override, feedforward=feed_forward, speed=v_ego, deadzone=deadzone)

    self.sat_flag = self.pid.saturated
    self.prev_angle_steers = angle_steers

    return output_steer, float(self.dampened_desired_angle)
