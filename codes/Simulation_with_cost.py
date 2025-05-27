# Note that run on salabim 24.0.16

import salabim as sim

import numpy as np
import random

import time

# import pandas as pd
import matplotlib.pyplot as plt

# from tqdm import tqdm

# Parameters
vessel_IAT_mean = 2.77 * 60  # 2.77 hours of IAT
vessel_time_enter = 0.5 * 60  # 0.5 hours of entering station
vessel_time_leave = 0.5 * 60  # 0.5 hours of leaving station
vessel_demand = 160  # 160 unit of demand for ammonia
vessel_size = 100 * 10  # in total 10 vessels per day, simulation for 10 days
vessel_finished = 0  # finished vessels
station_num = 3  # number of stations
# station_speed = [4, 6]  # low- and high-speed refueling (just for debugging)
# station_extra_speed = 40 / 12  # the extra speed provided by substorage
station_timestep = 5  # each timestep of 5 minutes for station, min
# station_substorage_capacity = 37.85  # capacity of substorage, m3
station_substorage_capacity = 0  # capacity of substorage
# converter_intput_max = 200 / 12
# converter_output_max_per_station = 80 / 12
# main_storage_level = max(
#     vessel_demand * vessel_size + station_num * station_substorage_capacity + 1e4, 5e4
# )
main_storage_level = 1892 * 10  # central storage 1892 (daily refill)
main_storage_timeline = [(0, main_storage_level)]

pipe_fc = [200, 80, 120]  # m3 per hour
# three sections of pipe, central-converter, converter-station, station-vessel
converter_intput_max = pipe_fc[0] * station_timestep / 60
converter_output_max_per_station = pipe_fc[1] * station_timestep / 60
station_output_max = pipe_fc[2] * station_timestep / 60


# --- New Infrastructure Cost Calculation Section ---
# Constant definitions
AMMONIA_DENSITY_TON_PER_M3 = 0.682  # Approximately 0.61 tons/m3
GALLONS_PER_M3 = 264.172  # 1 m3 approximately equals 264.172 US liquid gallons

# Tank cost regression formula: y = 1.41x + 329.72 (y in USD, x in gallons) [cite: 217]
TANK_COST_SLOPE = 1.41
TANK_COST_INTERCEPT = 329.72

# Pipe cost regression formula: y = 42.39x + 21490 (y in USD/km, x in tons/day) [cite: 225]
PIPE_COST_SLOPE = 42.39
PIPE_COST_INTERCEPT = 21490

# Pipe lengths (assumed values, please adjust based on actual design)
# len[0]: Central Storage to Converter
# len[1]: Converter to Station (per station)
# len[2]: In-station, Sub-Storage/Converter to Vessel (per station)
PIPE_LENGTHS_KM = {
    "central_to_converter": 0.5,  # 0.5 km
    "converter_to_station": 0.1,  # 0.1 km (per station)
    "station_to_vessel": 0.05,  # 0.05 km (per station)
}

