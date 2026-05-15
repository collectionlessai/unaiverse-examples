import time
import string
from .config import Config
from unaiverse.agent import Agent
from unaiverse.utils.misc import build_unaid
from unaiverse.networking.node.profile import NodeProfile


class Room:
    def __init__(self, id: str):
        """Create a room in the Turing hotel.

        Every room is composed of guests, identified by their peer IDs (strings) and having a fake name as
        'A', 'B', 'C', ... etc. It also stores the profile of each guest, and, if needed, there are also
        separated maps for HUMAN and ARTIFICIAL guests.

        Args:
            id: the id of the room in the list of rooms of the hotel.
        """
        self.id = id

        self.guests: dict[str, NodeProfile] = {}  # peer ID -> profile (ALL guests)
        self.human_guests: dict[str, NodeProfile] = {}  # peer ID -> profile (HUMAN guests only)
        self.artificial_guests: dict[str, NodeProfile] = {}  # peer ID -> profile (ARTIFICIAL guests only)
        self.temp_guests: set[str] = set()

        self.fake_names = Room.__make_fake_names()  # Generate names such as 'A', 'B', 'C', ...
        self.next_fake_name_index = 0
        self.guest2fake: dict[str, str] = {}  # peer ID -> fake name
        self.fake2cached_info: dict[str, tuple[str, bool, str]] = {}  # fake name -> (peer ID, is a human?, unaid)
        self.guest2insert_time: dict[str, float] = {}
        self.guest2status_time: dict[str, float] = {}  # peer ID -> float time
        self.guest2status: dict[str, object] = {}  # peer ID -> status object

        self.msgs_sent_by_fake_to_fake: dict[str, dict[str, int]] = {}  # peer ID, peer ID -> number of exchanges
        self.msgs_recv_by_fake_from_fake: dict[str, dict[str, int]] = {}  # peer ID, peer ID -> number of exchanges

        assert len(self.fake_names) >= (Config.max_guests_per_room + Config.max_overbooked_guests)

    def get_guests(self):
        return self.guests

    def get_time_spent_in_room_by(self, guest):
        if guest in self.guest2insert_time:
            return int(time.perf_counter() - self.guest2insert_time[guest])
        else:
            return 0

    def get_fake_names_met_by(self, fake_name: str):
        if fake_name not in self.msgs_recv_by_fake_from_fake:
            return set()
        return self.msgs_recv_by_fake_from_fake[fake_name].keys() - {fake_name}

    def set_status(self, guest, status: object):
        self.guest2status[guest] = status
        self.guest2status_time[guest] = time.perf_counter()

    def get_status(self, guest):
        if guest in self.guest2status:
            return self.guest2status[guest]
        else:
            return None

    def get_time_in_current_status(self, guest):
        if guest in self.guest2status_time:
            return int(time.perf_counter() - self.guest2status_time[guest])
        else:
            return 0.

    def count_messages_sent_by(self, fake_name: str, to_fake_name: str):
        if fake_name in self.msgs_sent_by_fake_to_fake and to_fake_name in self.msgs_sent_by_fake_to_fake[fake_name]:
            return self.msgs_sent_by_fake_to_fake[fake_name][to_fake_name]
        else:
            return 0

    def count_messages_recv_by(self, fake_name: str, from_fake_name: str):
        if (fake_name in self.msgs_recv_by_fake_from_fake and
                from_fake_name in self.msgs_recv_by_fake_from_fake[fake_name]):
            return self.msgs_recv_by_fake_from_fake[fake_name][from_fake_name]
        else:
            return 0

    def inc_message_exchanges(self, fake_name_from: str, fake_name_to: str):
        self.msgs_sent_by_fake_to_fake.setdefault(fake_name_from, {}).setdefault(fake_name_to, 0)
        self.msgs_sent_by_fake_to_fake[fake_name_from][fake_name_to] += 1
        self.msgs_recv_by_fake_from_fake.setdefault(fake_name_to, {}).setdefault(fake_name_from, 0)
        self.msgs_recv_by_fake_from_fake[fake_name_to][fake_name_from] += 1

    def get_fake_names_seen_by(self, fake_name: str):
        recv_from = self.msgs_recv_by_fake_from_fake.get(fake_name, {}).keys()
        sent_to = self.msgs_sent_by_fake_to_fake.get(fake_name, {}).keys()
        return sent_to | recv_from

    def count_human_guests(self):
        return len(self.human_guests)

    def count_artificial_guests(self):
        return len(self.artificial_guests)

    def count_guests(self, count_temp_too: bool = False):
        if not count_temp_too:
            return len(self.guests)
        else:
            return len(self.guests) + len(self.temp_guests)

    def is_in_room(self, peer_id):
        return peer_id in self.guests

    def clear_temp_assignments(self):
        self.temp_guests.clear()

    def add_temp_assignment(self, guest: str):
        self.temp_guests.add(guest)

    def insert(self, guest: str, profile: NodeProfile | None, assign_fake_name: bool = True) -> bool:
        fake_name = None
        if assign_fake_name:

            # Checking the fake names of the oldest guest, to avoid clashes
            oldest_fake_name = self.fake_name_of(next(iter(self.guests))) if len(self.guests) > 0 else None

            # Attaching a fake name to the guest (ensuring it is not shared by another guest already in the room)
            fake_name = self.fake_names[self.next_fake_name_index]
            self.next_fake_name_index = (self.next_fake_name_index + 1) % len(self.fake_names)
            if fake_name == oldest_fake_name:
                return False  # Clash
            while fake_name in self.fake2cached_info and self.is_in_room(self.fake2cached_info[fake_name][0]):
                fake_name = self.fake_names[self.next_fake_name_index]
                self.next_fake_name_index = (self.next_fake_name_index + 1) % len(self.fake_names)
                if fake_name == oldest_fake_name:
                    return False  # Clash

            self.guest2fake[guest] = fake_name

        self.guests[guest] = profile
        self.guest2insert_time[guest] = time.perf_counter()

        # This must be done BEFORE calling self.is_human(guest) - see below
        if profile is not None:
            is_human = profile.get_static_profile()["node_type"] == Agent.HUMAN
            if is_human:
                self.human_guests[guest] = profile
            else:
                self.artificial_guests[guest] = profile

        if fake_name is not None:
            self.fake2cached_info[fake_name] = (guest, self.is_human(guest), build_unaid(profile))
        return True

    def eject(self, guest: str):
        if self.is_in_room(guest):
            fake_name = self.fake_name_of(guest)
            del self.guests[guest]
            if guest in self.guest2fake:
                del self.guest2fake[guest]
            if guest in self.human_guests:
                del self.human_guests[guest]
            if guest in self.artificial_guests:
                del self.artificial_guests[guest]
            if guest in self.guest2insert_time:
                del self.guest2insert_time[guest]
            if guest in self.guest2status:
                del self.guest2status[guest]
            if guest in self.guest2status_time:
                del self.guest2status_time[guest]
            if fake_name in self.msgs_sent_by_fake_to_fake:
                del self.msgs_sent_by_fake_to_fake[fake_name]
            if fake_name in self.msgs_recv_by_fake_from_fake:
                del self.msgs_recv_by_fake_from_fake[fake_name]
            if self.count_guests() == 0:
                self.next_fake_name_index = 0
                self.fake2cached_info.clear()

    def fake_name_of(self, guest: str):
        if guest in self.guest2fake:
            return self.guest2fake[guest]
        else:
            return None

    def guest_whose_fake_name_is(self, fake_name: str):
        if fake_name in self.fake2cached_info:
            return self.fake2cached_info[fake_name][0]
        else:
            return None

    def is_human(self, guest: str):
        if guest not in self.guests:
            return None
        return guest in self.human_guests

    def is_artificial(self, guest: str):
        if guest not in self.guests:
            return None
        return guest in self.artificial_guests

    def get_unaid_of(self, guest):
        if guest in self.guests:
            return build_unaid(self.guests[guest])
        else:
            return None

    def get_unaid_of_fake_name(self, fake_name):
        if fake_name in self.fake2cached_info:
            return self.fake2cached_info[fake_name][2]
        else:
            return None

    def get_ground_truth_of(self, guest):
        is_human = self.is_human(guest)
        if is_human is None:
            return None
        return "human" if is_human else "ai"

    def get_ground_truth_of_fake_name(self, fake_name):
        if fake_name not in self.fake2cached_info:
            return None
        is_human = self.fake2cached_info[fake_name][1]
        return "human" if is_human else "ai"

    def get_fake_names(self):
        return self.fake_names

    @staticmethod
    def __make_fake_names():
        alphabet = string.ascii_uppercase
        max_names = 26
        names = []
        for i in range(max_names):
            letter = alphabet[i % len(alphabet)]
            suffix = (i // len(alphabet)) + 1 if max_names > len(alphabet) else 0
            names.append(letter if suffix == 0 else f"{letter}{suffix}")
        return names
