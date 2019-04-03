import math
from common.numpy_fast import interp
from selfdrive.controls.lib.latcontrol_helpers import model_polyfit, calc_desired_path, compute_path_pinv, calc_poly_curvature

CAMERA_OFFSET = 0.06  # m from center car to camera


class ModelParser(object):
  def __init__(self):
    self.d_poly = [0., 0., 0., 0.]
    self.c_poly = [0., 0., 0., 0.]
    self.l_poly = [0., 0., 0., 0.]
    self.r_poly = [0., 0., 0., 0.]
    self.l_avg_poly = [0., 0., 0., 0.]
    self.r_avg_poly = [0., 0., 0., 0.]
    self.v_avg_curv = 0.0
    self.p_avg_curv_far = 0.0
    self.l_avg_curv_far = 0.0
    self.r_avg_curv_far = 0.0
    self.p_avg_curv_near = 0.0
    self.l_avg_curv_near = 0.0
    self.r_avg_curv_near = 0.0
    self.l_sum_avg = 0.0
    self.r_sum_avg = 0.0

    self.c_prob = 0.
    self.l_sum = 0
    self.p_sum = 0
    self.r_sum = 0
    self.last_model = 0.
    self.lead_dist, self.lead_prob, self.lead_var = 0, 0, 1
    self._path_pinv = compute_path_pinv()

    self.lane_width_estimate = 3.7
    self.lane_width_certainty = 1.0
    self.lane_width = 3.7
    self.l_prob = 0.
    self.r_prob = 0.
    self.lane_prob= 0.

  def update(self, v_ego, md, v_curv=0.0):
    if md is not None:
      p_poly = model_polyfit(md.model.path.points, self._path_pinv)  # predicted path
      l_poly = model_polyfit(md.model.leftLane.points, self._path_pinv)  # left line
      r_poly = model_polyfit(md.model.rightLane.points, self._path_pinv)  # right line

      '''
      #print(self._path_pinv[0:4][25:50])
      far_pinv = [self._path_pinv[0][25:50],self._path_pinv[1][25:50],self._path_pinv[2][25:50],self._path_pinv[3][25:50]]
      near_pinv = [self._path_pinv[0][0:30],self._path_pinv[1][0:30],self._path_pinv[2][0:30],self._path_pinv[3][0:30]]
      p_poly_far = model_polyfit(map(float, md.model.path.points)[25:50], far_pinv)  # predicted path
      l_poly_far = model_polyfit(map(float, md.model.leftLane.points)[25:50], far_pinv)  # left line
      r_poly_far = model_polyfit(map(float, md.model.rightLane.points)[25:50], far_pinv)  # right line

      p_poly_near = model_polyfit(map(float, md.model.path.points)[0:30], near_pinv)  # predicted path
      l_poly_near = model_polyfit(map(float, md.model.leftLane.points)[0:30], near_pinv)  # left line
      r_poly_near = model_polyfit(map(float, md.model.rightLane.points)[0:30], near_pinv)  # right line
      '''

      # only offset left and right lane lines; offsetting p_poly does not make sense
      l_poly[3] += CAMERA_OFFSET
      r_poly[3] += CAMERA_OFFSET

      p_prob = 1.  # model does not tell this probability yet, so set to 1 for now
      l_prob = md.model.leftLane.prob  # left line prob
      r_prob = md.model.rightLane.prob  # right line prob

      # Find current lanewidth
      lr_prob = l_prob * r_prob
      self.lane_width_certainty += 0.05 * (lr_prob - self.lane_width_certainty)
      current_lane_width = abs(l_poly[3] - r_poly[3])
      self.lane_width_estimate += 0.005 * (current_lane_width - self.lane_width_estimate)
      speed_lane_width = interp(v_ego, [0., 31.], [3., 3.8])
      self.lane_width = self.lane_width_certainty * self.lane_width_estimate + \
                        (1 - self.lane_width_certainty) * speed_lane_width

      lane_width_diff = abs(self.lane_width - current_lane_width)
      lane_prob = interp(lane_width_diff, [0.1, 0.5], [1.0, 0.0])


      '''
      l_divergence = (l_poly[2] - self.l_avg_poly[2])
      r_divergence = (self.r_avg_poly[2] - r_poly[2])
      self.p_curv = ((9.0 * self.p_curv) + calc_poly_curvature(p_poly)) / 10.0
      curv_prob = interp(abs(self.p_curv), [0.00001, 0.00005], [1.0, 0.0] )

      if (self.r_avg_poly[3] - r_poly[3]) > abs(l_poly[3] - self.l_avg_poly[3]):
        #print("   right lane_prob  %1.2f" % lane_prob)
        r_prob *= lane_prob
      elif (l_poly[3] - self.l_avg_poly[3]) > abs(self.r_avg_poly[3] - r_poly[3]):
        #print("   left lane_prob  %1.2f" % lane_prob)
        l_prob *= lane_prob

      if r_divergence > abs(l_divergence) and self.p_curv < 0:
        #print("   right curv prob  %1.2f" % curv_prob)
        r_prob *= curv_prob
        p_prob *= curv_prob
      elif l_divergence > abs(r_divergence) and self.p_curv > 0:
        #print("   left curv prob  %1.2f" % curv_prob)
        l_prob *= curv_prob
        p_prob *= curv_prob
      left = md.model.leftLane
      right = md.model.rightLane
      l_sum = left.points[0:10]
      r_sum = right.points[0:10]

      #l_diverging = (l_sum - self.l_sum_avg) > abs(r_sum - self.r_sum_avg) and (v_curv > self.v_avg_curv)
      #r_diverging = (self.l_sum_avg - r_sum) > abs(l_sum - self.l_sum_avg) and (v_curv < self.v_avg_curv)
      '''

      steer_compensation = v_curv * v_ego
      total_left_divergence = md.model.leftLane.points[5] - md.model.leftLane.points[0] + steer_compensation
      total_right_divergence = -(md.model.rightLane.points[5] - md.model.rightLane.points[0] + steer_compensation)

      if (total_left_divergence > abs(total_right_divergence) and (self.lane_prob > 0 or self.r_prob > 0)) or (self.lane_prob == 0 and self.l_prob == 0):
        l_prob *= lane_prob
        p_prob *= lane_prob # (1.0 - (1.0 - lane_prob) / 2.0)
        if lane_prob == 0.0:
          r_prob *= 1.5
      elif total_right_divergence > abs(total_left_divergence) or (self.lane_prob == 0 and self.r_prob == 0):
        r_prob *= lane_prob
        p_prob *= lane_prob # (1.0 - (1.0 - lane_prob) / 2.0)
        if lane_prob == 0.0:
          l_prob *= 1.5     #(1.0 + (1.0 - lane_prob))

      '''if lane_prob == 0 and self.l_prob == 0.0 and self.r_prob > 0.4 and r_prob > 0.4:
        l_prob = 0.0
      elif lane_prob == 0 and self.r_prob == 0.0 and self.l_prob > 0.4 and l_prob > 0.4:
        r_prob = 0.0
      '''

      '''if (l_curv_diff_far) > (l_curv_diff_near) or (v_curv > self.v_avg_curv and self.r_poly[3] > r_poly[3]) or self.l_prob == 0.0: # and left.std > right.std:
        l_prob *= lane_prob
        if (p_curv_diff_far) > (p_curv_diff_near):
          p_prob *= (1.0 - ((1.0 - lane_prob) / 2.0))
        print(l_prob, r_prob, p_prob)
      elif (r_curv_diff_far) < (r_curv_diff_near) or (v_curv < self.v_avg_curv and self.l_poly[3] < l_poly[3]): # and left.std < right.std:
        r_prob *= lane_prob
        if (p_curv_far - self.p_avg_curv_far) < (p_curv_far - self.p_avg_curv_near):
          p_prob *= (1.0 - ((1.0 - lane_prob) / 2.0))
        print("  right")
      elif (l_curv_near - self.l_avg_curv_near) > (r_curv_near - self.r_avg_curv_near): # and left.std > right.std:
        l_prob *= lane_prob
        if (p_curv_near - self.p_avg_curv_near) > (r_curv_near - self.r_avg_curv_near):
          p_prob *= (1.0 - ((1.0 - lane_prob) / 2.0))
        print(l_prob, r_prob, p_prob)
      elif (r_curv_near - self.r_avg_curv_near) < (l_curv_near - self.l_avg_curv_near): # and left.std < right.std:
        r_prob *= lane_prob
        if (r_curv_near - self.r_avg_curv_near) < (p_curv_near - self.p_avg_curv_near):
          p_prob *= (1.0 - ((1.0 - lane_prob) / 2.0))
        print("  right")


      #self.v_avg_curv += 0.25 * (v_curv - self.v_avg_curv)
      self.l_sum_avg += 0.25 * (l_sum - self.l_sum_avg)
      self.r_sum_avg += 0.25 * (r_sum - self.r_sum_avg)
      '''

      self.lead_dist = md.model.lead.dist
      self.lead_prob = md.model.lead.prob
      self.lead_var = md.model.lead.std**2

      # compute target path
      self.d_poly, self.c_poly, self.c_prob = calc_desired_path(
        l_poly, r_poly, p_poly, l_prob, r_prob, p_prob, v_ego, self.lane_width)

      self.lane_prob = lane_prob
      self.r_poly = r_poly
      self.r_prob = r_prob

      self.l_poly = l_poly
      self.l_prob = l_prob

      self.p_poly = p_poly
      self.p_prob = p_prob
