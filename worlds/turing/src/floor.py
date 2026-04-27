import copy
import uuid
from .room import Room
from .config import Config
from .utils import print_live
from unaiverse.networking.node.profile import NodeProfile


class Floor:
    def __init__(self, floor_manager: str, id: str,
                 room_ids: list[str] | None = None, managed_guest_profiles: dict[str, NodeProfile] | None = None):
        """Create a floor in the Turing hotel."""

        # Floor identifier and the associated manager
        self.floor_manager = floor_manager
        self.id = id

        # Room identifiers (if not given)
        if room_ids is None or len(room_ids) == 0:
            room_ids = [str(uuid.uuid4()) for _ in range(Config.rooms_per_floor)]

        # Floor structure
        self.rooms: dict[str, Room] = {room_id: Room(room_id) for room_id in room_ids}  # The rooms in this floor

        # Floor guests
        self.guest2room = {}  # A map from guest ID to the room in which the guest is (only for guests in a room)

        # Hotel managers who handled guests (sponsors)
        self.guest2hotel_manager: dict[str, str] = {}

        # Guests managed by the floor manager
        self.managed_guest_profiles = managed_guest_profiles  # Map from guest to its profile

        # Guests that are expected to be here by the hotel manager (in its personal view).
        # Basically, when this object is used to recreate the hotel structure in the hotel manager's view,
        # this the set of guests sponsored by such an hotel manager.
        self.hotel_manager_expected_guests = set()  # This is only operated by a hotel manager

        # Printing facilities
        self.live = None

    def copy_floor_status(self):
        copied_floor = Floor(floor_manager=self.floor_manager, id=self.id,
                             room_ids=["fake"], managed_guest_profiles=None)
        copied_floor.rooms = copy.deepcopy(self.rooms)
        copied_floor.guest2room = copy.deepcopy(self.guest2room)

    def get_guests(self):
        return self.guest2room.keys()

    def get_hotel_manager_of(self, guest: str):
        if guest in self.guest2hotel_manager:
            return self.guest2hotel_manager[guest]
        else:
            return None

    def get_rooms(self):
        return self.rooms.values()

    def get_room(self, room: str):
        if room in self.rooms:
            return self.rooms[room]
        else:
            return None

    def get_room_of(self, guest: str):
        if guest in self.guest2room:
            return self.guest2room[guest]
        else:
            return None

    def get_expected_guests(self):
        return self.hotel_manager_expected_guests

    def is_expected_guest(self, guest: str):
        return guest in self.hotel_manager_expected_guests

    def add_expected_guest(self, guest: str):
        self.hotel_manager_expected_guests.add(guest)

    def remove_expected_guest(self, guest: str):
        self.hotel_manager_expected_guests.discard(guest)

    def is_managed_guest(self, guest: str):
        return guest in self.managed_guest_profiles

    def get_managed_guests(self):
        return list(self.managed_guest_profiles.keys())

    def get_profile_of(self, guest: str):
        if guest in self.managed_guest_profiles:
            return self.managed_guest_profiles[guest]
        else:
            return None

    def is_in_a_room(self, guest: str):
        return guest in self.guest2room

    def insert(self, guest: str, profile: NodeProfile | None, hotel_manager: str, room: Room,
               assign_fake_name: bool = True):
        if room.insert(guest, profile, assign_fake_name):
            self.guest2room[guest] = room
            self.guest2hotel_manager[guest] = hotel_manager
            return True
        else:
            return False

    def eject(self, guest):
        if guest in self.guest2room:
            room = self.guest2room[guest]
            room.eject(guest)
            del self.guest2room[guest]
        if guest in self.guest2hotel_manager:
            del self.guest2hotel_manager[guest]
        self.hotel_manager_expected_guests.discard(guest)

    def print(self, status_msg: str):
        print_live(self, status_msg)
