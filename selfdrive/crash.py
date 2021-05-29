"""Install exception handler for process crash."""
import os
import sys
import capnp
import requests
import traceback
from cereal import car
from common.params import Params
from selfdrive.version import version, dirty, origin, branch

from selfdrive.swaglog import cloudlog
from selfdrive.version import version

import sentry_sdk
from sentry_sdk.integrations.threading import ThreadingIntegration
from common.op_params import opParams
from datetime import datetime

def save_exception(exc_text):
  COMMUNITY_DIR = '/data/community'
  CRASHES_DIR = '{}/crashes'.format(COMMUNITY_DIR)

  if not os.path.exists(COMMUNITY_DIR):
    os.mkdir(COMMUNITY_DIR)
  if not os.path.exists(CRASHES_DIR):
    os.mkdir(CRASHES_DIR)
  i = 0
  log_file = '{}/{}'.format(CRASHES_DIR, datetime.now().strftime('%Y-%m-%d--%H-%M-%S.%f.log')[:-3])
  if os.path.exists(log_file):
    while os.path.exists(log_file + str(i)):
      i += 1
    log_file += str(i)
  with open(log_file, 'w') as f:
    f.write(exc_text)
  print('Logged current crash to {}'.format(log_file))

ret = car.CarParams.new_message()
candidate = ret.carFingerprint

params = Params()
op_params = opParams()
awareness_factor = op_params.get('awareness_factor')
alca_min_speed = op_params.get('alca_min_speed')
alca_nudge_required = op_params.get('alca_nudge_required')
ArizonaMode = op_params.get('ArizonaMode')
dynamic_follow_mod = op_params.get('dynamic_follow_mod')
dynamic_gas_mod = op_params.get('dynamic_gas_mod')
global_df_mod = op_params.get('global_df_mod')
keep_openpilot_engaged = op_params.get('keep_openpilot_engaged')
min_TR = op_params.get('min_TR')
physical_buttons_DF = op_params.get('physical_buttons_DF')
prius_pid = op_params.get('prius_pid')
username = op_params.get('username')
use_car_caching = op_params.get('use_car_caching')
#uniqueID = op_params.get('uniqueID')
try:
  dongle_id = params.get("DongleId").decode('utf8')
except AttributeError:
  dongle_id = "None"
try:
  ip = requests.get('https://checkip.amazonaws.com/').text.strip()
except Exception:
  ip = "255.255.255.255"
error_tags = {'dirty': dirty, 'dongle_id': dongle_id, 'branch': branch, 'remote': origin,
              'awareness_factor': awareness_factor, 'alca_min_speed': alca_min_speed, 'alca_nudge_required': alca_nudge_required,
              'ArizonaMode': ArizonaMode, 'dynamic_follow_mod': dynamic_follow_mod, 'dynamic_gas_mod': dynamic_gas_mod,
              'global_df_mod': global_df_mod, 'keep_openpilot_engaged': keep_openpilot_engaged, 'min_TR': min_TR,
              'physical_buttons_DF': physical_buttons_DF, 'prius_pid': prius_pid, 'use_car_caching': use_car_caching,
              'username': username, 'fingerprintedAs': candidate}
if username is None or not isinstance(username, str):
  username = 'undefined'
  #error_tags['uniqueID'] = uniqueID
error_tags['username'] = username

u_tag = []
if isinstance(username, str):
  u_tag.append(username)
if len(u_tag) > 0:
  error_tags['username'] = ''.join(u_tag)
for k, v in error_tags.items():
  sentry_sdk.set_tag(k, v)

def capture_exception(*args, **kwargs):
  save_exception(traceback.format_exc())
  exc_info = sys.exc_info()
  if not exc_info[0] is capnp.lib.capnp.KjException:
    sentry_sdk.capture_exception(*args, **kwargs)
    sentry_sdk.flush()  # https://github.com/getsentry/sentry-python/issues/291
  cloudlog.error("crash", exc_info=kwargs.get('exc_info', 1))

def bind_user(**kwargs):
    sentry_sdk.set_user(kwargs)

def capture_warning(warning_string):
  bind_user(id=dongle_id, ip_address=ip, username=username)
  sentry_sdk.capture_message(warning_string, level='warning')

def capture_info(info_string):
  bind_user(id=dongle_id, ip_address=ip, username=username)
  sentry_sdk.capture_message(info_string, level='info')

def bind_extra(**kwargs):
  for k, v in kwargs.items():
    sentry_sdk.set_tag(k, v)
def init():
  sentry_sdk.init("https://137e8e621f114f858f4c392c52e18c6d:8aba82f49af040c8aac45e95a8484970@sentry.io/1404547",
                  default_integrations=False, integrations=[ThreadingIntegration(propagate_hub=True)],
                  release=version)
  sentry_sdk.utils.MAX_STRING_LENGTH = 2048
