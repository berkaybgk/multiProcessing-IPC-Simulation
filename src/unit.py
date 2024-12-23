from abc import ABC, abstractmethod
from typing import Tuple, List, Dict


class Unit(ABC):
    """Abstract class for the units."""
    def __init__(self, faction, health, attack_power, healing_rate, N, coordinate: Tuple[int, int]):
        self.faction = faction
        self.health = health
        self.attack_power = attack_power
        self.healing_rate = healing_rate
        self.coordinate = coordinate  # (x, y) position on the grid
        self.did_attack_this_round = False
        self.max_health = None
        self.N = N

    @abstractmethod
    def attack_pattern(self):
        """Return the attack pattern as a list of relative positions."""
        pass

    def heal(self):
        """Heals the unit if not attacking."""
        self.health = min(self.max_health, self.health + self.healing_rate)

    def action(self, surroundings):
        """Decides the action to take based on the surroundings. Heal or attack"""
        attack_packs = []
        for coord, unit in surroundings.items():
            if unit == "." or unit.faction == self.faction:
                continue

            attack_packs.append({
                "type": "attack",
                "from": self.coordinate,
                "to": coord,
                "attack_power": self.attack_power,
            })

        if len(attack_packs) == 0:
            return [self.get_healing_pack()]

        return attack_packs

    def get_healing_pack(self):
        """Returns a healing pack for the unit."""
        return {
            "type": "heal",
            "coord": self.coordinate
        }

    def __str__(self):
        if self.faction == "Water":
            return "W"
        elif self.faction == "Earth":
            return "E"
        elif self.faction == "Fire":
            return "F"
        elif self.faction == "Air":
            return "A"
        return


class EarthUnit(Unit):
    """Earth Unit class"""
    def __init__(self, coordinate: Tuple[int, int], N):
        super().__init__(faction="Earth", health=18, attack_power=2, healing_rate=3, N=N, coordinate=coordinate)
        self.max_health = 18

    def attack_pattern(self) -> List[Tuple[int, int]]:
        """Earth units attack direct neighbors."""
        return [(-1, 0), (1, 0), (0, -1), (0, 1)]


class FireUnit(Unit):
    """Fire Unit class"""
    def __init__(self, coordinate: Tuple[int, int], N):
        super().__init__(faction="Fire", health=12, attack_power=4, healing_rate=1, N=N, coordinate=coordinate)
        self.max_attack_power = 6
        self.max_health = 12

    def attack_pattern(self) -> List[Tuple[int, int]]:
        """Fire units attack all 8 neighboring cells."""
        return [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def inferno(self):
        """Increases the attack power of the fire unit by 1. Caps at 6."""
        self.attack_power = min(6, self.attack_power+1)


class WaterUnit(Unit):
    """Water Unit class"""
    def __init__(self, coordinate: Tuple[int, int], N):
        super().__init__(faction="Water", health=14, attack_power=3, healing_rate=2, N=N, coordinate=coordinate)
        self.max_health = 14

    def attack_pattern(self) -> List[Tuple[int, int]]:
        """Water units attack diagonally adjacent cells."""
        return [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    def flood(self, surroundings: Dict):
        """Calculates and sends the best flood position for the water unit."""
        best_flood_position = None

        for coord, unit in surroundings.items():
            if unit != ".":
                continue

            if best_flood_position == None:
                best_flood_position = coord
                continue

            if coord[0] < best_flood_position[0]:
                best_flood_position = coord
            elif coord[0] == best_flood_position[0]:
                if coord[1] < best_flood_position[1]:
                    best_flood_position = coord

        # Return a flood pack
        return {
            "type": "flood",
            "from": self.coordinate,
            "to": best_flood_position,
            "attack_power": self.attack_power,
        }


class AirUnit(Unit):
    """Air Unit class"""
    def __init__(self, coordinate: Tuple[int, int], N):
        super().__init__(faction="Air", health=10, attack_power=2, healing_rate=2, N=N, coordinate=coordinate)
        self.max_health = 10

    def attack_pattern(self) -> List[Tuple[int, int]]:
        """Air units attack all neighboring cells and skip over neutral cells."""
        return [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def move(self, surroundings: Dict):
        """Calculates and sends the best move for the air unit."""

        _ = surroundings.pop(self.coordinate) # remove the air unit from the surroundings
        surroundings[self.coordinate] = "." # put a neutral cell in the air unit's place


        # initial attackable enemies
        initial_attackable_enemies = self.calculate_attackable_enemies(self.coordinate, surroundings)
        max_attackable_pos = (self.coordinate, initial_attackable_enemies)

        for i in range(-1, 2):
            for j in range(-1, 2):
                new_position = (self.coordinate[0] + i, self.coordinate[1] + j)

                if new_position[0] < 0 or new_position[0] >= self.N or new_position[1] < 0 or new_position[1] >= self.N:
                    continue

                if surroundings[new_position] != ".":
                    continue

                # calculate the number of attackable enemies from the new position
                attackable_enemies = self.calculate_attackable_enemies(new_position, surroundings)

                if attackable_enemies == initial_attackable_enemies:
                    continue

                # update the max attackable position
                if attackable_enemies > max_attackable_pos[1]:
                    max_attackable_pos = (new_position, attackable_enemies)
                elif attackable_enemies == max_attackable_pos[1]:
                    old_row, old_col = max_attackable_pos[0]
                    new_row, new_col = new_position
                    if new_row < old_row:
                        max_attackable_pos = (new_position, attackable_enemies)
                    elif new_row == old_row:
                        if new_col < old_col:
                            max_attackable_pos = (new_position, attackable_enemies)

        # Return a move pack
        return {
            "type": "move",
            "from": self.coordinate,
            "to": max_attackable_pos[0],
            "health": self.health,
            "attack_power": self.attack_power,
            "health_rate": self.healing_rate
        }

    def calculate_attackable_enemies(self, moved_position, surroundings):
        """Calculates the number of attackable enemies from a given position."""
        attackable_enemies = 0
        for attack_direction in self.attack_pattern():
            attack_position = (moved_position[0] + attack_direction[0], moved_position[1] + attack_direction[1])

            if attack_position[0] < 0 or attack_position[0] >= self.N or attack_position[1] < 0 or attack_position[1] >= self.N:
                continue

            # attacking 1 cell away
            if surroundings[attack_position] != "." and surroundings[attack_position].faction != self.faction:
                attackable_enemies += 1

            # attacking 2 cells away
            if surroundings[attack_position] == ".":
                attack_direction = (2 * attack_direction[0], 2 * attack_direction[1])
                attack_position = (moved_position[0] + attack_direction[0], moved_position[1] + attack_direction[1])

                if surroundings[attack_position] != "." and surroundings[attack_position].faction != self.faction:
                    attackable_enemies += 1

        # return the number of attackable enemies
        return attackable_enemies
