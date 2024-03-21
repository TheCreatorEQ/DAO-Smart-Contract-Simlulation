import os
import sys
import csv
import traci
import math

contract_counter = 0

def calculate_distance(pos1, pos2):
    """Calculate the Euclidean distance between two positions."""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

class DAOContract:
    def __init__(self, timestamp, initiator_id, initiator_position):
        global contract_counter
        self.contract_id = contract_counter
        contract_counter += 1
        self.timestamp = timestamp
        self.initiator_id = initiator_id
        self.initiator_position = initiator_position
        self.participants = {initiator_id: initiator_position}  # Automatically add initiator

    def add_participant(self, vehicle_id, position):
        if vehicle_id != self.initiator_id and calculate_distance(self.initiator_position, position) <= 5:
            self.participants[vehicle_id] = position

class Vehicle:
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.locational_data = []
        self.contracts = []

    def update_location(self, timestamp, position):
        self.locational_data.append((timestamp, position))

    def initiate_contract(self, timestamp):
        if not self.locational_data:
            return None
        current_position = self.locational_data[-1][1]
        contract = DAOContract(timestamp, self.vehicle_id, current_position)
        self.contracts.append(contract)
        return contract

    def participate_in_contract(self, contract):
        if self.locational_data:
            timestamp, position = self.locational_data[-1]
            contract.add_participant(self.vehicle_id, position)

def run_simulation(sumo_cmd):
    traci.start(sumo_cmd)
    vehicles = {}
    contract_interval = 1
    next_contract_time = 0

    with open("ledger.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Contract ID", "Timestamp", "Initiator", "Participants"])

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            current_time = traci.simulation.getTime()

            if current_time >= next_contract_time:
                next_contract_time += contract_interval

                vehicle_ids = traci.vehicle.getIDList()
                for vehicle_id in vehicle_ids:
                    if vehicle_id not in vehicles:
                        vehicles[vehicle_id] = Vehicle(vehicle_id)
                    position = traci.vehicle.getPosition(vehicle_id)
                    vehicles[vehicle_id].update_location(current_time, position)

                for vehicle_id, vehicle in vehicles.items():
                    contract = vehicle.initiate_contract(current_time)
                    if contract:
                        for vid, v in vehicles.items():
                            v.participate_in_contract(contract)

                        if len(contract.participants) > 1:  # Change here to check for more than 1 participant
                            with open("ledger.csv", "a", newline="") as file:
                                writer = csv.writer(file)
                                participants_data = "; ".join([f"{pid}: {pos}" for pid, pos in contract.participants.items()])
                                writer.writerow([contract.contract_id, contract.timestamp, contract.initiator_id, participants_data])
    finally:
        traci.close()

if __name__ == "__main__":
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("Please declare the environment variable 'SUMO_HOME'")

    sumoBinary = "sumo-gui"
    sumoCmd = [sumoBinary, "-c", "grid.sumocfg"]
    run_simulation(sumoCmd)