def calculate_infrastructure_cost(
    main_storage_capacity_m3,
    substorage_capacity_m3,
    num_stations,
    pipe_flow_capacities_m3_per_hr,
    pipe_lengths_km
):
    """
    Calculates the total infrastructure construction cost (tanks and pipes).
    Central storage tank uses a fixed cost of $1,750,000.
    Sub-storage tanks (if any) use the linear regression formula: y = 1.41x + 329.72 (y in USD, x in gallons).
    """
    total_tank_cost = 0
    total_pipe_cost = 0

    # 1. Calculate Central Storage Tank Cost (Fixed Cost)
    central_tank_cost = 1750000  # Fixed cost for central storage tank
    total_tank_cost += central_tank_cost
    central_storage_capacity_gallons = main_storage_capacity_m3 * GALLONS_PER_M3
    print(f"Central Storage Capacity: {main_storage_capacity_m3:.2f} m3 ({central_storage_capacity_gallons:.2f} gallons)")
    print(f"Central Storage Tank Cost (Fixed): ${central_tank_cost:.2f}")

    # 2. Calculate Sub-Storage Tank Cost (if any)
    if substorage_capacity_m3 > 0:
        substorage_capacity_gallons = substorage_capacity_m3 * GALLONS_PER_M3
        single_substorage_cost = TANK_COST_SLOPE * substorage_capacity_gallons + TANK_COST_INTERCEPT
        total_substorage_cost = single_substorage_cost * num_stations
        total_tank_cost += total_substorage_cost
        print(f"Single Sub-Storage Tank Capacity: {substorage_capacity_m3:.2f} m3 ({substorage_capacity_gallons:.2f} gallons)")
        print(f"Single Sub-Storage Tank Cost: ${single_substorage_cost:.2f}")
        print(f"Total Sub-Storage Tank Cost ({num_stations} units): ${total_substorage_cost:.2f}")
    else:
        print("No Sub-Storage Tanks, Sub-Storage Cost is $0.")

    # 3. Calculate Pipe Costs
    # Pipe 0: Central Storage to Converter
    fc0_tons_per_day = pipe_flow_capacities_m3_per_hr[0] * AMMONIA_DENSITY_TON_PER_M3 * 24
    cost_per_km_0 = PIPE_COST_SLOPE * fc0_tons_per_day + PIPE_COST_INTERCEPT
    pipe0_cost = cost_per_km_0 * pipe_lengths_km["central_to_converter"]
    total_pipe_cost += pipe0_cost
    print(f"\nPipe 0 (Central-Converter) Flow Capacity: {fc0_tons_per_day:.2f} tons/day, Length: {pipe_lengths_km['central_to_converter']} km")
    print(f"Pipe 0 Cost: ${pipe0_cost:.2f}")

    # Pipe 1: Converter to Station (per station, multiplied by number of stations)
    fc1_tons_per_day = pipe_flow_capacities_m3_per_hr[1] * AMMONIA_DENSITY_TON_PER_M3 * 24
    cost_per_km_1 = PIPE_COST_SLOPE * fc1_tons_per_day + PIPE_COST_INTERCEPT
    pipe1_cost = cost_per_km_1 * pipe_lengths_km["converter_to_station"] * num_stations
    total_pipe_cost += pipe1_cost
    print(f"Pipe 1 (Converter-Station) Flow Capacity: {fc1_tons_per_day:.2f} tons/day, Length: {pipe_lengths_km['converter_to_station']} km/station")
    print(f"Pipe 1 Total Cost ({num_stations} stations): ${pipe1_cost:.2f}")

    # Pipe 2: In-station (Sub-Storage/Converter to Vessel) (per station, multiplied by number of stations)
    fc2_tons_per_day = pipe_flow_capacities_m3_per_hr[2] * AMMONIA_DENSITY_TON_PER_M3 * 24
    cost_per_km_2 = PIPE_COST_SLOPE * fc2_tons_per_day + PIPE_COST_INTERCEPT
    pipe2_cost = cost_per_km_2 * pipe_lengths_km["station_to_vessel"] * num_stations
    total_pipe_cost += pipe2_cost
    print(f"Pipe 2 (In-Station to Vessel) Flow Capacity: {fc2_tons_per_day:.2f} tons/day, Length: {pipe_lengths_km['station_to_vessel']} km/station")
    print(f"Pipe 2 Total Cost ({num_stations} stations): ${pipe2_cost:.2f}")

    print(f"\nTotal Tank Cost: ${total_tank_cost:.2f}")
    print(f"Total Pipe Cost: ${total_pipe_cost:.2f}")

    total_infrastructure_cost = total_tank_cost + total_pipe_cost
    return total_infrastructure_cost


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


