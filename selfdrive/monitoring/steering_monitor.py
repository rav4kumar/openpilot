from enum import Enum

from common.filter_simple import FirstOrderFilter
from common.realtime import DT_DMON

from cereal import car

from common.op_params import opParams
from common.travis_checker import travis
if not travis:
  awareness_factor = opParams().get('awareness_factor', default=1.0)
else:
  awareness_factor = 1

EventName = car.CarEvent.EventName

_PRESSED_FILTER_TS = 0.16  # 1Hz -> (1./0.16)rad/sec

_PRE_ALERT_THRESHOLD = 50 + awareness_factor * 600  # 5s
_PROMPT_ALERT_THRESHOLD = 150 + awareness_factor * 600  # 15s
_TERMINAL_ALERT_THRESHOLD = 300 + awareness_factor * 600  # 30s

MAX_TERMINAL_DURATION = 300 * awareness_factor  # 30s

class SteeringState(Enum):
  NOT_ACTIVE = 0
  HANDS_ON_WHEEL = 1
  HANDS_OFF_WHEEL = 2
  HANDS_OFF_WHEEL_PRE = 3
  HANDS_OFF_WHEEL_PROMPT = 4
  HANDS_OFF_WHEEL_TERMINAL = 5

class SteeringStatus():
  def __init__(self):
    self.steering_state = SteeringState.NOT_ACTIVE
    self.steering_pressed_filter = FirstOrderFilter(0., _PRESSED_FILTER_TS, DT_DMON)
    self.hands_off_wheel_cnt = 0

  def update(self, events, steering_pressed, ctrl_active, standstill):
    self.steering_pressed_filter.update(steering_pressed)

    if standstill or not ctrl_active:
      self.steering_state = SteeringState.NOT_ACTIVE
      self.hands_off_wheel_cnt = 0
      return

    is_steering_pressed = bool(round(self.steering_pressed_filter.x))

    if is_steering_pressed:
        self.steering_state = SteeringState.HANDS_ON_WHEEL
        self.hands_off_wheel_cnt = 0
        return

    self.hands_off_wheel_cnt += 1
    alert = None

    if self.hands_off_wheel_cnt >= _TERMINAL_ALERT_THRESHOLD:
      # terminal red alert: disengagement required
      self.steering_state = SteeringState.HANDS_OFF_WHEEL_TERMINAL
      alert = EventName.keepHandsOnWheel
    elif self.hands_off_wheel_cnt >= _PROMPT_ALERT_THRESHOLD:
      # prompt orange alert
      self.steering_state = SteeringState.HANDS_OFF_WHEEL_PROMPT
      alert = EventName.promptKeepHandsOnWheel
    elif self.hands_off_wheel_cnt >= _PRE_ALERT_THRESHOLD:
      # pre green alert
      self.steering_state = SteeringState.HANDS_OFF_WHEEL_PRE
      alert = EventName.preKeepHandsOnWheel
    else:
      self.steering_state = SteeringState.HANDS_OFF_WHEEL

    if alert is not None:
      events.add(alert)

  def current_steering_pressed(self):
    return self.steering_pressed_filter.x
