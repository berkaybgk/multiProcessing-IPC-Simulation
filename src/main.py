#!/usr/bin/env python
import math

from mpi4py import MPI
from worker import Worker

# MPI setup
comm = MPI.COMM_WORLD
world_size = comm.Get_size()
rank = comm.Get_rank()

# Constant for manager rank
MANAGER = 0

# get the max perfect square number that is less than or equal to the world size
worker_count = int(math.sqrt(world_size - 1)) ** 2

def main():
    if rank == MANAGER: # Manager

        file_path = "./io/input1.txt"

        board_for_waves, N, wave_count, units_per_wave, rounds_per_wave = parse_input(file_path)

        grid_size = int(N / math.sqrt(worker_count))

        # Send the simulation info to the workers
        for worker_index in range(1, worker_count+1):
            comm.send((N, units_per_wave, rounds_per_wave, wave_count, grid_size), dest=worker_index, tag=1)

        # Send the board to the workers
        for wave_index in range(wave_count):
            # partition the board to fields and send them to the workers
            worker_fields = partition_board_to_fields(board_for_waves[wave_index], N, worker_count, grid_size)

            # Send the fields to the workers
            for worker_index in range(1, worker_count+1):
                comm.send(worker_fields[worker_index - 1], dest=worker_index, tag=0)

            # # The debug print to get the board after each round in a wave
            # for round_number in range(rounds_per_wave):
            #     worker_regions_combined = {}
            #     for worker_index in range(1, worker_count+1):
            #         worker_regions = comm.recv(source=worker_index, tag=0)
            #         worker_regions_combined.update(worker_regions)
            #
            #     print("Round", round_number+1)
            #     print_dict_board(worker_regions_combined, N)

            # ------- BEFORE ENDING THE WAVE -------

            # Receive the fields from the workers
            worker_regions_combined = {}
            for worker_index in range(1, worker_count+1):
                worker_regions = comm.recv(source=worker_index, tag=0)
                worker_regions_combined.update(worker_regions)

            # Print the board after the wave ends
            # print("Wave", wave_index+1)

            # Print the last state of the board after the waves end
            if wave_index == wave_count - 1:
                with open("./io/output1.txt", "w") as file:
                    for i in range(N):
                        for j in range(N):
                            if worker_regions_combined[(i, j)] == "." or worker_regions_combined[(i, j)] is None:
                                file.write(".")
                            else:
                                file.write(worker_regions_combined[(i, j)].faction[0])
                            if j != N - 1:
                                file.write(" ")
                        file.write("\n")

    else: # Worker
        if rank > worker_count:
            return
        # Receive the simulation info from the manager
        N, units_per_wave, rounds_per_wave, wave_count, grid_size = comm.recv(source=MANAGER, tag=1)
        grid_edge_length = int(math.sqrt(world_size - 1))

        # Create the worker instance
        worker = Worker(rank, grid_size, grid_edge_length, N)

        # Start the simulation, iterate over the waves
        for i in range(wave_count):
            # Receive the field from the manager
            worker_field = comm.recv(source=MANAGER, tag=0)

            # Set and update the field from the info received
            worker.receive_wave_info(worker_field)

            # Iterate over the rounds in the wave
            for round_number in range(rounds_per_wave):
                ############# ROUND STARTED #############

                # ------- MOVE PHASE START -------
                # get the move packs from the worker
                move_packs = worker.move_phase()

                # get the neighbour ranks of the worker
                neighbour_ranks = worker.get_neighbour_worker_ranks()

                # send the move packs to the neighbours
                for neighbour_rank in neighbour_ranks:
                    move_packs_filtered = worker.filter_moves(move_packs)
                    comm.send(move_packs_filtered, dest=neighbour_rank, tag=2)

                # receive the move packs from the neighbours
                every_neighbour_move = {}
                for neighbour_rank in neighbour_ranks:
                    neighbour_moves = comm.recv(source=neighbour_rank, tag=2)
                    every_neighbour_move[neighbour_rank] = neighbour_moves

                # resolve the moves
                worker.resolve_moves(every_neighbour_move, move_packs)
                # ------- MOVE PHASE END -------


                # ------- ACTION PHASE START -------
                # get the action packs from the worker
                action_packs = worker.action_phase()

                # get the neighbour ranks of the worker
                for neighbour_rank in neighbour_ranks:
                    action_packs_filtered = worker.filter_actions(action_packs)
                    comm.send(action_packs_filtered, dest=neighbour_rank, tag=4)

                # receive the action packs from the neighbours
                every_neighbour_action = {}
                for neighbour_rank in neighbour_ranks:
                    neighbour_actions = comm.recv(source=neighbour_rank, tag=4)
                    every_neighbour_action[neighbour_rank] = neighbour_actions

                # resolve the actions
                worker.resolve_actions(every_neighbour_action, action_packs)
                # ------- ACTION PHASE END -------

                # # The debug send to get the board after each round in a wave
                # comm.send(worker.get_r2_r3(), dest=MANAGER, tag=0)
                ############# ROUND ENDED #############

            # ------- BEFORE ENDING THE WAVE -------

            # flood ability of the water units
            flood_packs = worker.flood_phase()
            neighbour_ranks = worker.get_neighbour_worker_ranks()

            # send the flood packs to the neighbours
            for neighbour_rank in neighbour_ranks:
                flood_packs_filtered = worker.filter_floods(flood_packs)
                comm.send(flood_packs_filtered, dest=neighbour_rank, tag=6)

            # receive the flood packs from the neighbours
            every_neighbour_flood = {}
            for neighbour_rank in neighbour_ranks:
                neighbour_floods = comm.recv(source=neighbour_rank, tag=6)
                every_neighbour_flood[neighbour_rank] = neighbour_floods

            # resolve the floods
            worker.resolve_floods(every_neighbour_flood, flood_packs)

            ############# WAVE ENDED #############
            # Reset the attack powers of the units
            worker.reset_attack_powers()

            # Send the wave-end r2_r3 values to the manager
            comm.send(worker.get_r2_r3(), dest=MANAGER, tag=0)