#             self.hold(vessel_IAT_mean)


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
        global vessel_finished
        if self.vessel_status == -1:
            self.enter(v_con.bunkering_queue)
            if v_con.ispassive():
                v_con.activate()
            self.passivate()
        if self.vessel_status >= 0:
            #             print(
            #                 "Vessel %d assigned to Station %d"
            #                 % (self.vessel_id, self.vessel_status)
            #             )
            self.timeline.append((env.now(), self.vessel_status, self.demand))
            if self.flag_enter == 0:
                self.hold(vessel_time_enter)
                self.flag_enter = 1
                #                 print(
                #                     "Vessel %d arrives at Station %d"
                #                     % (self.vessel_id, self.vessel_status)
                #                 )
                stations[self.vessel_status].station_status = self.vessel_id
                # stations[self.vessel_status].activate()
                self.timeline.append((env.now(), self.vessel_status, self.demand))
                self.passivate()
                self.hold(station_timestep)
            if self.demand <= 0:
                v_con.station_busy_flag[self.vessel_status] = 0
                v_con.activate()
                self.vessel_status = -2
                vessel_finished = vessel_finished + 1
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
                #                 print(
                #                     "Vessel %d is to be allocated" % self.bunkering_queue[0].vessel_id
                #                 )
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
        global main_storage_level
        while True:
            if s_converter.station_demand_flag[self.station_id] <= 0:
                self.passivate()
            if self.station_status == -1:
                self.refuel_speed_flag = -1
                if self.substorage_level > station_substorage_capacity:
                    main_storage_level = (
                        main_storage_level
                        + self.substorage_level
                        - station_substorage_capacity
                    )
                    # give the last step's extra ammonia back to main storage
                    self.substorage_level = station_substorage_capacity
                    # s_converter.station_demand_flag[self.station_id] = 0
                    # self.passivate()
                    # self.hold(station_timestep)
                    self.timeline.append(
                        (env.now(), self.station_status, -1, self.substorage_level)
                    )
                else:
                    # s_converter.station_demand_flag[self.station_id] = 1
                    # s_converter.activate()
                    # self.passivate()
                    #                     print("Station %d is refueling its substorage" % self.station_id)
                    self.timeline.append(
                        (env.now(), self.station_status, -1, self.substorage_level)
                    )
                    # self.hold(station_timestep)
                    self.substorage_level += self.flow_from_converter
                    if self.substorage_level > station_substorage_capacity:
                        main_storage_level = (
                            main_storage_level
                            + self.substorage_level
                            - station_substorage_capacity
                        )
                        # give the last step's extra ammonia back to main storage
                        self.substorage_level = station_substorage_capacity
                    self.timeline.append(
                        (
                            env.now() + station_timestep,
                            self.station_status,
                            -1,
                            self.substorage_level,
                        )
                    )
            if self.station_status >= 0:
                # s_converter.station_demand_flag[self.station_id] = 1
                # s_converter.activate()
                # self.passivate()
                self.refuel_speed_flag = int(self.substorage_level > 0)
                #                 print(
                #                     "Station %d is working on vessel %d with Speed Flag %d, %.3f from converter"
                #                     % (
                #                         self.station_id,
                #                         self.station_status,
                #                         self.refuel_speed_flag,
                #                         self.flow_from_converter,
                #                     )
                #                 )
                self.timeline.append(
                    (env.now(), self.station_status, -1, self.substorage_level)
                )
                vessels[self.station_status].timeline.append(
                    (env.now(), self.station_id, vessels[self.station_status].demand)
                )
                # self.hold(station_timestep)
                if self.refuel_speed_flag == 0:
                    vessels[self.station_status].demand -= self.flow_from_converter
                    if vessels[self.station_status].demand < 0:
                        #                         print("case1-1=%.3f,%.3f"%(main_storage_level,- vessels[self.station_status].demand))
                        main_storage_level = (
                            main_storage_level - vessels[self.station_status].demand
                        )
                        # give the extra ammnoia last step back to main storage
                        vessels[self.station_status].demand = 0
                else:
                    # quick charge: check in flow and output demand
                    vessels[self.station_status].demand -= self.flow_from_converter
                    if vessels[self.station_status].demand < 0:
                        # case 1: inflow satisfies demand
                        main_storage_level = (
                            main_storage_level - vessels[self.station_status].demand
                        )
                        # give the extra ammnoia last step back to main storage
                        vessels[self.station_status].demand = 0
                    else:
                        # case 2: inflow cannot satisfy demand, use substorage
                        station_extra_speed = min(
                            vessels[self.station_status].demand,
                            station_output_max - self.flow_from_converter,
                            self.substorage_level,
                        )
                        vessels[self.station_status].demand -= station_extra_speed
                        self.substorage_level -= station_extra_speed
                #                     vessels[self.station_status].demand -= (
                #                         self.flow_from_converter + station_extra_speed
                #                     )
                #                     self.substorage_level -= station_extra_speed
                #                     self.substorage_level = max(self.substorage_level, 0)
                #                     vessels[self.station_status].demand = max(
                #                         vessels[self.station_status].demand, 0
                #                     )
                vessels[self.station_status].timeline.append(
                    (
                        env.now() + station_timestep,
                        self.station_id,
                        vessels[self.station_status].demand,
                    )
                )
                self.timeline.append(
                    (
                        env.now() + station_timestep,
                        self.station_status,
                        self.refuel_speed_flag,
                        self.substorage_level,
                    )
                )
                # print("VesselDEMAND %.3f" % vessels[self.station_status].demand)
                if vessels[self.station_status].demand <= 0:
                    vessels[self.station_status].activate()
                    self.station_status = -1
                    v_con.activate()
            self.passivate()


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
            # calculate station demand flags
            for id in range(station_num):
                if (
                    stations[id].station_status < 0
                    and stations[id].substorage_level >= station_substorage_capacity
                ):
                    self.station_demand_flag[id] = 0
                else:
                    self.station_demand_flag[id] = 1
            if vessel_finished >= vessel_size and sum(self.station_demand_flag) <= 0:
                self.passivate()
                break
            if sum(self.station_demand_flag) <= 0:
                self.output_flow = 0
                self.input_flow = 0
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
                stations[id].flow_from_converter = 0
                if self.station_demand_flag[id] == 1:
                    stations[id].flow_from_converter = self.output_flow
                    stations[id].activate()
            self.hold(station_timestep)
            main_storage_level -= self.input_flow
            main_storage_timeline.append((env.now(), main_storage_level))
            # self.passivate()


