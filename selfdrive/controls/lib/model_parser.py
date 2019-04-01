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
    self.p_curv = 0.0
    self.c_prob = 0.
    self.last_model = 0.
    self.lead_dist, self.lead_prob, self.lead_var = 0, 0, 1
    self._path_pinv = compute_path_pinv()

    self.lane_width_estimate = 3.7
    self.lane_width_certainty = 1.0
    self.lane_width = 3.7
    self.l_prob = 0.
    self.r_prob = 0.

  def update(self, v_ego, md):
    if md is not None:
      p_poly = model_polyfit(md.model.path.points, self._path_pinv)  # predicted path
      l_poly = model_polyfit(md.model.leftLane.points, self._path_pinv)  # left line
      r_poly = model_polyfit(md.model.rightLane.points, self._path_pinv)  # right line

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
      lane_prob = interp(lane_width_diff, [0.2, 1.0], [1.0, 0.0])

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

      self.l_avg_poly[2] = ((9.0 * self.l_avg_poly[2]) + l_poly[2]) / 10.0
      self.r_avg_poly[2] = ((9.0 * self.r_avg_poly[2]) + r_poly[2]) / 10.0

      self.lead_dist = md.model.lead.dist
      self.lead_prob = md.model.lead.prob
      self.lead_var = md.model.lead.std**2

      # compute target path
      self.d_poly, self.c_poly, self.c_prob = calc_desired_path(
        l_poly, r_poly, p_poly, l_prob, r_prob, p_prob, v_ego, self.lane_width)

      self.r_poly = r_poly
      self.r_prob = r_prob

      self.l_poly = l_poly
      self.l_prob = l_prob

      self.p_poly = p_poly
      self.p_prob = p_prob