def partition_board_to_fields(board, N, worker_count, grid_size):
    """Partition the board to fields for each worker"""
    worker_fields = []
    for i in range(int(math.sqrt(worker_count))):
        for j in range(int(math.sqrt(worker_count))):
            worker_field = {}
            for x in range(i*grid_size - 3, (i+1)*grid_size + 3):
                for y in range(j*grid_size - 3, (j+1)*grid_size + 3):
                    if (0 <= x < N) and (0 <= y < N):
                        worker_field[(x, y)] = board[x][y]
                    else:
                        worker_field[(x, y)] = None
            worker_fields.append(worker_field)
    return worker_fields

def print_2d_grid(grid):
    """Debug print for 2D grids"""
    for row in grid:
        print(" ".join(row))
    print()

def dict_to_board(board_dict, N):
    """Convert the board dictionary to a 2D list"""
    board = [["." for _ in range(N)] for _ in range(N)]
    for coord, unit in board_dict.items():
        board[coord[0]][coord[1]] = unit
    return board

def print_dict_board(board_dict, N):
    """Print the board dictionary"""
    for i in range(0, N):
        for j in range(0, N):
            print(board_dict[(i, j)], end=" ")
        print()
    print()

def print_dict_board_debug(board_dict, N):
    """Print the board dictionary with health and attack power"""
    for i in range(0, N):
        for j in range(0, N):
            print(board_dict[(i, j)], end=" ")
            try:
                print(f"{board_dict[(i, j)].health:02} {board_dict[(i, j)].attack_power:02}", end=" ")
            except Exception:
                print("      ", end="")
        print()
    print()

def parse_input(file_path):
    """Parse the input file and return the parameters"""
    def parse_coordinates(coordinates):
        """Parse the coordinates"""
        coordinates = [coord.strip() for coord in coordinates]
        # coordinates is a list of strings, each string is a coordinate in the form of "x y"
        return [(int(coord.split()[0]), int(coord.split()[1])) for coord in coordinates]

    def parse_units_coordinates(earth_units_coordinates, fire_units_coordinates, water_units_coordinates, air_units_coordinates):
        """Parse the units' coordinates"""
        return (parse_coordinates(earth_units_coordinates), parse_coordinates(fire_units_coordinates),
            parse_coordinates(water_units_coordinates), parse_coordinates(air_units_coordinates))

    # Read the file
    with open(file_path, "r") as file:
        lines = file.readlines()
        params = lines[0].strip().split()
        N = int(params[0])
        wave_count = int(params[1])
        units_per_wave = int(params[2])
        rounds_per_wave = int(params[3])

        units_in_waves = {}
        for i in range(wave_count):
            units_in_waves[i] = [["." for _ in range(N)] for i in range(N)]

        # Read the grid
        for i in range(int((len(lines)-1) / 5)):
            earth_coords = lines[2 + i*5].strip().split(":")[1].strip().split(",")
            fire_coords = lines[3 + i*5].strip().split(":")[1].strip().split(",")
            water_coords = lines[4 + i*5].strip().split(":")[1].strip().split(",")
            air_coords = lines[5 + i*5].strip().split(":")[1].strip().split(",")

            (earth_units_coordinates, fire_units_coordinates,
             water_units_coordinates, air_units_coordinates) = parse_units_coordinates(
                earth_coords, fire_coords, water_coords, air_coords
            )

            for earth_coord in earth_units_coordinates:
                units_in_waves[i][earth_coord[0]][earth_coord[1]] = "E"

            for fire_coord in fire_units_coordinates:
                units_in_waves[i][fire_coord[0]][fire_coord[1]] = "F"

            for water_coord in water_units_coordinates:
                units_in_waves[i][water_coord[0]][water_coord[1]] = "W"

            for air_coord in air_units_coordinates:
                units_in_waves[i][air_coord[0]][air_coord[1]] = "A"

    # Return the parameters
    return units_in_waves, N, wave_count, units_per_wave, rounds_per_wave


if __name__ == "__main__":
    main()
