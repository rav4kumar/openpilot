# functions common among cars
from common.numpy_fast import clip, interp


def dbc_dict(pt_dbc, radar_dbc, chassis_dbc=None):
  return {'pt': pt_dbc, 'radar': radar_dbc, 'chassis': chassis_dbc}


def apply_std_steer_torque_limits(apply_torque, apply_torque_last, driver_torque, LIMITS):

  # limits due to driver torque
  driver_max_torque = LIMITS.STEER_MAX + (LIMITS.STEER_DRIVER_ALLOWANCE + driver_torque * LIMITS.STEER_DRIVER_FACTOR) * LIMITS.STEER_DRIVER_MULTIPLIER
  driver_min_torque = -LIMITS.STEER_MAX + (-LIMITS.STEER_DRIVER_ALLOWANCE + driver_torque * LIMITS.STEER_DRIVER_FACTOR) * LIMITS.STEER_DRIVER_MULTIPLIER
  max_steer_allowed = max(min(LIMITS.STEER_MAX, driver_max_torque), 0)
  min_steer_allowed = min(max(-LIMITS.STEER_MAX, driver_min_torque), 0)
  apply_torque = clip(apply_torque, min_steer_allowed, max_steer_allowed)

  # slow rate if steer torque increases in magnitude
  if apply_torque_last > 0:
    apply_torque = clip(apply_torque, max(apply_torque_last - LIMITS.STEER_DELTA_DOWN, -LIMITS.STEER_DELTA_UP),
                                    apply_torque_last + LIMITS.STEER_DELTA_UP)
  else:
    apply_torque = clip(apply_torque, apply_torque_last - LIMITS.STEER_DELTA_UP,
                                    min(apply_torque_last + LIMITS.STEER_DELTA_DOWN, LIMITS.STEER_DELTA_UP))

  return int(round(apply_torque))


def apply_toyota_steer_torque_limits(apply_torque, apply_torque_last, motor_torque, LIMITS, angle_steers, angle_steers_des, angle_rate_des):

  starting_torque = apply_torque
  # limits due to comparison of commanded torque VS motor reported torque
  max_lim = min(max(motor_torque + LIMITS.STEER_ERROR_MAX, LIMITS.STEER_ERROR_MAX), LIMITS.STEER_MAX)
  min_lim = max(min(motor_torque - LIMITS.STEER_ERROR_MAX, -LIMITS.STEER_ERROR_MAX), -LIMITS.STEER_MAX)
  apply_torque = clip(apply_torque, min_lim, max_lim)

  '''delta_factor_up =  interp(abs(angle_steers - angle_steers_des), [0.5, 0.75, 1.15, 2.25, 3.75, 4.75], [1.0, 0.9, 0.8, 0.6, 0.45, 0.4 ])
  delta_factor_up = rate_factor

  delta_factor_down = interp(abs(angle_steers_des), [1.0, 1.5, 2.5, 4.0, 7.0, 12.0],[1.0, 0.85, 0.7, 0.55, 0.4, 0.3 ])
  delta_factor_down *= interp(abs(angle_steers - angle_steers_des), [0.0 ,0.2], [0.0, 1.0])
  delta_factor_down = rate_factor
  '''

  rate_factor = interp(abs(angle_rate_des), [0.0, 2.0], [1.0, 1.0])
  delta_up = LIMITS.STEER_DELTA_UP * rate_factor
  delta_down = LIMITS.STEER_DELTA_DOWN * rate_factor

  # slow rate if steer torque increases in magnitude
  if apply_torque_last > 0:
    apply_torque = clip(apply_torque,
                        max(apply_torque_last - delta_down, -delta_up),
                        apply_torque_last + delta_up)
  else:
    apply_torque = clip(apply_torque,
                        apply_torque_last - delta_up,
                        min(apply_torque_last + delta_down, delta_up))

  if starting_torque != apply_torque:  print("desired rate: %1.1f   angle error: % 1.1f  rate_factor:  %1.1f" % (angle_rate_des, angle_steers_des - angle_steers, rate_factor))   #, delta_factor_up, -delta_factor_down)


  return int(round(apply_torque))


def crc8_pedal(data):
  crc = 0xFF    # standard init value
  poly = 0xD5   # standard crc8: x8+x7+x6+x4+x2+1
  size = len(data)
  for i in range(size-1, -1, -1):
    crc ^= data[i]
    for j in range(8):
      if ((crc & 0x80) != 0):
        crc = ((crc << 1) ^ poly) & 0xFF
      else:
        crc <<= 1
  return crc


def create_gas_command(packer, gas_amount, idx):
  # Common gas pedal msg generator
  enable = gas_amount > 0.001

  values = {
    "ENABLE": enable,
    "COUNTER_PEDAL": idx & 0xF,
  }

  if enable:
    values["GAS_COMMAND"] = gas_amount * 255.
    values["GAS_COMMAND2"] = gas_amount * 255.

  dat = packer.make_can_msg("GAS_COMMAND", 0, values)[2]

  dat = [ord(i) for i in dat]
  checksum = crc8_pedal(dat[:-1])
  values["CHECKSUM_PEDAL"] = checksum

  return packer.make_can_msg("GAS_COMMAND", 0, values)
