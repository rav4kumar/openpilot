#!/usr/bin/env python3
# type: ignore

import os
import argparse
import signal
import sys
import math

import cereal.messaging as messaging
from selfdrive.monitoring.steering_monitor import SteeringStatus
from selfdrive.controls.lib.events import Events

def sigint_handler(signal, frame):
  print("handler!")
  exit(0)
signal.signal(signal.SIGINT, sigint_handler)

def status_monitor():
  # use driverState socker to drive timing.
  driverState = messaging.sub_sock('driverState', addr=args.addr, conflate=True)
  sm = messaging.SubMaster(['carState', 'dMonitoringState'], addr=args.addr)
  steering_status = SteeringStatus()

  while messaging.recv_one(driverState):
    try:
      sm.update()

      # Get status and steering pressed value from our own instance of SteeringStatus
      steering_status.update(Events(), sm['carState'].steeringPressed, sm['carState'].cruiseState.enabled, sm['carState'].standstill)
      steering_value = int(math.floor(steering_status.current_steering_pressed() * 9.99))
      plot_list = ['-' for i in range(10)]
      plot_list[steering_value] = '+'

      # Get events from `dMonitoringState`
      events = sm['dMonitoringState'].events
      event_name = events[0].name if len(events) else "None"

      # Print output
      sys.stdout.write(f'\rsteering Pressed -> {"".join(plot_list)} | state: {steering_status.steering_state.name} | event: {event_name}')
      sys.stdout.flush()

    except Exception as e:
      print(e)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Sniff a communcation socket')
  parser.add_argument('--addr', default='127.0.0.1')
  parser.add_argument('--type', default='status')
  args = parser.parse_args()

  if args.addr != "127.0.0.1":
    os.environ["ZMQ"] = "1"
    messaging.context = messaging.Context()

  status_monitor()
