from typing import Dict
from unit import EarthUnit, FireUnit, WaterUnit, AirUnit

class Worker:
    """Worker class"""
    def __init__(self, rank: int, grid_size: int, grid_edge_length: int, N: int):
        self.rank = rank
        self.grid_size = grid_size
        self.grid_edge_length = grid_edge_length
        self.field = {}
        self.N = N
        self.grid_position = ( (rank-1)//grid_edge_length, (rank-1)%grid_edge_length )
        # board position of the top left corner of the grid
        self.board_position = (self.grid_position[0]*grid_size, self.grid_position[1]*grid_size)

    @staticmethod
    def _create_unit(unit_type: str, coordinate: (int, int), N):
        """Create a unit based on the given unit type and coordinate."""
        if unit_type == "E":
            return EarthUnit(coordinate, N)
        elif unit_type == "F":
            return FireUnit(coordinate, N)
        elif unit_type == "W":
            return WaterUnit(coordinate, N)
        elif unit_type == "A":
            return AirUnit(coordinate, N)
        else:
            return "." # neutral cell

    def decide_region(self, row, col):
        """Decide the region of the given row and column in the grid."""

        # region 3
        if (( self.board_position[0] + 3 <= row <= self.board_position[0] + self.grid_size - 4 ) and
                ( self.board_position[1] + 3 <= col <= self.board_position[1] + self.grid_size - 4 )):
            return 3

        # region 2
        if (( self.board_position[0] <= row <= self.board_position[0] + self.grid_size - 1 ) and
                ( self.board_position[1] <= col <= self.board_position[1] + self.grid_size - 1 )):
            return 2

        # region 1
        if (row,col) in self.field:
            return 1

        # out of bounds
        return 82

    def receive_wave_info(self, new_field: Dict[tuple, str]):
        """Receive wave info from the manager. Initialize or discard conflicts."""
        if len(self.field.keys()) == 0:
            for k,v in new_field.items():
                self.field[k] = self._create_unit(v, k, self.N)
        else:
            for k,v in new_field.items():
                if k in self.field and self.field[k] != v: # the newly received field info conflicts with the existing one
                    if self.field[k] == ".":
                        self.field[k] = self._create_unit(v, k, self.N)
                    else:
                        pass # ignore the new info

                else:
                    if k not in self.field:
                        print("MAJOR MISTAKE")

    def move_phase(self):
        """Create the move packs for the units in the grid."""
        packs = []
        for coord, unit in self.field.items():
            if isinstance(unit, AirUnit) and (self.decide_region(coord[0], coord[1]) == 3 or self.decide_region(coord[0], coord[1]) == 2):
                surroundings = {}
                for i in range(coord[0]-3, coord[0]+4):
                    for j in range(coord[1]-3, coord[1]+4):
                        surroundings[(i, j)] = self.field.get((i, j))

                packs.append(unit.move(surroundings))

        return packs

    def get_neighbour_worker_ranks(self):
        """Get the ranks of the neighbouring workers."""
        neighbour_ranks = []
        if self.grid_position[0] > 0:
            neighbour_ranks.append(self.rank - self.grid_edge_length)
        if self.grid_position[0] < self.grid_edge_length - 1:
            neighbour_ranks.append(self.rank + self.grid_edge_length)
        if self.grid_position[1] > 0:
            neighbour_ranks.append(self.rank - 1)
        if self.grid_position[1] < self.grid_edge_length - 1:
            neighbour_ranks.append(self.rank + 1)

        # diagonal neighbours
        if self.grid_position[0] > 0 and self.grid_position[1] > 0:
            neighbour_ranks.append(self.rank - self.grid_edge_length - 1)
        if self.grid_position[0] > 0 and self.grid_position[1] < self.grid_edge_length - 1:
            neighbour_ranks.append(self.rank - self.grid_edge_length + 1)
        if self.grid_position[0] < self.grid_edge_length - 1 and self.grid_position[1] > 0:
            neighbour_ranks.append(self.rank + self.grid_edge_length - 1)
        if self.grid_position[0] < self.grid_edge_length - 1 and self.grid_position[1] < self.grid_edge_length - 1:
            neighbour_ranks.append(self.rank + self.grid_edge_length + 1)

        return neighbour_ranks

    def resolve_moves(self, every_neighbour_move, move_packs):
        """Resolve the moves of the units in the grid."""
        moving_coordinates = {}
        for coord in self.field.keys():
            moving_coordinates[coord] = []

        for neighbour_rank, neighbour_moves in every_neighbour_move.items():
            for neighbour_move in neighbour_moves:
                if neighbour_move["to"] in self.field:
                    moving_coordinates[neighbour_move["to"]].append(neighbour_move)

        # moves that are leaving the grid
        leaving_moves = []
        for move in move_packs:
            if move["to"] in self.field:
                moving_coordinates[move["to"]].append(move)
            elif move["from"] in self.field and move["to"] not in self.field:
                print("NO ONE SHOULD LEAVE", move)
                leaving_moves.append(move)

        for to_coord, moves in moving_coordinates.items():
            if len(moves) == 0:
                continue

            # make the move if the length of the move list is 1
            if len(moves) == 1:
                if moves[0]["to"] in self.field.keys():

                    # if the "from" coordinate is in the field, then move the unit
                    if moves[0]["from"] in self.field.keys():

                        self.field[to_coord] = self.field[moves[0]["from"]]
                        if moves[0]["from"] != to_coord:
                            self.field[moves[0]["from"]] = "."
                        self.field[to_coord].coordinate = to_coord

                    # else, the unit is coming from a neighbour worker, so create the unit
                    else:
                        self.field[to_coord] = self._create_unit("A", to_coord, self.N)
                        # update the unit's stats
                        self.field[to_coord].health = moves[0]["health"]
                        self.field[to_coord].attack_power = moves[0]["attack_power"]
                        self.field[to_coord].healing_rate = moves[0]["health_rate"]

            # combine the units if the length of the move list is greater than 1
            else:
                combined_unit = self.combine_air_units_while_moving(moves)
                if combined_unit.coordinate == to_coord:
                    self.field[to_coord] = combined_unit
                for move in moves:
                    if move["from"] in self.field.keys():
                        self.field[move["from"]] = "."

        # move the units that are leaving the grid
        for move in leaving_moves:
            self.field[move["from"]] = "."

    def combine_air_units_while_moving(self, move_packs):
        """Combine the air units while moving if they are moving to the same cell."""
        units = []
        for move in move_packs:
            if self.field[move["from"]] not in self.field.keys():
                new_unit = self._create_unit("A", move["from"], self.N)
                new_unit.attack_power = move["attack_power"]
                new_unit.health = move["health"]
                new_unit.healing_rate = move["health_rate"]
                units.append(new_unit)

            else:
                units.append(self.field[move["from"]])

        attack_power = 0
        health = 0
        for unit in units:
            attack_power += unit.attack_power
            health += unit.health
            if health > unit.max_health:
                health = unit.max_health

        combined_unit = AirUnit(move_packs[0]["to"], self.N)
        combined_unit.attack_power = attack_power
        combined_unit.health = health

        return combined_unit

    def get_r2_r3(self):
        """Get the units in regions 2 and 3."""
        r2_r3 = []
        for coord, unit in self.field.items():
            if self.decide_region(coord[0], coord[1]) == 2 or self.decide_region(coord[0], coord[1]) == 3:
                r2_r3.append((coord, unit))

        return r2_r3

    def filter_moves(self, move_packs):
        """Filter the move packs based on the regions."""
        filtered_packs = []
        for move_pack in move_packs:
            if (self.decide_region(move_pack["to"][0], move_pack["to"][1]) == 3
                    and self.decide_region(move_pack["from"][0], move_pack["from"][1]) == 3):
                continue
            filtered_packs.append(move_pack)

        return filtered_packs

    def filter_actions(self, action_packs):
        """Filter the action packs based on the regions."""
        filtered_packs = []
        for action_pack in action_packs:
            if action_pack["type"] == "attack":
                if (self.decide_region(action_pack["to"][0], action_pack["to"][1]) == 3
                        and self.decide_region(action_pack["from"][0], action_pack["from"][1]) == 3):
                    continue

            elif action_pack["type"] == "heal":
                if self.decide_region(action_pack["coord"][0], action_pack["coord"][1]) == 3:
                    continue

            filtered_packs.append(action_pack)

        return filtered_packs

    def filter_floods(self, flood_packs):
        """Filter the flood packs based on the regions."""
        filtered_packs = []
        for flood_pack in flood_packs:
            if flood_pack["to"] is None:
                continue
            if self.decide_region(flood_pack["to"][0], flood_pack["to"][1]) == 3:
                continue
            filtered_packs.append(flood_pack)

        return filtered_packs

    def action_phase(self):
        """Create the action packs for the units in the grid."""
        actions_packs = []
        for coord, unit in self.field.items():

            # if the unit is not in region 2 or 3, skip
            if not(self.decide_region(coord[0], coord[1]) == 2) and not(self.decide_region(coord[0], coord[1]) == 3):
                continue

            if (isinstance(unit, EarthUnit) or isinstance(unit, FireUnit)
                    or isinstance(unit, WaterUnit) or isinstance(unit, AirUnit)):

                # if the units health is below 50 percent, heal
                if unit.health < (unit.max_health / 2):
                    actions_packs.append(unit.get_healing_pack())
                    continue

                # then look for the attackable enemies and either heal or attack
                surroundings = {}
                for attack_direction in unit.attack_pattern():
                    attack_position = (coord[0] + attack_direction[0], coord[1] + attack_direction[1])

                    # if the unit is an air unit, check enlarged attack positions
                    if isinstance(unit, AirUnit):
                        if self.field[attack_position] == ".":
                            attack_direction = (2 * attack_direction[0], 2 * attack_direction[1])
                            attack_position = (coord[0] + attack_direction[0], coord[1] + attack_direction[1])

                    # if the attack position is out of bounds, skip
                    if attack_position[0] < 0 or attack_position[0] >= self.N or attack_position[1] < 0 or attack_position[1] >= self.N:
                        continue

                    surroundings[attack_position] = self.field.get(attack_position)

                actions_packs += unit.action(surroundings)

        return actions_packs

    def resolve_actions(self, neighbour_action_packs, action_packs):
        """Resolve the actions of the units in the grid."""
        target_action_coords = {}

        for coord in self.field.keys():
            target_action_coords[coord] = {
                "attacks": [],
                "heal": None
            }

        # get the attack and heal actions of the neighbouring workers
        for neighbour_rank, neighbour_actions in neighbour_action_packs.items():
            for neighbour_action in neighbour_actions:
                if neighbour_action["type"] == "attack":
                    if neighbour_action["to"] in self.field:
                        target_action_coords[neighbour_action["to"]]["attacks"].append(neighbour_action)
                elif neighbour_action["type"] == "heal":
                    if neighbour_action["coord"] in self.field:
                        target_action_coords[neighbour_action["coord"]]["heal"] = neighbour_action

        # get the attack and heal actions of the units in the grid
        for action_pack in action_packs:
            if action_pack["type"] == "attack":
                target_action_coords[action_pack["to"]]["attacks"].append(action_pack)
            elif action_pack["type"] == "heal":
                target_action_coords[action_pack["coord"]]["heal"] = action_pack

        # perform the actions
        for field_coord, target_action_dict in target_action_coords.items():
            if self.field[field_coord] != ".":
                self.perform_action_single_coord(field_coord, target_action_dict)

    def perform_action_single_coord(self, field_coord, target_action_dict):
        """Perform the action on the unit in the given field coordinate."""
        total_hit = 0
        fires = [] # store the fire units for inferno
        victim = self.field[field_coord]

        # attack actions
        for attack in target_action_dict["attacks"]:
            is_attacker_in_field = attack["from"] in self.field

            if not is_attacker_in_field or self.field[attack["from"]] == ".":
                pass

            else:
                attacker = self.field[attack["from"]]
                if attacker.faction == "Fire":
                    fires.append(attacker)

            # save the attack power to calculate the total hit
            attack_power = attack["attack_power"]

            total_hit += attack_power

        if victim.faction == "Earth": # earth units special ability
            total_hit = total_hit // 2
        victim.health -= total_hit

        if victim.health <= 0:
            self.field[field_coord] = "."
            for fire in fires: # if the victim dies, the fire units in the attack list should perform inferno
                fire.inferno()

        # heal action
        if target_action_dict["heal"] is not None: # if there is a heal action
            if victim != ".": # if the unit is still alive
                victim.heal()

    def flood_phase(self):
        """Create the flood packs for the units in the grid."""
        flood_packs = []
        for coord, unit in self.field.items():
            if isinstance(unit, WaterUnit):
                if (self.decide_region(coord[0], coord[1]) == 3) or (self.decide_region(coord[0], coord[1]) == 2):
                    surroundings = {}
                    for i in range(coord[0]-1, coord[0]+2):
                        for j in range(coord[1]-1, coord[1]+2):
                            if i < 0 or i >= self.N or j < 0 or j >= self.N:
                                continue
                            surroundings[(i, j)] = self.field.get((i, j))

                    flood_packs.append(unit.flood(surroundings))

        return flood_packs

    def resolve_floods(self, every_neighbour_flood, flood_packs):
        """Resolve the floods of the units in the grid."""
        flood_coordinates = {}

        for coord in self.field.keys():
            flood_coordinates[coord] = []

        # Neighbour floods
        for neighbour_rank, neighbour_floods in every_neighbour_flood.items():
            for neighbour_flood in neighbour_floods:
                if neighbour_flood["to"] in self.field:
                    flood_coordinates[neighbour_flood["to"]].append(neighbour_flood)

        # Self floods
        for flood_pack in flood_packs:
            if flood_pack["to"] in self.field:
                flood_coordinates[flood_pack["to"]].append(flood_pack)

        # Resolve floods
        for coord, floods in flood_coordinates.items():
            if len(floods) == 0 or floods is None:
                continue

            if len(floods) == 1:
                if floods[0]["to"] in self.field:
                    new_water_unit = self._create_unit("W", floods[0]["to"], self.N)
                    # new_water_unit.attack_power = floods[0]["attack_power"]
                    self.field[floods[0]["to"]] = new_water_unit

            else:
                if floods[0]["to"] in self.field:
                    new_water_unit = self._create_unit("W", floods[0]["to"], self.N)
                    # new_water_unit.attack_power = floods[0]["attack_power"]
                    self.field[floods[0]["to"]] = new_water_unit

    def reset_attack_powers(self):
        """Reset the attack powers of the fire units in the grid."""
        for coord, unit in self.field.items():
            if isinstance(unit, FireUnit):
                unit.attack_power = 4
