# Note that run on salabim 24.0.16

import salabim as sim
import numpy as np
import random
import time
import matplotlib.pyplot as plt
import json

# Function to run a single simulation and return metrics
def run_simulation(run_id):
    global vessel_finished, main_storage_level, main_storage_timeline, vessels, stations, v_con, s_converter

    # Parameters
    vessel_IAT_mean = 2.77 * 60  # 2.77 hours of IAT
    vessel_time_enter = 0.5 * 60  # 0.5 hours of entering station
    vessel_time_leave = 0.5 * 60  # 0.5 hours of leaving station
    vessel_demand = 160  # 160 unit of demand for ammonia
    vessel_size = 10 * 10  # 10 vessels per day, simulation for 10 days
    vessel_finished = 0  # finished vessels
    station_num = 2  # number of stations
    station_timestep = 5  # each timestep of 5 minutes for station, min
    station_substorage_capacity = 0  # capacity of substorage, m3
    main_storage_level = 1892 * 10  # central storage 18920 m3
    main_storage_timeline = [(0, main_storage_level)]

    pipe_fc = [200, 100, 120]  # m3 per hour
    converter_intput_max = pipe_fc[0] * station_timestep / 60
    converter_output_max_per_station = pipe_fc[1] * station_timestep / 60
    station_output_max = pipe_fc[2] * station_timestep / 60

    # Constant definitions
    AMMONIA_DENSITY_TON_PER_M3 = 0.682
    GALLONS_PER_M3 = 264.172
    TANK_COST_SLOPE = 1.41
    TANK_COST_INTERCEPT = 329.72
    PIPE_COST_SLOPE = 42.39
    PIPE_COST_INTERCEPT = 21490
    STATION_FIXED_COST = 1_500_000  # Fixed construction cost per ammonia station in USD

    PIPE_LENGTHS_KM = {
        "central_to_converter": 0.5,
        "converter_to_station": 0.1,
        "station_to_vessel": 0.05,
    }

    def calculate_infrastructure_cost(
        main_storage_capacity_m3,
        substorage_capacity_m3,
        num_stations,
        pipe_flow_capacities_m3_per_hr,
        pipe_lengths_km
    ):
        total_tank_cost = 0
        total_pipe_cost = 0
        total_station_fixed_cost = 0

        # Central storage tank cost
        central_tank_cost = 1750000
        total_tank_cost += central_tank_cost
        central_storage_capacity_gallons = main_storage_capacity_m3 * GALLONS_PER_M3
        if run_id == 0:  # Print details only for the first run
            print(f"Central Storage Capacity: {main_storage_capacity_m3:.2f} m3 ({central_storage_capacity_gallons:.2f} gallons)")
            print(f"Central Storage Tank Cost (Fixed): ${central_tank_cost:.2f}")

        # Sub-storage tank cost
        if substorage_capacity_m3 > 0:
            substorage_capacity_gallons = substorage_capacity_m3 * GALLONS_PER_M3
            single_substorage_cost = TANK_COST_SLOPE * substorage_capacity_gallons + TANK_COST_INTERCEPT
            total_substorage_cost = single_substorage_cost * num_stations
            total_tank_cost += total_substorage_cost
            if run_id == 0:
                print(f"Single Sub-Storage Tank Capacity: {substorage_capacity_m3:.2f} m3 ({substorage_capacity_gallons:.2f} gallons)")
                print(f"Single Sub-Storage Tank Cost: ${single_substorage_cost:.2f}")
                print(f"Total Sub-Storage Tank Cost ({num_stations} units): ${total_substorage_cost:.2f}")
        else:
            if run_id == 0:
                print("No Sub-Storage Tanks, Sub-Storage Cost is $0.")

        # Station fixed construction cost
        total_station_fixed_cost = STATION_FIXED_COST * num_stations
        if run_id == 0:
            print(f"Fixed Construction Cost per Ammonia Station: ${STATION_FIXED_COST:.2f}")
            print(f"Total Station Fixed Construction Cost ({num_stations} stations): ${total_station_fixed_cost:.2f}")

        # Pipe costs
        fc0_tons_per_day = pipe_flow_capacities_m3_per_hr[0] * AMMONIA_DENSITY_TON_PER_M3 * 24
        cost_per_km_0 = PIPE_COST_SLOPE * fc0_tons_per_day + PIPE_COST_INTERCEPT
        pipe0_cost = cost_per_km_0 * pipe_lengths_km["central_to_converter"]
        total_pipe_cost += pipe0_cost
        if run_id == 0:
            print(f"\nPipe 0 (Central-Converter) Flow Capacity: {fc0_tons_per_day:.2f} tons/day, Length: {pipe_lengths_km['central_to_converter']} km")
            print(f"Pipe 0 Cost: ${pipe0_cost:.2f}")

        fc1_tons_per_day = pipe_flow_capacities_m3_per_hr[1] * AMMONIA_DENSITY_TON_PER_M3 * 24
        cost_per_km_1 = PIPE_COST_SLOPE * fc1_tons_per_day + PIPE_COST_INTERCEPT
        pipe1_cost = cost_per_km_1 * pipe_lengths_km["converter_to_station"] * num_stations
        total_pipe_cost += pipe1_cost
        if run_id == 0:
            print(f"Pipe 1 (Converter-Station) Flow Capacity: {fc1_tons_per_day:.2f} tons/day, Length: {pipe_lengths_km['converter_to_station']} km/station")
            print(f"Pipe 1 Total Cost ({num_stations} stations): ${pipe1_cost:.2f}")

        fc2_tons_per_day = pipe_flow_capacities_m3_per_hr[2] * AMMONIA_DENSITY_TON_PER_M3 * 24
        cost_per_km_2 = PIPE_COST_SLOPE * fc2_tons_per_day + PIPE_COST_INTERCEPT
        pipe2_cost = cost_per_km_2 * pipe_lengths_km["station_to_vessel"] * num_stations
        total_pipe_cost += pipe2_cost
        if run_id == 0:
            print(f"Pipe 2 (In-Station to Vessel) Flow Capacity: {fc2_tons_per_day:.2f} tons/day, Length: {pipe_lengths_km['station_to_vessel']} km/station")
            print(f"Pipe 2 Total Cost ({num_stations} stations): ${pipe2_cost:.2f}")

        if run_id == 0:
            print(f"\nTotal Tank Cost: ${total_tank_cost:.2f}")
            print(f"Total Pipe Cost: ${total_pipe_cost:.2f}")
            print(f"Total Station Fixed Cost: ${total_station_fixed_cost:.2f}")

        total_infrastructure_cost = total_tank_cost + total_pipe_cost + total_station_fixed_cost
        return total_infrastructure_cost

    class VesselGenerator(sim.Component):
        def __init__(self, generator_id=0, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.generator_id = generator_id
            self.vessel_gen = 0

        def process(self):
            while self.vessel_gen < vessel_size:
                vessels.append(Vessel(self.vessel_gen))
                self.vessel_gen += 1
                self.hold(sim.Exponential(vessel_IAT_mean).sample())

    class Vessel(sim.Component):
        def __init__(self, vessel_id, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.vessel_id = vessel_id
            self.demand = vessel_demand
            self.vessel_status = -1
            self.flag_enter = 0
            self.timeline = [(env.now(), -1, vessel_demand)]

        def process(self):
            global vessel_finished
            if self.vessel_status == -1:
                self.enter(v_con.bunkering_queue)
                if v_con.ispassive():
                    v_con.activate()
                self.passivate()
            if self.vessel_status >= 0:
                self.timeline.append((env.now(), self.vessel_status, self.demand))
                if self.flag_enter == 0:
                    self.hold(vessel_time_enter)
                    self.flag_enter = 1
                    stations[self.vessel_status].station_status = self.vessel_id
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

        def process(self):
            while True:
                station_empty_id = -1
                for i in range(station_num):
                    if self.station_busy_flag[i] == 0:
                        station_empty_id = i
                        break
                if station_empty_id < 0 or len(self.bunkering_queue) == 0:
                    self.passivate()
                    continue
                if station_empty_id >= 0 and len(self.bunkering_queue) > 0:
                    self.station_busy_flag[station_empty_id] = 1
                    self.bunkering_queue[0].vessel_status = stations[station_empty_id].station_id
                    self.bunkering_queue[0].activate()
                    self.bunkering_queue.pop()

    class Station(sim.Component):
        def __init__(self, station_id, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.station_id = station_id
            self.station_status = -1
            self.substorage_level = station_substorage_capacity
            self.refuel_speed_flag = -1
            self.timeline = [(env.now(), -1, -1, station_substorage_capacity)]
            self.flow_from_converter = 0

        def process(self):
            global main_storage_level
            while True:
                if s_converter.station_demand_flag[self.station_id] <= 0:
                    self.passivate()
                if self.station_status == -1:
                    self.refuel_speed_flag = -1
                    if self.substorage_level > station_substorage_capacity:
                        main_storage_level = main_storage_level + self.substorage_level - station_substorage_capacity
                        self.substorage_level = station_substorage_capacity
                        self.timeline.append((env.now(), self.station_status, -1, self.substorage_level))
                    else:
                        self.timeline.append((env.now(), self.station_status, -1, self.substorage_level))
                        self.substorage_level += self.flow_from_converter
                        if self.substorage_level > station_substorage_capacity:
                            main_storage_level = main_storage_level + self.substorage_level - station_substorage_capacity
                            self.substorage_level = station_substorage_capacity
                        self.timeline.append((env.now() + station_timestep, self.station_status, -1, self.substorage_level))
                if self.station_status >= 0:
                    self.refuel_speed_flag = int(self.substorage_level > 0)
                    self.timeline.append((env.now(), self.station_status, -1, self.substorage_level))
                    vessels[self.station_status].timeline.append((env.now(), self.station_id, vessels[self.station_status].demand))
                    if self.refuel_speed_flag == 0:
                        vessels[self.station_status].demand -= self.flow_from_converter
                        if vessels[self.station_status].demand < 0:
                            main_storage_level = main_storage_level - vessels[self.station_status].demand
                            vessels[self.station_status].demand = 0
                    else:
                        vessels[self.station_status].demand -= self.flow_from_converter
                        if vessels[self.station_status].demand < 0:
                            main_storage_level = main_storage_level - vessels[self.station_status].demand
                            vessels[self.station_status].demand = 0
                        else:
                            station_extra_speed = min(
                                vessels[self.station_status].demand,
                                station_output_max - self.flow_from_converter,
                                self.substorage_level,
                            )
                            vessels[self.station_status].demand -= station_extra_speed
                            self.substorage_level -= station_extra_speed
                        vessels[self.station_status].timeline.append(
                            (env.now() + station_timestep, self.station_id, vessels[self.station_status].demand)
                        )
                        self.timeline.append(
                            (env.now() + station_timestep, self.station_status, self.refuel_speed_flag, self.substorage_level)
                        )
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
            self.output_flow = 0
            self.input_flow = 0
            self.timeline = [(env.now(), 0, 0, 0)]

        def process(self):
            global main_storage_level
            while True:
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
                        (env.now(), sum(self.station_demand_flag), self.input_flow, self.output_flow)
                    )
                for id in range(station_num):
                    stations[id].flow_from_converter = 0
                    if self.station_demand_flag[id] == 1:
                        stations[id].flow_from_converter = self.output_flow
                        stations[id].activate()
                self.hold(station_timestep)
                main_storage_level -= self.input_flow
                main_storage_timeline.append((env.now(), main_storage_level))

    # Simulation
    env = sim.Environment(time_unit="minutes")
    v_gen = VesselGenerator()
    v_con = VesselControl()
    s_converter = Converter()
    stations = [Station(i) for i in range(station_num)]
    vessels = []
    env.random_seed(run_id)  # Use run_id as random seed for reproducibility
    env.run()

    # Calculate metrics
    ideal_service_time = 60 * vessel_demand / pipe_fc[1]
    threshold_good = 1.7 * ideal_service_time
    threshold_acceptable = 2.3 * ideal_service_time
    vessel_service_time = [v.timeline[-1][0] - v.timeline[0][0] for v in vessels]
    P1 = sum(t <= threshold_good for t in vessel_service_time) / vessel_size
    P2 = sum(threshold_good < t <= threshold_acceptable for t in vessel_service_time) / vessel_size
    P3 = sum(t > threshold_acceptable for t in vessel_service_time) / vessel_size
    w1, w2, w3 = 10, 20, 60
    SLI = w1 * P1 + w2 * P2 + w3 * P3

    total_construction_cost = calculate_infrastructure_cost(
        main_storage_capacity_m3=main_storage_level,
        substorage_capacity_m3=station_substorage_capacity,
        num_stations=station_num,
        pipe_flow_capacities_m3_per_hr=pipe_fc,
        pipe_lengths_km=PIPE_LENGTHS_KM
    )

    # Print parameters and results
    print(f"\n--- Run {run_id + 1} ---")
    print(f"Number of Stations: {station_num}")
    print(f"Substorage Capacity: {station_substorage_capacity:.2f} m3")
    print(f"Pipe Flow Capacities: {pipe_fc} m3/h")
    print(f"Pipe Lengths: central_to_converter={PIPE_LENGTHS_KM['central_to_converter']:.2f} km, "
          f"converter_to_station={PIPE_LENGTHS_KM['converter_to_station']:.2f} km, "
          f"station_to_vessel={PIPE_LENGTHS_KM['station_to_vessel']:.2f} km")
    print(f"Final Main Storage Level: {main_storage_level:.2f}")
    print(f"SLI: {SLI:.3f}")
    print(f"Total Infrastructure Construction Cost: ${total_construction_cost:.2f}")

    return {
        "main_storage_level": main_storage_level,
        "SLI": SLI,
        "total_construction_cost": total_construction_cost
    }

# Run simulation 50 times and collect statistics
num_runs = 50
results = {
    "main_storage_level": [],
    "SLI": [],
    "total_construction_cost": []
}

for run_id in range(num_runs):
    metrics = run_simulation(run_id)
    results["main_storage_level"].append(metrics["main_storage_level"])
    results["SLI"].append(metrics["SLI"])
    results["total_construction_cost"].append(metrics["total_construction_cost"])

# Calculate statistics
def calculate_statistics(data):
    mean = np.mean(data)
    variance = np.var(data, ddof=1)  # Use ddof=1 for sample variance
    std_dev = np.std(data, ddof=1)
    return mean, variance, std_dev

print("\n--- Statistics for 50 Runs ---")
for metric in results:
    mean, variance, std_dev = calculate_statistics(results[metric])
    print(f"\n{metric}:")
    print(f"  Mean: {mean:.2f}")
    print(f"  Variance: {variance:.2f}")
    print(f"  Standard Deviation: {std_dev:.2f}")

# Save results to a file
with open("simulation_results.json", "w") as f:
    json.dump(results, f, indent=2)