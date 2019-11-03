from common.numpy_fast import interp
from common.op_params import opParams


class LaneHugging:
  def __init__(self):
    self.op_params = opParams()
    self.lane_hug_direction = self.op_params.get('lane_hug_direction', None)  # if lane hugging is present and which side. None, 'left', or 'right'
    self.lane_hug_mod = self.op_params.get('lane_hug_mod', 1.2)  # how much to reduce angle by. float from 1.0 to 2.0
    self.lane_hug_angle = self.op_params.get('lane_hug_angle', 10)  # where to end increasing angle modification. from 0 to this

  def lane_hug(self, angle_steers):
    angle_steers_des = angle_steers
    if self.lane_hug_direction == 'left' and angle_steers > 0:
      angle_steers_des = angle_steers / interp(angle_steers, [0, self.lane_hug_angle], [1.0, self.lane_hug_mod])  # suggestion thanks to zorrobyte
    elif self.lane_hug_direction == 'right' and angle_steers < 0:
      angle_steers_des = angle_steers / interp(angle_steers, [0, self.lane_hug_angle], [1.0, self.lane_hug_mod])

    return angle_steers_des
