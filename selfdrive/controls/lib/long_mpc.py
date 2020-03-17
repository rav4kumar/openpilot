import os
import math
import time

import cereal.messaging as messaging
import cereal.messaging_arne as messaging_arne
from selfdrive.swaglog import cloudlog
from common.realtime import sec_since_boot
from selfdrive.controls.lib.radar_helpers import _LEAD_ACCEL_TAU
from selfdrive.controls.lib.longitudinal_mpc import libmpc_py
from selfdrive.controls.lib.drive_helpers import MPC_COST_LONG
from common.op_params import opParams
from common.numpy_fast import interp, clip
from common.travis_checker import travis
from selfdrive.config import Conversions as CV

LOG_MPC = os.environ.get('LOG_MPC', False)


class LongitudinalMpc():
  def __init__(self, mpc_id):
    self.mpc_id = mpc_id
    self.op_params = opParams()

    self.setup_mpc()
    self.v_mpc = 0.0
    self.v_mpc_future = 0.0
    self.a_mpc = 0.0
    self.v_cruise = 0.0
    self.prev_lead_status = False
    self.prev_lead_x = 0.0
    self.new_lead = False
    self.TR_Mod = 0
    self.last_cloudlog_t = 0.0
    
    if not travis and mpc_id == 1:
      self.pm = messaging_arne.PubMaster(['smiskolData'])
    else:
      self.pm = None
    self.car_data = {'v_ego': 0.0, 'a_ego': 0.0}
    self.lead_data = {'v_lead': None, 'x_lead': None, 'a_lead': None, 'status': False}
    self.df_data = {"v_leads": [], "v_egos": []}  # dynamic follow data
    self.last_cost = 0.0
    self.df_profile = self.op_params.get('dynamic_follow', 'relaxed').strip().lower()
    self.sng = False

  def send_mpc_solution(self, pm, qp_iterations, calculation_time):
    qp_iterations = max(0, qp_iterations)
    dat = messaging.new_message('liveLongitudinalMpc')
    dat.liveLongitudinalMpc.xEgo = list(self.mpc_solution[0].x_ego)
    dat.liveLongitudinalMpc.vEgo = list(self.mpc_solution[0].v_ego)
    dat.liveLongitudinalMpc.aEgo = list(self.mpc_solution[0].a_ego)
    dat.liveLongitudinalMpc.xLead = list(self.mpc_solution[0].x_l)
    dat.liveLongitudinalMpc.vLead = list(self.mpc_solution[0].v_l)
    dat.liveLongitudinalMpc.cost = self.mpc_solution[0].cost
    dat.liveLongitudinalMpc.aLeadTau = self.a_lead_tau
    dat.liveLongitudinalMpc.qpIterations = qp_iterations
    dat.liveLongitudinalMpc.mpcId = self.mpc_id
    dat.liveLongitudinalMpc.calculationTime = calculation_time
    pm.send('liveLongitudinalMpc', dat)

  def setup_mpc(self):
    ffi, self.libmpc = libmpc_py.get_libmpc(self.mpc_id)
    self.libmpc.init(MPC_COST_LONG.TTC, MPC_COST_LONG.DISTANCE,
                     MPC_COST_LONG.ACCELERATION, MPC_COST_LONG.JERK)

    self.mpc_solution = ffi.new("log_t *")
    self.cur_state = ffi.new("state_t *")
    self.cur_state[0].v_ego = 0
    self.cur_state[0].a_ego = 0
    self.a_lead_tau = _LEAD_ACCEL_TAU

  def set_cur_state(self, v, a):
    self.cur_state[0].v_ego = v
    self.cur_state[0].a_ego = a
    
  def get_TR(self, CS):
    if not self.lead_data['status'] or travis:
      TR = 1.8
    elif CS.vEgo < 5.0:
      TRs = [2.0, 1.8, 1.75, 1.6]
      vEgos = [2.0, 3.0, 4.0, 5.0]
      #TRs = [1.8, 1.6]
      #vEgos =[4.0, 5.0]
      TR = interp(CS.vEgo, vEgos, TRs)
      p_mod_pos = 1.0
      p_mod_neg = 1.0
      TR_mod = []
      x = [-20.0383, -15.6978, -11.2053, -7.8781, -5.0407, -3.2167, -1.6122, 0.0]  # relative velocity values
      y = [0.641, 0.506, 0.418, 0.334, 0.24, 0.115, 0.055, 0.01]  # modification values
      TR_mod.append(interp(self.lead_data['v_lead'] - self.car_data['v_ego'], x, y))

      x = [-4.4795, -2.8122, -1.5727, -1.1129, -0.6611, -0.2692, 0.0]  # lead acceleration values
      y = [0.265, 0.187, 0.096, 0.057, 0.033, 0.024, 0.0]  # modification values
      TR_mod.append(interp(self.calculate_lead_accel(), x, y))
      
      self.TR_Mod = sum([mod * p_mod_neg if mod < 0 else mod * p_mod_pos for mod in TR_mod]) # calculate TR_Mod so that the cost function works correctly
      
    else:
      self.store_df_data()
      TR = self.dynamic_follow(CS)

    if not travis:
      self.change_cost(TR,CS.vEgo)
      self.send_cur_TR(TR)
    return TR

  def send_cur_TR(self, TR):
    if self.mpc_id == 1 and self.pm is not None:
      dat = messaging_arne.new_message()
      dat.init('smiskolData')
      dat.smiskolData.mpcTR = TR
      self.pm.send('smiskolData', dat)

  def change_cost(self, TR, vEgo):
    TRs = [0.9, 1.8, 2.7]
    costs = [0.3, 0.1, 0.05]
    cost = interp(TR, TRs, costs)
    if vEgo < 5.0:
      cost = 0.1
      cost = cost * min(max(1.0 , (6.0 - vEgo)),5.0) 
    if self.TR_Mod > 0:
      cost = cost + self.TR_Mod/2.0
    if self.last_cost != cost:
      self.libmpc.change_tr(MPC_COST_LONG.TTC, cost, MPC_COST_LONG.ACCELERATION, MPC_COST_LONG.JERK)
      self.last_cost = cost

  def store_df_data(self):
    v_lead_retention = 1.9  # keep only last x seconds
    v_ego_retention = 2.5

    cur_time = time.time()
    if self.lead_data['status']:
      self.df_data['v_leads'] = [sample for sample in self.df_data['v_leads'] if
                                 cur_time - sample['time'] <= v_lead_retention
                                 and not self.new_lead]  # reset when new lead
      self.df_data['v_leads'].append({'v_lead': self.lead_data['v_lead'], 'time': cur_time})

    self.df_data['v_egos'] = [sample for sample in self.df_data['v_egos'] if cur_time - sample['time'] <= v_ego_retention]
    self.df_data['v_egos'].append({'v_ego': self.car_data['v_ego'], 'time': cur_time})

  def calculate_lead_accel(self):
    min_consider_time = 1.0  # minimum amount of time required to consider calculation
    a_lead = self.lead_data['a_lead']
    if len(self.df_data['v_leads']):  # if not empty
      elapsed = self.df_data['v_leads'][-1]['time'] - self.df_data['v_leads'][0]['time']
      if elapsed > min_consider_time:  # if greater than min time (not 0)
        a_calculated = (self.df_data['v_leads'][-1]['v_lead'] - self.df_data['v_leads'][0]['v_lead']) / elapsed  # delta speed / delta time
        # old version: # if abs(a_calculated) > abs(a_lead) and a_lead < 0.33528:  # if a_lead is greater than calculated accel (over last 1.5s, use that) and if lead accel is not above 0.75 mph/s
        #   a_lead = a_calculated

        # long version of below: if (a_calculated < 0 and a_lead >= 0 and a_lead < -a_calculated * 0.5) or (a_calculated > 0 and a_lead <= 0 and -a_lead > a_calculated * 0.5) or (a_lead * a_calculated > 0 and abs(a_calculated) > abs(a_lead)):
        if (a_calculated < 0 <= a_lead < -a_calculated * 0.55) or (a_calculated > 0 >= a_lead and -a_lead < a_calculated * 0.45) or (a_lead * a_calculated > 0 and abs(a_calculated) > abs(a_lead)):  # this is a mess, fix
          a_lead = a_calculated
    return a_lead  # if above doesn't execute, we'll return a_lead from radar

  def dynamic_follow(self, CS):
    self.df_profile = self.op_params.get('dynamic_follow', 'relaxed').strip().lower()
    x_vel = [5.0, 7.4507, 9.3133, 11.5598, 13.645, 22.352, 31.2928, 33.528, 35.7632, 40.2336]  # velocities
    p_mod_x = [3, 20, 35]  # profile mod speeds
    if self.df_profile == 'roadtrip':
      y_dist = [1.6, 1.4507, 1.4837, 1.5327, 1.553, 1.581, 1.617, 1.653, 1.687, 1.74]  # TRs
      p_mod_pos = [0.99, 0.815, 0.57]
      p_mod_neg = [1.0, 1.27, 1.675]
    elif self.df_profile == 'traffic':  # for in congested traffic
      x_vel = [5.0, 7.4507, 9.3133, 11.5598, 13.645, 17.8816, 22.407, 28.8833, 34.8691, 40.3906]
      y_dist = [1.6, 1.437, 1.468, 1.501, 1.506, 1.38, 1.2216, 1.085, 1.0516, 1.016]
      p_mod_pos = [1.015, 2.175, 3.65]
      p_mod_neg = [0.98, 0.08, 0.0]
      # y_dist = [1.384, 1.391, 1.403, 1.415, 1.437, 1.3506, 1.3959, 1.4156, 1.38, 1.1899, 1.026, 0.9859, 0.9432]  # from 071-2 (need to fix FCW)
      # p_mod_pos = [1.015, 2.2, 3.95]
      # p_mod_neg = [0.98, 0.1, 0.0]
    else:  # default to relaxed/stock
      y_dist = [1.6, 1.444, 1.474, 1.516, 1.534, 1.546, 1.568, 1.579, 1.593, 1.614]
      p_mod_pos = [1.0, 1.0, 1.0]
      p_mod_neg = [1.0, 1.0, 1.0]

    p_mod_pos = interp(self.car_data['v_ego'], p_mod_x, p_mod_pos)
    p_mod_neg = interp(self.car_data['v_ego'], p_mod_x, p_mod_neg)

    sng_TR = 1.7  # reacceleration stop and go TR
    sng_speed = 15.0 * CV.MPH_TO_MS

    if self.car_data['v_ego'] > sng_speed:  # keep sng distance until we're above sng speed again
      self.sng = False

    if (self.car_data['v_ego'] >= sng_speed or self.df_data['v_egos'][0]['v_ego'] >= self.car_data['v_ego']) and not self.sng:  # if above 15 mph OR we're decelerating to a stop, keep shorter TR. when we reaccelerate, use sng_TR and slowly decrease
      TR = interp(self.car_data['v_ego'], x_vel, y_dist)
    else:  # this allows us to get closer to the lead car when stopping, while being able to have smooth stop and go when reaccelerating
      self.sng = True
      x = [sng_speed / 3.0, sng_speed]  # decrease TR between 5 and 15 mph from 1.8s to defined TR above at 15mph while accelerating
      y = [sng_TR, interp(sng_speed, x_vel, y_dist)]
      TR = interp(self.car_data['v_ego'], x, y)

    TR_mod = []
    # Dynamic follow modifications (the secret sauce)
    x = [-20.0383, -15.6978, -11.2053, -7.8781, -5.0407, -3.2167, -1.6122, 0.0, 0.6847, 1.3772, 1.9007, 2.7452]  # relative velocity values
    y = [0.641, 0.506, 0.418, 0.334, 0.24, 0.115, 0.055, 0.0, -0.03, -0.068, -0.142, -0.221]  # modification values
    TR_mod.append(interp(self.lead_data['v_lead'] - self.car_data['v_ego'], x, y))

    x = [-4.4795, -2.8122, -1.5727, -1.1129, -0.6611, -0.2692, 0.0, 0.1466, 0.5144, 0.6903, 0.9302]  # lead acceleration values
    y = [0.265, 0.187, 0.096, 0.057, 0.033, 0.024, 0.0, -0.009, -0.042, -0.053, -0.059]  # modification values
    TR_mod.append(interp(self.calculate_lead_accel(), x, y))

    # x = [4.4704, 22.352]  # 10 to 50 mph  #todo: remove if uneeded/unsafe
    # y = [0.94, 1.0]
    # TR_mod *= interp(self.car_data['v_ego'], x, y)  # modify TR less at lower speeds

    self.TR_Mod = sum([mod * p_mod_neg if mod < 0 else mod * p_mod_pos for mod in TR_mod])  # alter TR modification according to profile
    TR += self.TR_Mod

    if CS.leftBlinker or CS.rightBlinker and self.df_profile != 'traffic':
      x = [8.9408, 22.352, 31.2928]  # 20, 50, 70 mph
      y = [1.0, .75, .65]  # reduce TR when changing lanes
      TR *= interp(self.car_data['v_ego'], x, y)

    # TR *= self.get_traffic_level()  # modify TR based on last minute of traffic data  # todo: look at getting this to work, a model could be used

    return clip(TR, 0.9, 2.7)

  def process_lead(self, v_lead, a_lead, x_lead, status):
    self.lead_data['v_lead'] = v_lead
    self.lead_data['a_lead'] = a_lead
    self.lead_data['x_lead'] = x_lead
    self.lead_data['status'] = status

  # def get_traffic_level(self, lead_vels):  # generate a value to modify TR by based on fluctuations in lead speed
  #   if len(lead_vels) < 60:
  #     return 1.0  # if less than 30 seconds of traffic data do nothing to TR
  #   lead_vel_diffs = []
  #   for idx, vel in enumerate(lead_vels):
  #     try:
  #       lead_vel_diffs.append(abs(vel - lead_vels[idx - 1]))
  #     except:
  #       pass
  #
  #   x = [0, len(lead_vels)]
  #   y = [1.15, .9]  # min and max values to modify TR by, need to tune
  #   traffic = interp(sum(lead_vel_diffs), x, y)
  #
  #   return traffic

  def update(self, pm, CS, lead, v_cruise_setpoint):
    v_ego = CS.vEgo
    self.car_data = {'v_ego': CS.vEgo, 'a_ego': CS.aEgo}
    # Setup current mpc state
    self.cur_state[0].x_ego = 0.0

    if lead is not None and lead.status:
      x_lead = lead.dRel
      v_lead = max(0.0, lead.vLead)
      a_lead = lead.aLeadK

      if (v_lead < 0.1 or -a_lead / 2.0 > v_lead):
        v_lead = 0.0
        a_lead = 0.0
      self.process_lead(v_lead, a_lead, x_lead, lead.status)
      self.a_lead_tau = lead.aLeadTau
      self.new_lead = False
      if not self.prev_lead_status or abs(x_lead - self.prev_lead_x) > 2.5:
        self.libmpc.init_with_simulation(self.v_mpc, x_lead, v_lead, a_lead, self.a_lead_tau)
        self.new_lead = True

      self.prev_lead_status = True
      self.prev_lead_x = x_lead
      self.cur_state[0].x_l = x_lead
      self.cur_state[0].v_l = v_lead
    else:
      self.process_lead(None, None, None, False)
      self.prev_lead_status = False
      # Fake a fast lead car, so mpc keeps running
      self.cur_state[0].x_l = 50.0
      self.cur_state[0].v_l = v_ego + 10.0
      a_lead = 0.0
      self.a_lead_tau = _LEAD_ACCEL_TAU

    # Calculate mpc
    t = sec_since_boot()
    n_its = self.libmpc.run_mpc(self.cur_state, self.mpc_solution, self.a_lead_tau, a_lead, self.get_TR(CS))
    duration = int((sec_since_boot() - t) * 1e9)

    if LOG_MPC:
      self.send_mpc_solution(pm, n_its, duration)

    # Get solution. MPC timestep is 0.2 s, so interpolation to 0.05 s is needed
    self.v_mpc = self.mpc_solution[0].v_ego[1]
    self.a_mpc = self.mpc_solution[0].a_ego[1]
    self.v_mpc_future = self.mpc_solution[0].v_ego[10]

    # Reset if NaN or goes through lead car
    crashing = any(lead - ego < -50 for (lead, ego) in zip(self.mpc_solution[0].x_l, self.mpc_solution[0].x_ego))
    nans = any(math.isnan(x) for x in self.mpc_solution[0].v_ego)
    backwards = min(self.mpc_solution[0].v_ego) < -0.01

    if ((backwards or crashing) and self.prev_lead_status) or nans:
      if t > self.last_cloudlog_t + 5.0:
        self.last_cloudlog_t = t
        cloudlog.warning("Longitudinal mpc %d reset - backwards: %s crashing: %s nan: %s" % (
                          self.mpc_id, backwards, crashing, nans))

      self.libmpc.init(MPC_COST_LONG.TTC, MPC_COST_LONG.DISTANCE,
                       MPC_COST_LONG.ACCELERATION, MPC_COST_LONG.JERK)
      self.cur_state[0].v_ego = v_ego
      self.cur_state[0].a_ego = 0.0
      self.v_mpc = v_ego
      self.a_mpc = CS.aEgo
      self.prev_lead_status = False
