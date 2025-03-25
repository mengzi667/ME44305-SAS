# Note that run on salabim 24.0.16

import salabim as sim

import numpy as np
import random

# import pandas as pd
import matplotlib.pyplot as plt

# from tqdm import tqdm

# Parameters
vessel_IAT_mean = 2 * 60  # hours of IAT
vessel_time_enter = 0.5 * 60  # 0.5 hours of entering station
vessel_time_leave = 0.5 * 60  # 0.5 hours of leaving station
vessel_demand = 100  # 100 unit of demand for ammonia
vessel_gen = 0  # number of generated vessels
vessel_size = 10  # in total 10 vessels
station_speed = [10, 25]  # low- and high-speed refueling
station_num = 2  # number of stations
station_timestep = 50  # each timestep of 5 minutes for station


class VesselGenerator(sim.Component):
    def __init__(self, generator_id=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generator_id = generator_id

    def process(self):
        global vessel_gen
        while vessel_gen < vessel_size:
            vessels.append(Vessel(vessel_gen))
            vessel_gen += 1
            self.hold(sim.Exponential(vessel_IAT_mean).sample())


class Vessel(sim.Component):
    def __init__(self, vessel_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vessel_id = vessel_id
        self.demand = vessel_demand
        self.vessel_status = -1
        self.flag_enter = 0
        self.timeline = [(env.now(), -1, vessel_demand)]
        # vessel status: -1 - generated and enter queue;
        # nonegative integer - assigned station id;
        # -2 - refueling finished

    def process(self):
        if self.vessel_status == -1:
            if v_con.ispassive():
                self.enter(v_con.bunkering_queue)
                v_con.activate()
                self.passivate()
        if self.vessel_status >= 0:
            self.timeline.append((env.now(), self.vessel_status, self.demand))
            if self.flag_enter == 0:
                self.hold(vessel_time_enter)
                self.flag_enter = 1
                stations[self.vessel_status].activate()
                self.timeline.append((env.now(), self.vessel_status, self.demand))
                self.passivate()
            if self.demand <= 0:
                self.vessel_status = -2
                self.timeline.append((env.now(), -2, 0))
                self.hold(vessel_time_leave)
                self.timeline.append((env.now(), -2, 0))


class VesselControl(sim.Component):
    def __init__(self, control_id=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.control_id = control_id
        self.bunkering_queue = sim.Queue(f"VConQueue")

    def process(self):
        while True:
            # check if there is empty station and waiting vessel, if not both stay passive
            station_empty_id = -1
            for i in range(len(stations)):
                if stations[i].station_status == -1:
                    station_empty_id = i  # find the first empty station
                    break
            if station_empty_id < 0 or len(self.bunkering_queue) == 0:
                self.passivate()
                continue
            if station_empty_id >= 0 and len(self.bunkering_queue) > 0:
                print(
                    "Vessel %d assigned to Station %d"
                    % (self.bunkering_queue[0].vessel_id, station_empty_id)
                )
                self.bunkering_queue[0].activate()
                self.bunkering_queue[0].vessel_status = stations[
                    station_empty_id
                ].station_id
                stations[station_empty_id].station_status = self.bunkering_queue[
                    0
                ].vessel_id
                self.bunkering_queue.pop()


class Station(sim.Component):
    def __init__(self, station_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.station_id = station_id
        self.station_status = -1
        # status -1: empty; nonnegative integers: assigned vessel id

    def process(self):
        while True:
            while self.station_status == -1:
                self.passivate()
            print(
                "Station %d is working on vessel %d"
                % (self.station_id, self.station_status)
            )
            if self.station_status >= 0:
                self.hold(station_timestep)
                vessels[self.station_status].demand -= station_speed[0]
                vessels[self.station_status].timeline.append(
                    (env.now(), self.station_id, vessels[self.station_status].demand)
                )
                print("VesselDEMAND %.3f" % vessels[self.station_status].demand)
                if vessels[self.station_status].demand <= 0:
                    vessels[self.station_status].activate()
                    self.station_status = -1
                    v_con.activate()


# Simulation
env = sim.Environment(time_unit="minutes")
env = sim.Environment(trace="True")
v_gen = VesselGenerator()
v_con = VesselControl()
stations = [Station(i) for i in range(station_num)]
vessels = []
env.run()
# v_con.bunkering_queue.print_info()

# Output
for vessel in vessels:
#     print(vessel.timeline)
    plt.plot(
        [vessel.timeline[i][0] for i in range(len(vessel.timeline))],
        [vessel.timeline[i][2] for i in range(len(vessel.timeline))],
    )
plt.grid()
plt.xlabel("Time [s]")
plt.ylabel("Demand")
plt.show()

