# Note that run on salabim 24.0.16

import salabim as sim

import numpy as np
import random

# import pandas as pd
import matplotlib.pyplot as plt

# from tqdm import tqdm

# Parameters
vessel_IAT_mean = 1.5 * 60  # hours of IAT
vessel_time_enter = 0.5 * 60  # 0.5 hours of entering station
vessel_time_leave = 0.5 * 60  # 0.5 hours of leaving station
vessel_demand = 100  # 100 unit of demand for ammonia
vessel_size = 10  # in total 10 vessels
station_num = 3  # number of stations
station_speed = [4, 6]  # low- and high-speed refueling (just for debugging)
station_extra_speed = 2  # the extra speed provided by substorage
station_timestep = 10  # each timestep of 5 minutes for station
station_substorage_capacity = 20  # capacity of substorage
converter_intput_max = 10
converter_output_max_per_station = 4
main_storage_level = min(
    vessel_demand * vessel_size + station_num * station_substorage_capacity, 5e4
)
main_storage_timeline = [(0, main_storage_level)]


class VesselGenerator(sim.Component):
    def __init__(self, generator_id=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generator_id = generator_id
        self.vessel_gen = 0  # number of generated vessels

    def process(self):
        while self.vessel_gen < vessel_size:
            vessels.append(Vessel(self.vessel_gen))
            self.vessel_gen += 1
            self.hold(sim.Exponential(vessel_IAT_mean).sample())
            # self.hold(vessel_IAT_mean)


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
            self.enter(v_con.bunkering_queue)
            if v_con.ispassive():
                v_con.activate()
            self.passivate()
        if self.vessel_status >= 0:
            print(
                "Vessel %d assigned to Station %d"
                % (self.vessel_id, self.vessel_status)
            )
            self.timeline.append((env.now(), self.vessel_status, self.demand))
            if self.flag_enter == 0:
                self.hold(vessel_time_enter)
                self.flag_enter = 1
                print(
                    "Vessel %d arrives at Station %d"
                    % (self.vessel_id, self.vessel_status)
                )
                stations[self.vessel_status].station_status = self.vessel_id
                stations[self.vessel_status].activate()
                self.timeline.append((env.now(), self.vessel_status, self.demand))
                self.passivate()
            if self.demand <= 0:
                v_con.station_busy_flag[self.vessel_status] = 0
                v_con.activate()
                self.vessel_status = -2
                self.timeline.append((env.now(), -2, 0))
                self.hold(vessel_time_leave)
                self.timeline.append((env.now(), -2, 0))


class VesselControl(sim.Component):
    def __init__(self, control_id=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.control_id = control_id
        self.bunkering_queue = sim.Queue(f"VConQueue")
        self.station_busy_flag = [0 for i in range(station_num)]
        # 0 for empty stations, 1 for busy ones

    def process(self):
        while True:
            # check if there is empty station and waiting vessel, if not both stay passive
            station_empty_id = -1
            for i in range(station_num):
                if self.station_busy_flag[i] == 0:
                    station_empty_id = i  # find the first empty station
                    break
            if station_empty_id < 0 or len(self.bunkering_queue) == 0:
                self.passivate()
                continue
            if station_empty_id >= 0 and len(self.bunkering_queue) > 0:
                print(
                    "Vessel %d is to be allocated" % self.bunkering_queue[0].vessel_id
                )
                self.station_busy_flag[station_empty_id] = 1
                self.bunkering_queue[0].vessel_status = stations[
                    station_empty_id
                ].station_id
                self.bunkering_queue[0].activate()
                self.bunkering_queue.pop()


class Station(sim.Component):
    def __init__(self, station_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.station_id = station_id
        self.station_status = -1
        # status -1: empty; nonnegative integers: assigned vessel id
        self.substorage_level = station_substorage_capacity
        # initially the substorage is full
        self.refuel_speed_flag = (
            -1
        )  # 0 for no substorage acceleration; 1 for substorage acceleration; -1 for N/A
        self.timeline = [(env.now(), -1, -1, station_substorage_capacity)]
        # time, station_status, refuel_speed_flag, substorage_level
        self.flow_from_converter = 0

    def process(self):
        while True:
            if self.station_status == -1:
                self.refuel_speed_flag = -1
                if self.substorage_level >= station_substorage_capacity:
                    self.substorage_level = station_substorage_capacity
                    s_converter.station_demand_flag[self.station_id] = 0
                    self.passivate()
                    self.timeline.append(
                        (env.now(), self.station_status, -1, self.substorage_level)
                    )
                else:
                    s_converter.station_demand_flag[self.station_id] = 1
                    s_converter.activate()
                    self.passivate()
                    print("Station %d is refueling its substorage" % self.station_id)
                    self.hold(station_timestep)
                    self.substorage_level += self.flow_from_converter
                    self.substorage_level = min(
                        self.substorage_level, station_substorage_capacity
                    )
                    self.timeline.append(
                        (env.now(), self.station_status, -1, self.substorage_level)
                    )
            if self.station_status >= 0:
                s_converter.station_demand_flag[self.station_id] = 1
                s_converter.activate()
                self.passivate()
                self.refuel_speed_flag = self.substorage_level > 0
                print(
                    "Station %d is working on vessel %d with Speed Flag %d, %.3f from converter"
                    % (
                        self.station_id,
                        self.station_status,
                        self.refuel_speed_flag,
                        self.flow_from_converter,
                    )
                )
                self.hold(station_timestep)
                if self.refuel_speed_flag == 0:
                    vessels[self.station_status].demand -= self.flow_from_converter
                    vessels[self.station_status].demand = max(
                        vessels[self.station_status].demand, 0
                    )
                else:
                    vessels[self.station_status].demand -= (
                        self.flow_from_converter + station_extra_speed
                    )
                    self.substorage_level -= station_extra_speed
                    self.substorage_level = max(self.substorage_level, 0)
                    vessels[self.station_status].demand = max(
                        vessels[self.station_status].demand, 0
                    )
                vessels[self.station_status].timeline.append(
                    (env.now(), self.station_id, vessels[self.station_status].demand)
                )
                self.timeline.append(
                    (
                        env.now(),
                        self.station_status,
                        self.refuel_speed_flag,
                        self.substorage_level,
                    )
                )
                print("VesselDEMAND %.3f" % vessels[self.station_status].demand)
                if vessels[self.station_status].demand <= 0:
                    vessels[self.station_status].activate()
                    self.station_status = -1
                    v_con.activate()


class Converter(sim.Component):
    def __init__(self, converter_id=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.converter_id = converter_id
        self.station_demand_flag = [0 for i in range(station_num)]
        # each station for a demand flag 0 for no need 1 for need
        self.output_flow = 0  # output to per station
        self.input_flow = 0  # input from storage (total)
        self.timeline = [(env.now(), 0, 0, 0)]
        # time, number of stations calling for ammonia, input flow, output flow (per station)

    def process(self):
        global main_storage_level
        while True:
            if sum(self.station_demand_flag) <= 0:
                self.output_flow = 0
                self.timeline.append((env.now(), 0, 0, 0))
            else:
                self.output_flow = min(
                    converter_output_max_per_station,
                    converter_intput_max / sum(self.station_demand_flag),
                )
                self.input_flow = self.output_flow * sum(self.station_demand_flag)
                self.timeline.append(
                    (
                        env.now(),
                        sum(self.station_demand_flag),
                        self.input_flow,
                        self.output_flow,
                    )
                )
            for id in range(station_num):
                if self.station_demand_flag[id] == 1:
                    stations[id].flow_from_converter = self.output_flow
                    stations[id].activate()
            self.hold(station_timestep)
            main_storage_level -= self.input_flow
            self.passivate()


# Simulation
env = sim.Environment(time_unit="minutes")
# env = sim.Environment(trace="True")
v_gen = VesselGenerator()
v_con = VesselControl()
s_converter = Converter()
stations = [Station(i) for i in range(station_num)]
vessels = []
env.run()
# v_con.bunkering_queue.print_info()

# Output
# v_con.bunkering_queue.print_info()
plt.figure(1)
for vessel in vessels:
    # print(vessel.timeline)
    plt.plot(
        [vessel.timeline[i][0] for i in range(len(vessel.timeline))],
        [vessel.timeline[i][2] for i in range(len(vessel.timeline))],
    )
plt.grid()
plt.xlabel("Time [s]")
plt.ylabel("Demand")

plt.figure(2)
for station in stations:
    # print(station.timeline)
    plt.plot(
        [station.timeline[i][0] for i in range(len(station.timeline))],
        [station.timeline[i][3] for i in range(len(station.timeline))],
    )
plt.grid()
plt.xlabel("Time [s]")
plt.ylabel("Substorage level")
plt.show()
# print(s_converter.timeline)
