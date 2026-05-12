"""
       █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
      ░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
       ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░
       ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████
       ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█
       ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
       ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
        ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░░░░  ░░░░░░░░░░
                 A Collectionless AI Project (https://collectionless.ai)
                 Registration/Login: https://unaiverse.io
                 Code Repositories:  https://github.com/collectionlessai/
                 Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi
"""
import copy
import json
from .hotel import Hotel
from .config import Config
from unaiverse.custom import Custom
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.networking.node.profile import NodeProfile
from .utils import parse_vote_msg, compute_check_in_proposals


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Setting system level options
        Custom.MAX_INTERACTIONS = 10000
        Custom.MAX_STREAM_DATA_WITHOUT_INTERACTIONS = 100
        self.im.max_interactions = Custom.MAX_INTERACTIONS

        # The Turing Hotel
        self.hotel = Hotel(self.world_agents)

        # Floor updates identifier
        self._floor_update_tags = {}

        # The proposed check-ins, stored to pass through actions
        self._proposed_check_ins = {}

        # Time marker, for printing facilities
        self._last_update_received_at = "..."
        self._last_guest_send_to_floor_at = "..."

    async def on_tick(self):
        connected_floor_managers = self.get_agents_by_role("floor_manager")
        connected_guests = self.get_agents_by_role("guest")
        self.hotel.print(f"[Managed/Connected] Floor managers: "
                         f"{len(self.hotel.get_floor_managers())}/{len(connected_floor_managers)} "
                         f"| Guests: {len(self.hotel.get_guests())}/{len(connected_guests)}\n"
                         f"Last update: " + self._last_update_received_at +
                         "  | Last check-in: " + self._last_guest_send_to_floor_at)

    def remove_floor_by_floor_manager(self, floor_manager: str):
        floor = self.hotel.get_floor_by_manager(floor_manager)
        if floor is not None:
            if floor.id in self._floor_update_tags:
                del self._floor_update_tags[floor.id]

            # Removing manager and floor
            self.hotel.remove_floor(floor.id)  # This will also remove the floor manager

    async def add_agent(self, peer_id: str, profile: NodeProfile,
                        add_proc_streams: bool = True, add_env_streams: bool = True,
                        add_pubsub_streams: bool = True) -> bool:

        # Ignoring all processor's streams, i.e., only environmental streams of the peer are considered
        return await super().add_agent(peer_id, profile, add_proc_streams=False, add_env_streams=True,
                                       add_pubsub_streams=True)

    async def remove_agent(self, peer_id: str):
        await super().remove_agent(peer_id)

        if peer_id in self.hotel.get_floor_managers():
            self.remove_floor_by_floor_manager(peer_id)
        self.hotel.eject(peer_id)

    @action
    async def discover_floor_managers(self):
        return await self.connect_by_role("floor_manager")

    @action
    async def check_in(self):

        # Getting list of guests to be checked in
        connected_guests = self.get_agents_by_role("guest")
        if len(connected_guests) > 0:

            # A guest to check in is one that is not in a floor, and not even expected-to-be in a floor
            guests_to_check_in = [a for a in connected_guests
                                  if not self.hotel.is_in_a_floor(a) and not self.hotel.is_expected_guest(a)]
        else:
            guests_to_check_in = []
        if len(guests_to_check_in) == 0:
            return False

        # Proposing check-ins accordingly to the current status of the hotel
        proposed_check_ins, _ = compute_check_in_proposals(self.hotel, guests_to_check_in)
        self._proposed_check_ins.update(proposed_check_ins)
        return True

    @action
    async def send_to_floor(self):

        # Getting proposed check-ins and asking guests to reach the proposed floor
        at_least_one_sent = False

        # Shallow copy (in case of disconnections, the attrs starting with "_" are automatically handled)
        proposed_check_ins = self._proposed_check_ins.copy()
        for guest, proposed_check_in in proposed_check_ins.items():
            floor = self.hotel.get_floor(proposed_check_in["floor_id"])

            # Sending to floor
            if not await self.send(action_name="connect_to_floor_manager",
                                   action_kwargs={
                                       "floor_manager": floor.floor_manager
                                   },
                                   from_state="hall",
                                   id="FLOOR",  # There can be only one interaction about connecting to floor manager
                                   target=guest,
                                   volatile=True):
                await self.disconnect(guest)
            else:
                # Remembering this decision
                self.hotel.add_expected_guest(guest, floor)

                self._last_guest_send_to_floor_at = self.clock.get_time_as_string()
                at_least_one_sent = True

        self._proposed_check_ins.clear()
        return at_least_one_sent

    @action
    async def update_hotel(self):
        """
        An update packet is a string that encodes a JSON with the following format:
        
        {
            "floor_id": FLOOR_ID,
            "floor_status": [
                [ROOM_ID, GUEST_COUNT],
                ...   
            ]
            "inserted_guests": [
                [ROOM_ID, GUEST, HOTEL_MANAGER_WHO_HANDLED_THE_GUEST],
                ...   
            ]
            "ejected_guests": [
                [ROOM_ID, GUEST_COUNT],
                ...   
            ]                        
        }
        """

        def _build_update_dict_and_check_format(_update: str) -> dict | None:

            # Packet format
            expected_dict_keys = {"floor_id", "floor_status", "inserted_guests", "ejected_guests"}

            # Converting JSON encoded dict (str) to a real dict and checking format
            if not isinstance(_update, str):
                return None
            try:
                _update_dict = json.loads(_update)
            except Exception:
                return None

            invalid = False
            for expected_key in expected_dict_keys:
                if expected_key not in _update_dict:
                    invalid = True
                    break
                if expected_key != "floor_id":
                    _list = _update_dict[expected_key]
                    if not isinstance(_list, list):
                        invalid = True
                        break
                    for _elem in _list:
                        if expected_key == "floor_status" and len(_elem) != 2:
                            invalid = True
                            break
                        elif expected_key == "inserted_guests" and len(_elem) != 3:
                            invalid = True
                            break
                        elif expected_key == "ejected_guests" and len(_elem) != 2:
                            invalid = True
                            break
                    if invalid:
                        break
            if invalid:
                return None
            return _update_dict

        def _update_floor(_floor_id: str, _update_dict: dict):
            incoherence_detected = False

            # Reference to the floor
            _floor = self.hotel.get_floor(_floor_id)

            # Unknown guests in the floor
            unk_guests = [x for x in _floor.get_guests() if x.startswith(Config.unknown_guest_name)]

            # Handling new ejections of guests
            for (_room_id, _guest) in _update_dict["ejected_guests"]:
                if not self.hotel.is_in_a_floor(_guest):
                    if len(unk_guests) > 0:
                        _guest = unk_guests.pop(0)
                    else:
                        incoherence_detected = True
                elif not _floor.is_in_a_room(_guest) or _floor.get_room_of(_guest).id != _room_id:
                    incoherence_detected = True
                self.hotel.eject(_guest)

            # Handling new insertions of guests
            for (_room_id, _guest, _hotel_manager_who_handled_the_guest) in _update_dict["inserted_guests"]:
                self.hotel.insert(_guest, _floor_id, _room_id, _hotel_manager_who_handled_the_guest)

            return not incoherence_detected

        def _create_or_recreate_floor(_floor_manager: str, _update_dict: dict, _update_tag: int,
                                      _consider_guest_updates: bool, _fill_floor: bool):

            # Killing floor (if existent)
            if _floor_manager in self.hotel.get_floor_managers():
                self.remove_floor_by_floor_manager(_floor_manager)

            # Creating floor
            self.hotel.add_floor(floor_id=_update_dict["floor_id"], floor_manager=_floor_manager,
                                 room_ids=[_room_id for _room_id, _ in _update_dict["floor_status"]])

            # Reference to the floor
            _floor = self.hotel.get_floor(_update_dict["floor_id"])

            # Inserting/ejecting
            if _consider_guest_updates:
                _update_floor(_update_dict["floor_id"], _update_dict)  # Here we do not check the return value

            # Saving update tag
            self._floor_update_tags[_update_dict["floor_id"]] = _update_tag

            # Filling floor
            if _fill_floor:

                # Filling with unknowns
                for _room_id, _guest_count in _update_dict["floor_status"]:
                    _room = _floor.get_room(_room_id)
                    current_count = _room.count_guests()
                    for i in range(current_count, _guest_count):
                        j = 0
                        while True:
                            unk_name = Config.unknown_guest_name + str(j)
                            if self.hotel.is_in_a_floor(unk_name):
                                j += 1
                                continue
                            else:
                                self.hotel.insert(unk_name, _floor.id, _room_id,
                                                  hotel_manager_who_handled_the_guest=Config.unknown_guest_name)
                                break

        # Getting update data, if any
        for floor_manager in self.get_agents_by_role("floor_manager"):  # Considers floor manager with handshake done

            # Getting the stream where updates are sent
            floor_stream = self.get_stream("floor_updates", floor_manager)

            if floor_stream is None:
                log.error("Found a weird floor manager without any floor_updates streams, disconnecting!")
                await self.disconnect(floor_manager)
                continue

            # Getting all samples stored in such a stream (all UUIDs)
            updates = floor_stream.get("update_hotel", all_uuids=True)

            # For each update packet (one per UUID)...
            for (update_str, update_tag, update_time) in updates:

                # Filtering out empty packets
                if update_str is None:
                    continue

                # Building dict (and checking format)
                update_dict = _build_update_dict_and_check_format(update_str)
                if update_dict is None:
                    log.error(f"Received an invalid format floor update packet "
                              f"from floor manager {floor_manager}. Update packet (str) is: {update_str}")
                    continue

                # Checking tags (for already known floors only)
                floor_id = update_dict["floor_id"]
                if floor_id in self._floor_update_tags:

                    # If a tag is older that the last received one, we skip it
                    if self._floor_update_tags[floor_id] >= update_tag:
                        log.error(f"Received an invalid floor update packet "
                                  f"with tag {update_tag}. The last received tag was "
                                  f"{self._floor_update_tags[floor_id]}")
                        continue

                    # If some tags were missed, the floor is rebuilt
                    if (self._floor_update_tags[floor_id] + 1) != update_tag:
                        log.error(f"Received a floor update packet "
                                  f"with tag {update_tag}, and the last received tag was "
                                  f"{self._floor_update_tags[floor_id]}: "
                                  f"something was missed, resetting floor")
                        _create_or_recreate_floor(floor_manager, update_dict, update_tag,
                                                  _consider_guest_updates=True, _fill_floor=True)

                # Is this a new floor or not?
                if floor_manager not in self.hotel.get_floor_managers():

                    # When we get the first update from a floor manager that is not in the hotel object,
                    # then we create the floor and its rooms, inserting dummy guests
                    _create_or_recreate_floor(floor_manager, update_dict, update_tag,
                                              _consider_guest_updates=True, _fill_floor=True)
                else:

                    # Handling new insertion/ejections of guests
                    if not _update_floor(floor_id, update_dict):

                        # Some issue were found while trying to update the floor, let's kill it
                        _create_or_recreate_floor(floor_manager, update_dict, update_tag,
                                                  _consider_guest_updates=True, _fill_floor=True)
                    else:

                        # Saving update tag
                        self._floor_update_tags[update_dict["floor_id"]] = update_tag

                # Checking issues after update
                floor = self.hotel.get_floor(floor_id)
                for room_id, guest_count in update_dict["floor_status"]:

                    # Discrepancies
                    if floor.get_room(room_id).count_guests() != guest_count:
                        log.error(f"Floor manager {floor_manager} (floor {floor.id}) "
                                  f"communicated {guest_count} in room {room_id}, that is not coherent with the "
                                  f"local reconstruction ({floor.get_room(room_id).count_guests()}), resetting floor")
                        _create_or_recreate_floor(floor_manager, update_dict, update_tag,
                                                  _consider_guest_updates=True, _fill_floor=True)

                    # Floor managers doing a weird job (do this AFTER having checked for discrepancies,
                    # so it the floor is rebuilt, we will check it again)
                    if (floor.get_room(room_id).count_guests() >
                            Config.max_guests_per_room + Config.max_overbooked_guests):
                        log.error(f"Floor manager {floor_manager} (floor {floor.id}) "
                                  f"communicated {guest_count} in room {room_id}, that above the maximum allowed "
                                  f"({Config.max_guests_per_room + Config.max_overbooked_guests}), "
                                  f"disconnecting floor manager and removing floor")
                        await self.disconnect(floor_manager)

                self._last_update_received_at = self.clock.get_time_as_string()

        # Storing stats.
        # The first hotel manager is the head of the whole hotel managers, responsible for sending stats to the world.
        # First in alphabetical order.
        all_hotel_managers = self.get_agents_by_role(role="hotel_manager", handshake_completed=False)
        is_head_of_hotel_managers = len(all_hotel_managers) > 0 and min(all_hotel_managers) == self.get_peer_id()

        if is_head_of_hotel_managers:
            int_timestamp = self.clock.get_time_ms(monotonic=True)
            world_peer_id = self.get_connection_pool_manager().get_world_peer_id()

            # Referring to stats.py: CUSTOM_OUTER_STATS_DYNAMIC_SCHEMA
            self.stats.store_stat("hotel_n_floors_active", len(self.hotel.get_floors()),
                                  group_key=world_peer_id, timestamp=int_timestamp)
            self.stats.store_stat("hotel_n_rooms_active", self.hotel.count_not_empty_rooms(),
                                  group_key=world_peer_id, timestamp=int_timestamp)
            self.stats.store_stat("hotel_n_rooms_overbooked", self.hotel.count_overbooked_rooms(),
                                  group_key=world_peer_id, timestamp=int_timestamp)
            self.stats.store_stat("hotel_n_agents_present",
                                  len(self.hotel.get_all_hotel_guests()) - self.hotel.count_guests_in_the_hall(),
                                  group_key=world_peer_id, timestamp=int_timestamp)
            self.stats.store_stat("hotel_n_agents_waiting", self.hotel.count_guests_in_the_hall(),
                                  group_key=world_peer_id, timestamp=int_timestamp)
            self.stats.store_stat("n_total_agents",
                                  len(self.hotel.get_all_hotel_guests()),
                                  group_key=world_peer_id, timestamp=int_timestamp)

    @action
    async def send_violations(self):
        violations = {}

        for guest in self.hotel.get_managed_guests():
            floor = self.hotel.get_floor_of(guest)
            if floor is not None:
                hotel_manager = floor.get_hotel_manager_of(guest)
                expected_guest_of_this_floor = floor.is_expected_guest(guest)
                expected_guest_of_this_manager = self.hotel.is_expected_guest(guest)

                # If this manager was expected to be the manager of a guest, and he is not, or, if this manager was NOT
                # expected to be the manager of a guest, but it looks like he actually is...signal a violation!!!!
                if ((hotel_manager == self.get_peer_id() and not expected_guest_of_this_floor) or
                        (hotel_manager != self.get_peer_id() and expected_guest_of_this_floor)):
                    if floor.id not in violations:
                        violations[floor.id] = []
                    violations[floor.id].append(guest)

                # Aligning expectations with the hotel status communicated by the floor: it is up to the floor to
                # decide whether to eject the guest or not (the hotel manager goes Ponzio Pilato)
                if hotel_manager == self.get_peer_id() and not expected_guest_of_this_floor:
                    if expected_guest_of_this_manager:
                        self.hotel.remove_expected_guest(guest)  # It was in another expected floor
                    self.hotel.add_expected_guest(guest, floor)
                elif hotel_manager != self.get_peer_id() and expected_guest_of_this_manager:
                    self.hotel.remove_expected_guest(guest)

        # Sending violations
        for floor_id, guests in violations.items():
            # Sending violation to a floor
            await self.send(action_name="apply_violations",
                            from_state="votes_sent",
                            action_kwargs={"guests": guests},
                            target=self.hotel.get_floor(floor_id).floor_manager,
                            volatile=True)

    @action
    async def get_votes(self):
        """Get votes from the floor manager's "votes" stream.

        A vote sample is a string that encodes a list of JSONs, each with the following format:

        {
            "voter": VOTER_UNAID,
            "voter_nature": "human" | "ai,
            "vote": FULL_VOTE_MESSAGE,
            "ground_truth": (DICT) CANDIDATE_VOTEE_FAKE_NAME -> ("human" | "ai", CANDIDATE_VOTEE_UNAID),
            "session_id": FLOOR_ID:ROOM_ID,
            "floor_manager": FLOOR_MANAGER_PEER_ID,
            "hotel_manager": HOTEL_MANAGER_PEER_ID,
            "msgs_from_votee": (DICT) CANDIDATE_VOTEE_FAKE_NAME -> STRING_REPRESENTING_A_NUMBER,
            "msgs_from_voter": (DICT) CANDIDATE_VOTEE_FAKE_NAME -> STRING_REPRESENTING_A_NUMBER,
        }

        and it is converted into multiple dictionaries
        (one per each CANDIDATE_VOTEE_FAKE_NAME found by parsing FULL_VOTE_MESSAGE) stored as stats:

        {
            "voter": VOTER_UNAID,
            "voter_nature": "human" | "ai,
            "vote": "human" | "ai",
            "ground_truth": "human" | "ai"
            "session_id": FLOOR_ID:ROOM_ID,
            "floor_manager": FLOOR_MANAGER_PEER_ID,
            "hotel_manager": HOTEL_MANAGER_PEER_ID,
            "msgs_from_votee": STRING_REPRESENTING_A_NUMBER,
            "msgs_from_voter": STRING_REPRESENTING_A_NUMBER
        }
        """

        def _build_vote_dicts_and_check_format(_vote: str) -> list[dict] | None:

            # Packet format
            expected_dict_keys = ["voter", "voter_nature", "vote", "ground_truth", "session_id",
                                  "floor_manager", "hotel_manager", "msgs_from_votee", "msgs_from_voter"]

            # Converting JSON encoded dict (str) to a real dict and checking format
            if not isinstance(_vote, str):
                return None
            try:
                _list_of_vote_dicts = json.loads(_vote)
            except Exception:
                return None

            _list_of_valid_vote_dicts = []
            for _vote_dict in _list_of_vote_dicts:
                invalid = False
                fake_names = set()
                for expected_key in expected_dict_keys:
                    if expected_key not in _vote_dict:
                        invalid = True
                        break
                    _val = _vote_dict[expected_key]
                    if expected_key == "ground_truth":
                        if not isinstance(_val, dict):
                            invalid = True
                            break
                        for _k in _val.keys():
                            fake_names.add(_k)
                        for _k, _v in _val.items():
                            if len(_v) != 2:
                                invalid = True
                                break
                            else:
                                if _v[0] != "human" and _v[0] != "ai":
                                    invalid = True
                                    break
                                if "@" not in _v[1] or "/" not in _v[1]:
                                    invalid = True
                                    break
                        if invalid:
                            break
                    elif expected_key == "msgs_from_votee" or expected_key == "msgs_from_voter":
                        if not isinstance(_val, dict):
                            invalid = True
                            break
                        if len(_val) != len(fake_names):
                            invalid = True
                        if not invalid:
                            for _k in _val.keys():
                                if _k not in fake_names:
                                    invalid = True
                                    break
                        if invalid:
                            break
                    elif not isinstance(_val, str):
                        invalid = True
                        break

                    # Converting votes to integer
                    try:
                        for _k, _v in _vote_dict["msgs_from_votee"].items():
                            _vote_dict["msgs_from_votee"][_k] = int(_v)
                        for _k, _v in _vote_dict["msgs_from_voter"].items():
                            _vote_dict["msgs_from_voter"][_k] = int(_v)
                    except Exception:
                        invalid = True
                        break
                if invalid:
                    continue
                else:
                    _list_of_valid_vote_dicts.append(_vote_dict)
            return _list_of_valid_vote_dicts

        hotel_manager_peer_id = self.get_peer_id()

        # Getting the stream where votes are sent: all floor manager might send votes
        for floor_manager in self.get_agents_by_role("floor_manager"):
            votes_stream = self.get_stream("votes", floor_manager)

            if votes_stream is None:
                log.error("Found a weird floor manager without any vote-related streams, disconnecting!")
                await self.disconnect(floor_manager)
                continue

            # Getting all samples stored in such a stream (all UUIDs)
            votes = votes_stream.get("get_votes", all_uuids=True)

            for vote_str, _, _ in votes:

                # Filtering out empty packets
                if vote_str is None:
                    continue

                # Building dict (and checking format)
                list_of_vote_dicts = _build_vote_dicts_and_check_format(vote_str)
                if list_of_vote_dicts is None or len(list_of_vote_dicts) == 0:
                    log.error(f"Received an invalid format vote packet "
                              f"from floor manager {floor_manager}. Vote packet (str) is: {vote_str}")
                    continue

                for vote_dict in list_of_vote_dicts:

                    # Augmenting vote dict with hotel manager-related information or specific actions
                    # Checking the actual manager (to be extra sure... actually, it should be already there), and
                    # the floor manager. Checking also the number of exchanged messages
                    if (hotel_manager_peer_id != vote_dict["hotel_manager"] or
                            vote_dict["floor_manager"] != floor_manager):
                        log.error(f"Invalid vote received: the actual hotel manager ({hotel_manager_peer_id} or "
                                  f"the actual floor manager ({floor_manager}) is not the one "
                                  f"in the vote: {vote_dict})")
                        continue

                    # Counting messages from votee
                    fake_names_to_ignore = set()
                    for k, v in vote_dict["msgs_from_votee"].items():
                        if v < Config.min_msgs_from_votee:
                            fake_names_to_ignore.add(k)

                    # Parsing vote
                    parsed_vote = parse_vote_msg(vote_dict["vote"])  # Dict fake-name (votee) to "human" | "ai"

                    # Reversing the logic: the index is the votee, hence the vote dictionary must be replicated for each
                    # votee of in the parsed vote structure
                    for fake_name, classification in parsed_vote.items():

                        # Ignoring votes associated to too few exchanges with the votee
                        if fake_name in fake_names_to_ignore:
                            continue

                        # Ignoring votes associated to agents that were not there at all (or wrong parsing results)
                        if fake_name not in vote_dict["ground_truth"]:
                            continue

                        _vote_dict_ = copy.deepcopy(vote_dict)
                        _vote_dict_["vote"] = classification
                        _vote_dict_["ground_truth"] = vote_dict["ground_truth"][fake_name][0]
                        _vote_dict_["msgs_from_votee"] = vote_dict["msgs_from_votee"][fake_name]
                        _vote_dict_["msgs_from_voter"] = vote_dict["msgs_from_voter"][fake_name]
                        _votee_unaid_ = vote_dict["ground_truth"][fake_name][1]

                        # Storing vote as stat (group_key = votee UNaID so votes are bucketed per votee)
                        int_timestamp = self.clock.get_time_ms(monotonic=True)
                        self.stats.store_stat("turing_vote", _vote_dict_,
                                              group_key=_votee_unaid_, timestamp=int_timestamp)

    @action
    async def guest_back_to_hall(self, guest: str | None = None):
        self.hotel.eject(guest)
        return True