# Simulation
env = sim.Environment(time_unit="minutes")
# env = sim.Environment(trace="True")
v_gen = VesselGenerator()
v_con = VesselControl()
s_converter = Converter()
stations = [Station(i) for i in range(station_num)]
vessels = []
env.random_seed(int(time.time()))  # use timestamp as random seed
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

plt.figure(3)
plt.plot(
    [main_storage_timeline[i][0] for i in range(len(main_storage_timeline))],
    [main_storage_timeline[i][1] for i in range(len(main_storage_timeline))],
)
plt.grid()

vessel_service_time = [0] * vessel_size
for i in range(vessel_size):
    vessel_service_time[i] = vessels[i].timeline[-1][0] - vessels[i].timeline[0][0]
# print(vessel_service_time)
# print(np.mean(vessel_service_time))
plt.figure(4)
plt.bar(range(vessel_size), vessel_service_time)
plt.axhline(1.7 * 60 * vessel_demand / pipe_fc[1])
plt.axhline(2.3 * 60 * vessel_demand / pipe_fc[1])

plt.show()
# print(s_converter.timeline)
print(f"Final Main Storage Level: {main_storage_level:.2f}")

ideal_service_time = 60 * vessel_demand / pipe_fc[1]  # in minutes

# Thresholds for service level classification
threshold_good = 1.7 * ideal_service_time
threshold_acceptable = 2.3 * ideal_service_time

# Calculate service time per vessel
vessel_service_time = [v.timeline[-1][0] - v.timeline[0][0] for v in vessels]

# Proportions of vessels in each category
P1 = sum(t <= threshold_good for t in vessel_service_time) / vessel_size
P2 = sum(threshold_good < t <= threshold_acceptable for t in vessel_service_time) / vessel_size
P3 = sum(t > threshold_acceptable for t in vessel_service_time) / vessel_size

# Define weights and penalty
w1, w2, w3 = 0.7, 0.25, 0.05
penalty_lambda = 0.3

# Compute SLI and adjusted SLI
SLI = w1 * P1 + w2 * P2 + w3 * P3
adjusted_SLI = SLI - penalty_lambda * P3

print(f"SLI: {SLI:.3f}")
print(f"Adjusted SLI (with penalty): {adjusted_SLI:.3f}")

# --- Output Total Infrastructure Construction Cost ---
print("\n--- Infrastructure Construction Cost Estimation ---")
# main_storage_level is defined as 1892 * 10 = 18920 m3, which is the total capacity.
# The calculation should use this total capacity.
total_construction_cost = calculate_infrastructure_cost(
    main_storage_capacity_m3=main_storage_level,
    substorage_capacity_m3=station_substorage_capacity,
    num_stations=station_num,
    pipe_flow_capacities_m3_per_hr=pipe_fc,
    pipe_lengths_km=PIPE_LENGTHS_KM
)
print(f"\nTotal Infrastructure Construction Cost: ${total_construction_cost:.2f}")