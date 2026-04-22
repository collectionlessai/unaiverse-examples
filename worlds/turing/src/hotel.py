from .room import Room
from .floor import Floor
from .config import Config
from .utils import print_live
from unaiverse.networking.node.profile import NodeProfile


class Hotel:

    def __init__(self, managed_guest_profiles: dict[str, NodeProfile]):
        """Create a Turing hotel, composed of multiple floors, each of them composed of multiple rooms.

        Args:
            managed_guest_profiles: A dictionary of known guest profiles, where to search for guest information.
                It is a map from peer ID to node profile.
        """

        # Hotel structure
        self.floors: dict[str, Floor] = {}  # The floors of the hotel (floor ID to floor object)
        self.rooms: dict[str, Room] = {}  # The rooms of the hotel (room ID to room object)
        self.room2floor: dict[str, Floor] = {}  # Room ID to floor object

        # Hotel guests
        self.guest2floor = {}  # A map from guest ID to the floor in which the guest is (only for guests in a floor)
        self.guest2hotel_manager_expected_floor = {}

        # Floor managers:
        self.floor_manager2floor = {}

        # Guests managed by the manager who instantiated this object
        self.managed_guest_profiles = managed_guest_profiles  # Read-only! Map from guest to its profile

        # Printing facilities
        self.live = None

    def get_floor_managers(self):
        return self.floor_manager2floor.keys()

    def get_floor_by_manager(self, floor_manager: str):
        if floor_manager in self.floor_manager2floor:
            return self.floor_manager2floor[floor_manager]
        else:
            return None

    def get_floors(self):
        return self.floors.values()

    def get_floor(self, floor: str) -> Floor | None:
        if floor in self.floors:
            return self.floors[floor]
        else:
            return None

    def get_floor_of(self, guest: str) -> Floor | None:
        if guest in self.guest2floor:
            return self.guest2floor[guest]
        else:
            return None

    def get_floor_of_room(self, room: str) -> Floor | None:
        if room in self.room2floor:
            return self.room2floor[room]
        else:
            return None

    def get_expected_floor_of(self, guest: str) -> Floor | None:
        if guest in self.guest2hotel_manager_expected_floor:
            return self.guest2hotel_manager_expected_floor[guest]
        else:
            return None

    def get_expected_guests(self):
        return self.guest2hotel_manager_expected_floor.keys()

    def is_expected_guest(self, guest: str):
        return self.get_expected_floor_of(guest) is not None

    def get_guests(self):
        return self.guest2floor.keys()

    def get_rooms(self):
        return self.rooms.values()

    def count_not_empty_rooms(self):
        return sum(1 for room in self.get_rooms() if room.count_guests() > 0)

    def count_overbooked_rooms(self):
        return sum(1 for room in self.get_rooms() if room.count_guests() > Config.max_guests_per_room)

    def count_guests_in_the_hall(self):
        return sum(1 for guest in self.get_all_hotel_guests() if not self.is_in_a_floor(guest))

    def get_all_hotel_guests(self):
        return list(self.guest2floor.keys())

    def is_managed_guest(self, guest: str):
        return guest in self.managed_guest_profiles

    def get_managed_guests(self):
        return list(self.managed_guest_profiles.keys())

    def get_profile_of(self, guest: str):
        if guest in self.managed_guest_profiles:
            return self.managed_guest_profiles[guest]
        else:
            return None

    def is_in_a_floor(self, guest: str):
        return guest in self.guest2floor

    def add_expected_guest(self, guest: str, floor: Floor):
        floor.add_expected_guest(guest)
        self.guest2hotel_manager_expected_floor[guest] = floor

    def remove_expected_guest(self, guest: str):
        floor = self.get_expected_floor_of(guest)
        if floor is not None:
            floor.remove_expected_guest(guest)

    def insert(self, guest: str, floor_id: str, room_id: str, hotel_manager_who_handled_the_guest: str):
        if floor_id in self.floors and room_id in self.rooms:
            floor = self.get_floor(floor_id)
            room = floor.get_room(room_id)
            floor.insert(guest, self.get_profile_of(guest), hotel_manager_who_handled_the_guest, room,
                         assign_fake_name=False)  # Do not assign nicks
            self.guest2floor[guest] = floor

    def eject(self, guest: str):
        if guest in self.guest2floor:
            floor = self.guest2floor[guest]
            floor.eject(guest)
            del self.guest2floor[guest]
        if guest in self.guest2hotel_manager_expected_floor:
            floor = self.guest2hotel_manager_expected_floor[guest]
            floor.eject(guest)
            del self.guest2hotel_manager_expected_floor[guest]

    def add_floor(self, floor_id: str, floor_manager: str, room_ids: list[str]):
        if floor_id not in self.floors:

            # Creating a new floor, associating the manager to it
            floor = Floor(floor_manager, floor_id, room_ids)

            # Saving associations
            self.floors[floor_id] = floor
            self.floor_manager2floor[floor_manager] = floor

            # Updating room list
            for room in floor.get_rooms():
                self.rooms[room.id] = room
                self.room2floor[room.id] = floor

    def remove_floor(self, floor_id: str):
        if floor_id in self.floors:
            floor = self.floors[floor_id]

            if floor.floor_manager in self.floor_manager2floor:
                del self.floor_manager2floor[floor.floor_manager]

            # Checking-out all the guests of the removed floor (from the hotel perspective)
            guests = list(floor.get_guests())  # Shallow
            for guest in guests:
                self.eject(guest)

            # Removing all rooms (from the hotel perspective)
            rooms = list(floor.get_rooms())  # Shallow
            for room in rooms:
                if room.id in self.rooms:
                    del self.rooms[room.id]
                if room.id in self.room2floor:
                    del self.room2floor[room.id]

            # Removing floor
            del self.floors[floor_id]

    def print(self, status_msg: str):
        print_live(self, status_msg)
