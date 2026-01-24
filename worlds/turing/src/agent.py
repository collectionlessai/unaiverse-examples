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
import uuid
import string
import random
import time as ttime
from datetime import datetime
from unaiverse.agent import Agent
from unaiverse.dataprops import DataProps
from unaiverse.networking.node.profile import NodeProfile
from unaiverse.streams import DataStream, BufferedDataStream
from unaiverse.utils.misc import GenException, has_human_processor


class WAgent(Agent):

    # Generic options to configure the Turing Test Hotel
    profile_link = ("https://docs.google.com/forms/d/e/1FAIpQLScF6FuSMDFpowk3bfLzrr35tGErxd864Rf7FuZI9ic8p-nQAg/"
                    "viewform?usp=pp_url&entry.1591917462=<email>")
    test_duration = 120  # Seconds (int)
    survey_reply_time = 1 * 30  # Seconds
    guests_per_room = 4
    tot_rooms = 20
    manager_fake_name = "MANAGER"
    sender_prefix = "**"
    sender_suffix = ":** "  # Do not forget the final space here
    init_message_delay = 2.5  # Seconds
    init_message = (f"WELCOME TO THE TURING TEST HOTEL 🏨 (Your email: <email>)!<br/><br/>"
                    f"This is a unique destination "
                    f"composed of rooms that implement the multi-agent Turing Test, where you will act as both "
                    f"the judge ⚖️ and a conversation partner 🗣️!<br/>You will judge others to detect who is human, "
                    f"while others judge whether you are a human 🧑 or a machine 🤖 (remember to act human).<br/><br/>"
                    f"<strong>Have you already completed your profile?</strong> If not, please do so before "
                    f"starting this experience; you only need to do it once: <a href='{profile_link}'>Click Here!</a>. "
                    f"<br/>REPLY TO THIS MESSAGE ONCE YOU HAVE FILLED OUT THE FORM (for example, say 'yes' or any "
                    f"other response to continue 😀).")
    start_message = (f"You were named <YOUR_NAME> and the other "
                     f"guests are <OTHER_NAMES>. Start chatting and keep it going for "
                     f"{test_duration} seconds.")
    survey_message = ("Dear <YOUR_NAME>, you have interacted with <OTHER_NAMES>. "
                      "Each was either a human or an AI. "
                      "<br/><br/><strong>PLEASE LIST THE ONES YOU THINK WERE HUMANS</strong> "
                      "(separated by commas or even just spaces, as you prefer). "
                      "<br/><br/>After having written down the list, you can keep writing on the same message to"
                      " add optional comments, explaining why you made your choice,"
                      " and every extra feedback about this experience (warning: LIST AND COMMENTS GO ALL IN A "
                      "SINGLE MESSAGE, once you send it you are done).")

    class Room:
        def __init__(self, target_guests: int, id_in_hotel: int):
            """Create a room in the Turing hotel.

            Every room is composed of guests, identified by their peer IDs (strings) and having a fake name as
            'A', 'B', 'C', ... etc. It also stores the profile of each guest, and, if needed, there are also
            separated maps for HUMAN and ARTIFICIAL guests.

            A room is identified by an 8-chars UUID, and it features two attributes: ACTIVE, EDITABLE.
            An ACTIVE room is a room where the conversation is going on.
            An EDITABLE room is room where new guests could leave or join (no matter if it is ACTIVE or not).

            Args:
                target_guests: The target number of guests to activate a room (it is also the max number of guests)
                id_in_hotel: the id of the room in the list of rooms of the hotel.
            """
            self.uuid = uuid.uuid4().hex[:8]
            self.target_guests = target_guests
            self.id_in_hotel = id_in_hotel

            self.guests: dict[str, NodeProfile] = {}  # peer ID -> profile (ALL guests)
            self.human_guests: dict[str, NodeProfile] = {}  # peer ID -> profile (HUMAN guests only)
            self.artificial_guests: dict[str, NodeProfile] = {}  # peer ID -> profile (ARTIFICIAL guests only)

            self.active = False
            self.editable = True
            self.activation_timestamp = -1.
            self.deactivation_timestamp = -1.

            self.fake_names = self.__make_fake_names()  # Generate names such as 'A', 'B', 'C', ...
            self.guest2name: dict[str, str] = {}  # peer ID -> fake name
            self.name2guest: dict[str, str] = {}  # fake name -> peer ID

        def reset(self):
            self.uuid = uuid.uuid4().hex[:8]

            self.guests: dict[str, NodeProfile] = {}  # peer ID -> profile (ALL guests)
            self.human_guests: dict[str, NodeProfile] = {}  # peer ID -> profile (HUMAN guests only)
            self.artificial_guests: dict[str, NodeProfile] = {}  # peer ID -> profile (ARTIFICIAL guests only)

            self.active = False
            self.editable = True
            self.activation_timestamp = -1.
            self.deactivation_timestamp = -1.

            self.guest2name: dict[str, str] = {}  # peer ID -> fake name
            self.name2guest: dict[str, str] = {}  # fake name -> peer ID

        def count_human_guests(self):
            return len(self.human_guests)

        def count_artificial_guests(self):
            return len(self.artificial_guests)

        def count_guests(self):
            return len(self.guests)

        def count_free_spots(self):
            return max(0, self.target_guests - self.count_guests())

        def is_room_full(self):
            return self.target_guests <= len(self.guests)

        def is_present(self, peer_id):
            return peer_id in self.guests

        def add_if_there_is_space(self, guest: str, profile: NodeProfile) -> bool:
            if self.is_editable() and not self.is_room_full():

                # Saving the new guest in the internal maps
                self.guests[guest] = profile
                is_human = profile.get_static_profile()["node_type"] == WAgent.HUMAN
                if is_human:
                    self.human_guests[guest] = profile
                else:
                    self.artificial_guests[guest] = profile

                # Attaching a fake name to the guest
                fake_name = self.fake_names[self.count_guests() - 1]
                self.guest2name[guest] = fake_name
                self.name2guest[fake_name] = guest
                return True
            else:
                return False

        def remove_if_present(self, peer_id: str, ignore_editable_flag: bool = False) -> bool:
            if (self.is_editable() or ignore_editable_flag) and self.is_present(peer_id):
                del self.guests[peer_id]
                if peer_id in self.human_guests:
                    del self.human_guests[peer_id]
                if peer_id in self.artificial_guests:
                    del self.artificial_guests[peer_id]
                return True
            else:
                return False

        def is_active(self):
            return self.active

        def is_editable(self):
            return self.editable

        def set_as_editable(self):
            self.editable = True

        def set_as_not_editable(self):
            self.editable = False

        def set_as_active(self):
            self.active = True
            self.activation_timestamp = ttime.monotonic()

        def set_as_not_active(self):
            self.active = False
            self.deactivation_timestamp = ttime.monotonic()

        def get_passed_seconds_since_activation(self):
            if self.is_active():
                return int(ttime.monotonic() - self.activation_timestamp)
            else:
                return -1

        def get_passed_seconds_since_deactivation(self):
            if not self.is_active() and self.deactivation_timestamp > 0:
                return int(ttime.monotonic() - self.deactivation_timestamp)
            else:
                return -1

        def __make_fake_names(self):
            alphabet = string.ascii_uppercase
            names = []
            for i in range(self.target_guests):
                letter = alphabet[i % len(alphabet)]
                suffix = (i // len(alphabet)) + 1 if self.target_guests > len(alphabet) else 0
                names.append(letter if suffix == 0 else f"{letter}{suffix}")
            return names

    class Hotel:
        def __init__(self, tot_rooms: int = 10, target_per_room: int = -1, max_stay_seconds: int = -1,
                     known_profiles_dict: dict[str, NodeProfile] | None = None):
            """Create a Turing hotel, composed of some rooms.

            Args:
                tot_rooms: Total number of rooms (i.e., maximum number of parallel conversation groups).
                target_per_room: The target number of guests to declare a room as active and start the conversation.
                max_stay_seconds: The duration of a group conversation.
                known_profiles_dict: A dictionary of known node profiles, where to search for guest information.
                    It is a map peer ID to node profile.
            """
            self.target_per_room = target_per_room
            self.known_profiles_dict = known_profiles_dict
            self.max_stay_seconds = max_stay_seconds

            self.rooms = [WAgent.Room(target_per_room, i) for i in range(tot_rooms)]  # The rooms of the hotel
            self.guest2room = {}  # A map from guest peer ID to the room in which the guest is

        def get_room(self, guest: str):
            if guest in self.guest2room:
                return self.guest2room[guest]
            else:
                return None

        def already_in_a_hotel_room(self, guest: str):
            return guest in self.guest2room

        def deactivate_rooms_due_to_time_limits(self):
            """Get rooms for which the max conversation time has passed (set them as not editable and not active)."""

            rooms_that_were_deactivated = []
            for room in self.rooms:

                # If the predefined conversation time has passed, the room is "locked" (set as not editable),
                # deactivated (since the conversation is not going on anymore), and returned as room to be checked out
                if room.is_active() and room.get_passed_seconds_since_activation() >= self.max_stay_seconds:
                    room.set_as_not_editable()  # locking
                    room.set_as_not_active()  # deactivating
                    rooms_that_were_deactivated.append(room)
            return rooms_that_were_deactivated

        def check_in(self, guests: list[str]):
            """Check the profiles of the guests waiting, assign them to rooms with the goal of filling them."""

            checked_in = []  # Correctly checked in guests (peer IDs)
            cannot_check_in = []  # Guests for which check in was not possible (for example, missing profile)
            updated_rooms = set()  # This will keep the set of rooms that get updated by the check-in routine

            # Shuffling guests waiting in the hall
            shuffled_guests = random.sample(guests, len(guests))

            # Sorting rooms: our goal is to fill them, so let's put the most populated on top
            sorted_rooms = sorted(self.rooms, key=lambda _room: _room.count_guests(), reverse=True)

            # Consider rooms one by one
            i = 0
            for room in sorted_rooms:

                # Early stop
                if len(shuffled_guests) == 0:
                    break

                # Skip the room if the conversation is already going on or if the room is locked (not editable)
                if room.is_active() or not room.is_editable():
                    continue

                # Aim at filling the currently considered room
                while not room.is_room_full():
                    guest = shuffled_guests[i]

                    if not self.already_in_a_hotel_room(guest):  # Skip already in-room guests (important)

                        # Look for the profile of the guest, and add the guest to the room
                        if self.known_profiles_dict is not None and guest in self.known_profiles_dict:
                            guest_profile = self.known_profiles_dict[guest]
                            if room.add_if_there_is_space(guest, guest_profile):  # This is expected to work
                                self.guest2room[guest] = room  # Writing down the room where the guest was added
                                checked_in.append(guest)  # Saving the guest peer ID
                                updated_rooms.add(room)  # Marking the room as updated
                            else:
                                cannot_check_in.append(guest)  # This is not expected to happen, but better be safe
                        else:
                            cannot_check_in.append(guest)  # If the profile is missing

                    i += 1  # Move to the next guest
                    if i >= len(shuffled_guests):
                        break
                if i >= len(shuffled_guests):
                    break
            return checked_in, cannot_check_in, updated_rooms

        def check_out(self, guest):
            if guest in self.guest2room:
                room = self.guest2room[guest]
                room.remove_if_present(guest, ignore_editable_flag=True)
                del self.guest2room[guest]

        def compute_room_stats(self):
            """If you want some stats, not currently used."""

            stats = {
                "hist_room_stats": [0] * self.target_per_room,
                "hist_room_stats_humans": [0] * self.target_per_room,
                "hist_room_stats_artificial": [0] * self.target_per_room,
                "mean_per_room": 0.0,
                "mean_humans_per_room": 0.0,
                "mean_artificial_per_room": 0.0,
            }
            n = float(len(self.rooms))

            for room in self.rooms:
                artificial = room.count_artificial_guests()
                humans = room.count_human_guests()
                total = room.count_guests()

                stats["hist_room_stats_artificial"][artificial] += 1
                stats["hist_room_stats_humans"][humans] += 1
                stats["hist_room_stats"][total] += 1

                stats["mean_per_room"] += total
                stats["mean_humans_per_room"] += humans
                stats["mean_artificial_per_room"] += artificial

            stats["mean_per_room"] /= n
            stats["mean_humans_per_room"] /= n
            stats["mean_artificial_per_room"] /= n
            return stats

    def __init__(self, *args, **kwargs) -> None:
        """Create an agent for the Hotel Turing test.

        There are two types of agent attributes (recall they are expected to start with "_"): those that are considered
        when the role is 'participant', and those that are considered when the role is 'manager'.
        """
        super().__init__(*args, **kwargs)

        # These attributes are valued only if the role is 'participant'
        self._part_conversation = None  # The list of messages of the whole conversation happened so far
        self._part_conversation_as_str = None  # A long-string version of the whole conversation
        self._part_manager_peer_id: str | None = None  # The peer ID of the selected manager
        self._part_manager_stream = None  # Output stream of the selected manager
        self._part_room_stream = None  # Stream of the manager where chat messages are received
        self._part_proc_output_stream = None  # Output stream of this participant
        self._part_fake_name = None  # Your fake name

        # These attributes are valued only if the role is 'manager'
        self._mana_hotel: WAgent.Hotel | None = None  # The Turing hotel
        self._mana_peer_id: str | None = None  # The peer ID of our agent
        self._mana_sender_peer_id: str | None = None  # The peer ID of the agent who sent a message we are broadcasting
        self._mana_guests_ready_to_get_the_survey: set[str] | None = None  # Guests that will be asked for a feedback
        self._mana_guests_who_got_the_survey: dict[str, int] | None = None  # The data UUID of the survey requests
        self._mana_proc_output_stream: DataStream | None = None  # Our output stream that will store messages we send
        self._mana_proc_output_stream_net_hash: str | None = None  # Hash of our output stream
        self._mana_rooms_ready_for_start_message: dict | None = None  # The dict of rooms just set as active
        self._mana_streams_of_rooms: list | None = None  # The data streams associated to the rooms
        self._mana_streams_of_rooms_net_hashes: list | None = None  # The net hashes of the room streams
        self._mana_streams_of_rooms_buffered_recipients: list[list[list[str]]] | None = None
        self._mana_streams_of_rooms_tags: list[int] | None = None
        self._mana_streams_of_rooms_sent_tags: list[int] | None = None
        self._mana_do_gen_called: int | None = None

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        if self.get_current_role() == "manager":
            self.out("I just became the manager of the Turing Test Hotel, what a honor!")

            # Creating the hotel
            self._mana_hotel = WAgent.Hotel(tot_rooms=WAgent.tot_rooms, target_per_room=WAgent.guests_per_room,
                                            max_stay_seconds=WAgent.test_duration,
                                            known_profiles_dict=self.world_agents)
            self._mana_peer_id = self.get_peer_ids()[1]
            self._mana_do_gen_called = 0
            self._mana_guests_ready_to_get_the_survey = set()
            self._mana_guests_who_got_the_survey = {}
            self._mana_rooms_ready_for_start_message = {}
            for net_hash, stream_dict in self.proc_streams.items():
                for stream_name, stream_obj in stream_dict.items():
                    if stream_obj.props.is_text():
                        self._mana_proc_output_stream = stream_obj
                        self._mana_proc_output_stream_net_hash = net_hash
                        break
            if self._mana_proc_output_stream is None:
                raise GenException("Cannot find the output stream of the manager agent")

            # Creating one stream per room
            self._mana_streams_of_rooms = []
            self._mana_streams_of_rooms_net_hashes = []
            self._mana_streams_of_rooms_buffered_recipients = []
            self._mana_streams_of_rooms_tags = []
            self._mana_streams_of_rooms_sent_tags = []
            for i in range(0, WAgent.tot_rooms):

                # We create buffered streams handled as queues, since the rate with which the manager will set data to
                # these streams will be way faster that the actual sending rate (we do this to avoid missed samples)
                stream_dict = self.add_stream(BufferedDataStream(props=DataProps(name=f"stream_of_room_id_{i}",
                                                                                 data_type="text"), is_queue=True),
                                              owned=True)
                for stream_obj in stream_dict.values():
                    self._mana_streams_of_rooms.append(stream_obj)
                    self._mana_streams_of_rooms_net_hashes.append(stream_obj.net_hash(self._mana_peer_id))
                    break

                # Here we will store the recipients of the messages we buffer on the stream (recall that the buffered
                # stream stores only samples and their data tag, but nothing about the recipients of what will be sent
                self._mana_streams_of_rooms_buffered_recipients.append([])

                # During the same clock cycle, multiple data samples will be generated,
                # hence we need to manually tag them (cannot use the clock cycle number)
                self._mana_streams_of_rooms_tags.append(0)
                self._mana_streams_of_rooms_sent_tags.append(-1)  # This marks the tags that were sent, start with -1

            # Updating the manager's profile
            self.update_streams_in_profile()

        else:
            self._part_conversation = None
            self._part_conversation_as_str = None
            self._part_manager_peer_id = None
            self._part_room_stream = None
            self._part_proc_output_stream = None
            self._part_fake_name = None

            for net_hash, stream_dict in self.proc_streams.items():
                for stream_name, stream_obj in stream_dict.items():
                    if not stream_obj.props.is_public() and stream_obj.props.is_text():
                        self._part_proc_output_stream = stream_obj
                        break
            self.out("I just entered the Turing Test Hotel as a guest")

    async def assign_to_rooms(self):
        """Randomly assign all the guests waiting in the hall to some rooms, trying to fill them."""

        if self.get_current_role() != "manager":
            return False

        # Looking for all current known guests of the whole hotel, being them in rooms or not
        if await self.find_agents("participant", handshake_completed=True):
            all_hotel_guests = [a for a in self._found_agents if not self._mana_hotel.already_in_a_hotel_room(a)]
            self._found_agents.clear()  # Clear this, otherwise it will become the default argument in involved agents
        else:
            all_hotel_guests = []
        self.print(f"Guests in the hall: {all_hotel_guests}")

        # Wait for all the rooms to finish before checking-in again
        for room in self._mana_hotel.rooms:

            # If even just a single room is active or in "wait-for-survey" stage
            if room.is_active() or (room.activation_timestamp > 0 and room.count_guests() > 0):
                return True

        # Clearing all pending requests (we start from scratch since we are handling rooms in a synchronous manner)
        actions = self.behav.get_all_actions()
        for action in actions:
            action.get_list_of_requests().clear()

        # Assign to rooms the ones that are not already in some rooms
        checked_in, cannot_check_in, updated_rooms = self._mana_hotel.check_in(all_hotel_guests)
        self.print(f"Guests checked-in: {checked_in}")
        self.print(f"Guests that cannot be checked-in: {cannot_check_in}")
        self.print(f"Updated rooms IDs: {[room.id_in_hotel for room in updated_rooms]}")

        # Discarding those that for some weird reasons could be checked in
        for guest in cannot_check_in:
            await self.disconnect(guest)

        # Telling the newly checked in guests to join their room
        checked_in_and_reached_out = []
        for guest in checked_in:
            ret = await self.set_next_action(agent=guest, action="join_room", from_state="hall",
                                             args={"room_id": self._mana_hotel.get_room(guest).id_in_hotel})

            # Clearing UUIDs and the data of the processor of the guests
            net_hash_to_stream_dict = self.find_streams(guest, name_or_group="processor")
            for net_hash, stream_dict in net_hash_to_stream_dict.items():
                self.set_uuid(net_hash, None, expected=True)
                self.set_uuid(net_hash, None, expected=False)
                for stream_obj in stream_dict.values():
                    stream_obj.set(None)

            if not ret:
                self._mana_hotel.check_out(guest)
                await self.disconnect(guest)  # Killing the ones that are not reachable anymore
            else:
                checked_in_and_reached_out.append(guest)
        self.print(f"Guests that were correctly asked to join their room: {checked_in_and_reached_out}")

        # We send a room update event for all the rooms that got a new guest in
        for room in updated_rooms:

            # Saving stats
            room_stats = {
                "room_uuid": room.uuid,
                "human_guests": [(z, room.guest2name[z],
                                  room.guests[z].get_static_profile()['email'] + '/' +
                                  room.guests[z].get_static_profile()['node_name'])
                                 for z in room.human_guests.keys()],
                "artificial_guests": [(z, room.guest2name[z],
                                       room.guests[z].get_static_profile()['email'] + '/' +
                                       room.guests[z].get_static_profile()['node_name'])
                                      for z in room.artificial_guests.keys()],
                "timestamp": self._node_clock.get_time_as_string(),
                "event": "room_update"
            }
            int_timestamp = self._node_clock.get_time_ms(monotonic=True)
            self.stats.store_stat("room_update", room_stats, peer_id=room.uuid, timestamp=int_timestamp)

        return True

    async def check_rooms(self):
        """Check current rooms of the Turing hotel, activating, updating or deactivating them, removing lost guests."""

        if self.get_current_role() != "manager":
            return False

        # For each room of the hotel...
        self.print(f"Connected to manager ({len(self.all_agents.keys())}): {list(self.all_agents.keys())}")
        self.print(f"Hotel guests ({len(self._mana_hotel.guest2room)}): {list(self._mana_hotel.guest2room.keys())}")
        for room in self._mana_hotel.rooms:
            kicked_all_out = False
            self.print(f"Room ID {room.id_in_hotel}, UUID {room.uuid}, {len(room.guests)} guests: "
                       f"{list(room.guests.keys())}")

            # Activating a room that has the right number of guests
            if room.is_room_full() and not room.is_active() and room.is_editable():
                self.print(f"Activating room ID {room.id_in_hotel}, UUID {room.uuid}, telling guests to start the chat")

                # Telling the guests the conversation can start
                lost_guests = []
                for guest in room.guests.keys():
                    ret = await self.set_next_action(agent=guest, action="start")
                    if not ret:
                        self._mana_hotel.check_out(guest)
                        await self.disconnect(guest)  # Killing the ones that are not reachable anymore
                        lost_guests.append(guest)

                if len(lost_guests) > 0:
                    self.print(f"Cannot activate room ID {room.id_in_hotel}, UUID {room.uuid}, "
                               f"these guests couldn't be reached out to start the chat: {lost_guests}")
                else:
                    # Activating the room: notice that we will postpone the actual activation by a few seconds, to let
                    # the 'start' signal reach all the guests
                    room.set_as_active()
                    room.activation_timestamp += WAgent.init_message_delay

                    # We take a note of the room that is ready to receive the welcome message
                    self._mana_rooms_ready_for_start_message[room.id_in_hotel] = \
                        {'room': room, 'send_message_at': ttime.monotonic() + WAgent.init_message_delay,
                         'requested_action': False}

            # Sending the welcome (start) message (unless it was already requested before)
            if (room.id_in_hotel in self._mana_rooms_ready_for_start_message and
                    ttime.monotonic() >= self._mana_rooms_ready_for_start_message[room.id_in_hotel]['send_message_at']
                    and not self._mana_rooms_ready_for_start_message[room.id_in_hotel]['requested_action']):

                # The manager asks ("ask_gen", well, actually using set_next_action) himself to generate ("do_gen")
                # the message, that will be sent to all the guest since the "do_gen" of the manager is prepared to do.
                # Before doing anything, we set in the input stream of the manager's processor the "welcome/start"
                # message, assuming the processor acts like an identity function
                self.set_proc_input(WAgent.start_message, uuid="s4m344ll")
                if not self.behav.request_action(signature=self._mana_peer_id,
                                                 action_name="do_gen",
                                                 args={"u_hashes": [f'{self._mana_peer_id}:processor_in'],
                                                       "samples": 1},
                                                 uuid="s4m344ll", from_state="collect_messages"):

                    # This thing below is really not expected to happen, since the manager asked himself... (safety)
                    await self.__kick_all_guests(room)  # Telling to "leave_room"...
                    kicked_all_out = True
                else:
                    # Marking to avoid requesting it again
                    self._mana_rooms_ready_for_start_message[room.id_in_hotel]['requested_action'] = True

                # Saving stats about room activation (the actual activation, the postponed one)
                if not kicked_all_out:
                    room_stats = {
                        "room_uuid": room.uuid,
                        "human_guests": [(z, room.guest2name[z],
                                          room.guests[z].get_static_profile()['email'] + '/' +
                                          room.guests[z].get_static_profile()['node_name'])
                                         for z in room.human_guests.keys()],
                        "artificial_guests": [(z, room.guest2name[z],
                                               room.guests[z].get_static_profile()['email'] + '/' +
                                               room.guests[z].get_static_profile()['node_name'])
                                              for z in room.artificial_guests.keys()],
                        "timestamp": self._node_clock.get_time_as_string(),
                        "event": "room_activation"
                    }
                    int_timestamp = self._node_clock.get_time_ms(monotonic=True)
                    self.stats.store_stat("room_activation", room_stats, peer_id=room.uuid, timestamp=int_timestamp)

            # If just one guest is not connected anymore to the manager, kick everybody out (telling to "leave_room")
            if not kicked_all_out:
                for guest in room.guests:
                    if guest not in self.world_agents:
                        self.print(f"Guest {guest} is not connected to me anymore, kicking all out form "
                                   f"room ID {room.id_in_hotel}, UUID {room.uuid}")
                        await self.__kick_all_guests(room)  # Telling to "leave_room"...
                        kicked_all_out = True
                        break

            # Kicking out all the guest who did not answer in time to the feedback request
            if not kicked_all_out and room.get_passed_seconds_since_deactivation() >= WAgent.survey_reply_time:
                self.print(f"Too much time passed waiting for survey feedback from {room.guests.keys()}, "
                           f"room ID {room.id_in_hotel}, UUID {room.uuid}, kicking all out")
                await self.__kick_all_guests(room)  # Telling to "leave_room"...

            # Reset empty rooms (only those that were "used" before, using the activation_timestamp to discriminate)
            if room.count_guests() == 0 and room.activation_timestamp > 0:
                self.__reset_room(room)

        # TODO remove this check
        count = 0
        for room in self._mana_hotel.rooms:
            count += room.count_guests()
        assert count == len(self._mana_hotel.guest2room), \
            f"Sum of room counts does not match hotel guest count: {count} vs {len(self._mana_hotel.guest2room)}"

        return True

    async def ready_to_send(self):
        """Setting the survey in the output stream of the manager and setting recipients of the buffered messages."""

        if self.get_current_role() != "manager":
            return False

        # Letting the survey message be formatted as by adding the sender name as a prefix
        _survey_message = WAgent.__format_message(WAgent.manager_fake_name, WAgent.survey_message)

        # Putting the survey in output stream of the manager (recall that the output stream was altered after every
        # room-related internal 'do_gen' to format the message)
        self._mana_proc_output_stream.set(_survey_message)  # Keep it fresh
        self._mana_proc_output_stream.set_uuid("5urv3y")

        # Setting the list of recipients that will get the survey
        self.clear_recipients(self._mana_proc_output_stream_net_hash)
        for guest_ready_to_get_the_survey in self._mana_guests_ready_to_get_the_survey:
            self.add_recipient(self._mana_proc_output_stream_net_hash, guest_ready_to_get_the_survey)

        # Setting the engaged partners, that will be the one who will be passed to the ask_gen for the survey
        # (They change every time)
        await self.set_engaged_partner(self._mana_guests_ready_to_get_the_survey)

        # Setting the recipients for the currently buffered chat messages that still have to be sent
        for room_id in range(0, len(self._mana_hotel.rooms)):

            # Clearing the existing recipients first...
            self.clear_recipients(self._mana_streams_of_rooms_net_hashes[room_id])

            # ...then adding the new ones, that are the oldest recipients in our queue (assuming we will be sending the
            # oldest queued/buffered message at the next cycle)
            if len(self._mana_streams_of_rooms_buffered_recipients[room_id]) > 0:
                self.add_recipient(self._mana_streams_of_rooms_net_hashes[room_id],
                                   self._mana_streams_of_rooms_buffered_recipients[room_id][0])  # First is the oldest
                del self._mana_streams_of_rooms_buffered_recipients[room_id][0]  # Removing recipients from the queue
        return True

    async def survey_requests_sent(self):
        """Saving the UUIDs of the requests for feedbacks we just sent."""

        if self.get_current_role() != "manager":
            return False

        # We reached this state by an "ask_gen" that sent the surveys and automatically prepared the list of agents
        # that were asked for a feedback, i.e., we sent to "self._engaged_agents"
        # and saved the request UUID to "self.last_ref_uuid". We remember this information here, so that when we will
        # get a message from a guest, we will be able to detect if it is a feedback in response to the survey or not.
        for asked in self._mana_guests_ready_to_get_the_survey:
            self._mana_guests_who_got_the_survey[asked] = self._mana_proc_output_stream.get_tag()  # Saving the UUID
        self._mana_guests_ready_to_get_the_survey.clear()  # Clearing

        self.print(f"Guests who correctly got the survey and that are expected to send a feedback: "
                   f"{list(self._mana_guests_who_got_the_survey.keys())}")
        return True

    async def prepare_surveys_and_get_feedbacks(self):
        """Get the list of guests that must receive the survey, and handle those that already replied to it."""

        if self.get_current_role() != "manager":
            return False

        # Deactivate the rooms for which the max time has passed and lock them (set as not editable)
        rooms_that_were_deactivated = self._mana_hotel.deactivate_rooms_due_to_time_limits()

        # For each deactivated/locked room, we get its guests and save them to the list of those that will receive
        # our final survey
        for room in rooms_that_were_deactivated:
            self.print(f"Deactivated room ID {room.id_in_hotel}, UUID {room.uuid}, saving guest list to send survey")

            # Let's stop circulating messages
            self.__reset_room_stream(room)

            # Saving stats
            room_stats = {
                "room_uuid": room.uuid,
                "timestamp": self._node_clock.get_time_as_string(),
                "event": "room_deactivation"
            }
            int_timestamp = self._node_clock.get_time_ms(monotonic=True)
            self.stats.store_stat("room_deactivation", room_stats, peer_id=room.uuid, timestamp=int_timestamp)

            # Saving guests into the list of those who will be expected to reply to the request we are going to make
            for guest in room.guests:
                ret = await self.set_next_action(agent=guest, action="stop")
                if not ret:
                    await self.__kick_all_guests(room)
                    break
                else:
                    self._mana_guests_ready_to_get_the_survey.add(guest)

        # Let's copy this dictionary, since we will modify it in the loop below
        guests_who_got_the_survey = {k: v for k, v in self._mana_guests_who_got_the_survey.items()}

        # Checking the data produced guests that got the survey: if they replied, we store their feedback and remove
        # them from the list of guests who got the survey
        for guest in guests_who_got_the_survey:

            # Getting the UUID of the 'ask_gen' request, that the manager used to send the survey and ask for a reply
            tag = self._mana_guests_who_got_the_survey[guest]

            # Getting the processor stream of the guest (that is where the feedback will be placed)
            net_hash = DataProps.build_net_hash(guest, pubsub=False, name_or_group="processor")
            stream_dict = self.known_streams[net_hash]
            stop_loop = False
            for stream_name, stream_obj in stream_dict.items():
                if stop_loop:
                    break

                if not stream_obj.props.is_public() and stream_obj.props.is_text():

                    # Getting feedback
                    if stream_obj.get_uuid() == 's4m344ll':
                        continue

                    # Getting feedback
                    guest_feedback = stream_obj.get("prepare_surveys_and_get_feedbacks")
                    if guest_feedback is None:
                        self.print(
                            f"Got nothing (expected feedback) from {guest}")
                        stop_loop = True
                        continue

                    # Checking if this is actually the requested feedback
                    if tag != stream_obj.get_tag():
                        self.print(
                            f"Got something (expected feedback) "
                            f"from {guest}, but with wrong data tag ({stream_obj.get_tag()} vs {tag}). "
                            f"Got: {guest_feedback}")
                        stop_loop = True
                        continue

                    # Kicking out
                    self.print(f"Got feedback from {guest}, kicking the guest out of the room, nothing more to do "
                               f"here. Got: {guest_feedback}")
                    room = self._mana_hotel.get_room(guest)
                    await self.__kick_guest(guest, room)

                    # Saving stats about this message
                    sender_profile = self.all_agents[guest].get_static_profile()
                    feedback = {
                        "msg": guest_feedback if (guest_feedback is not None
                                                  and isinstance(guest_feedback, str)) else "<INVALID_FORMAT>",
                        "timestamp": self._node_clock.get_time_as_string(),
                        "room_uuid": room.uuid,
                        "sender_peer_id": guest,
                        "sender_fake_name": room.guest2name[guest],
                        "sender_real_name": sender_profile['email'] + '/' + sender_profile['node_name']
                    }
                    int_timestamp = self._node_clock.get_time_ms(monotonic=True)
                    self.stats.store_stat("room_survey", feedback, peer_id=room.uuid, timestamp=int_timestamp)
        return True

    async def do_gen(self, u_hashes: list[str] | None = None, extra_hashes: list[str] | None = None,
                     samples: int = 100, time: float = -1., timeout: float = -1.,
                     _requester: str | list | None = None, _request_time: float = -1., _request_uuid: str | None = None,
                     _completed: bool = False) -> bool:
        """This is an overload of 'do_gen' for the 'manager' role only to broadcast to all the guests of the room.

        The logic is simple: the manager receives a message from a guest (i.e., the message is in the output
        stream of the guest), and sends it to all the other guests of the room (excluding the sender). The sending
        happens by means of the room stream (from the point of view of the guests, he asks for a do_gen to the manager,
        and the manager replies on the room stream).

        This is also used to send the welcome/start message to all the guests of the room.
        """

        if self.get_current_role() == "manager" and self.behaving_in_world() and _requester is not None:

            # Let's distinguish ordinary room-messages (sent by participants) from the welcome/start message sent
            # by the manager
            is_welcome_message = _requester == self._mana_peer_id
            is_participant_message = self._mana_hotel.already_in_a_hotel_room(_requester)
            room_ids = []

            # First of all, let's stop every attempt to 'do_gen' if the requester is not in the hotel, and he is not
            # the manager as well sending the welcome message
            if not is_participant_message and not is_welcome_message:
                return True

            # Welcome message
            if is_welcome_message:
                self._mana_sender_peer_id = _requester  # Saving the peer ID of the sender (the hotel manager)
                room_ids = [room_id for room_id, status in self._mana_rooms_ready_for_start_message.items()
                            if status['requested_action'] is True]

                # Clearing: all the just-activated rooms will get the welcome/start message
                for room_id in room_ids:
                    del self._mana_rooms_ready_for_start_message[room_id]
                self.print("Preparing welcome message...")

                ret = await super().do_gen(u_hashes, extra_hashes, samples, time, timeout,
                                           None, _request_time, _request_uuid, _completed)
                if not ret:
                    self.err("Failed to process the welcome message by internally calling do_gen")  # Unexpected
                    return False

            # Ordinary room message from a participant
            if is_participant_message:

                # Let's avoid attempts to send messages by guests in rooms not active yet or by guests in rooms that
                # were just activated, but that have not broadcast the welcome/start message yet.
                # This will also filter out guests that are dealing with the survey, since their rooms are
                # deactivates (i.e., not active)
                room = self._mana_hotel.get_room(_requester)
                if not room.is_active() or room.id_in_hotel in self._mana_rooms_ready_for_start_message:
                    return True

                self._mana_sender_peer_id = _requester  # Saving the peer ID of the sender (a guest of the room)
                room_ids = [self._mana_hotel.get_room(_requester).id_in_hotel]

            # For each room involved (either in case (1) or (2)), call the original 'do_gen' to format the message,
            # and load it to the room stream. Notice that 'do_gen' is called once per room, and the clock cycle here
            # is always the same (i.e., it does not change in the different calls to do_gen), so we rely on manual
            # tagging (the clock cycle is not a unique tag anymore)
            for room_id in room_ids:

                # Internal call to format the message before sending it: call 'do_gen' by clearing the requester
                # (no need to do it for the welcome message, that is the same for all the rooms, hence already
                # generated above - only once)
                if is_participant_message:
                    ret = await super().do_gen(u_hashes, extra_hashes, samples, time, timeout,
                                               None, _request_time, _request_uuid, _completed)
                    if not ret:
                        self.err("Failed to process the message by internally calling do_gen")  # Unexpected
                        return False

                # Getting the formatted message (do not put any arguments in get())
                sample_to_broadcast = self._mana_proc_output_stream.get()  # No arguments here (important!)
                self.print(f"Sample to broadcast (wildcards not handled yet): {sample_to_broadcast}")

                # Manual tag management
                sample_tag = self._mana_streams_of_rooms_tags[room_id]
                self._mana_streams_of_rooms_tags[room_id] += 1

                # Setting the formatted message to the room stream (using the just prepared tag)
                # Recall that this is a buffered stream handled as a queue, so we will have to manually set the
                # recipients of this message (not here, we will do it when leaving the state where we are now)
                self._mana_streams_of_rooms[room_id].set(sample_to_broadcast, data_tag=sample_tag)

                # Setting the UUID to the same one that was originally requested
                self._mana_streams_of_rooms[room_id].set_uuid(_request_uuid)

                # Saving the recipients of this broadcasting: all the guests in case (1),
                # all except the sender in case (2) - since the manager is not a guest, this code is fine for both.
                # We will set them when leaving this state, assuming that the oldest buffered message is the next
                # one that will be sent, and the oldest saved recipients are the ones who are expected to receive it
                broadcast_to = set(self._mana_hotel.rooms[room_id].guests.keys()) - {self._mana_sender_peer_id}
                self._mana_streams_of_rooms_buffered_recipients[room_id].append(list(broadcast_to))
                self.print(f"Broadcast it to: {broadcast_to}")
            return True

        # In all other cases (public network, participant-related stuff, ..., revert to the usual do_gen
        return await super().do_gen(u_hashes, extra_hashes, samples, time, timeout,
                                    _requester, _request_time, _request_uuid, _completed)

    async def connect_to_manager(self):
        """Connecting to the (first found) Turing hotel manager (async)."""

        if self.get_current_role() != "participant":
            return False

        if await self.connect_by_role("manager"):  # It only "starts" connection (and it will fill self._found_agents)
            self._part_manager_peer_id = next(iter(self._found_agents))  # Takes the first found manager
            await self.set_engaged_partner(self._part_manager_peer_id)
            self.out("Connection to manager started...")
            return True
        else:
            self.err("Failed to connect to a manager")
            return False

    async def manager_is_disconnected(self, delay: float = 1.):
        """Checking is the manager is disconnected (usually starts with a delay to wait for handshake to complete."""
        assert delay == -1. or delay >= 0., "Invalid delay"

        if self.get_current_role() != "participant":
            return False

        return await self.disconnected(agent=self._part_manager_peer_id, handshake_completed=True, delay=-1.)

    async def lost(self, delay: float = -1):
        """Disconnecting from the manager (in case of timeouts)."""
        assert delay is not None, "Missing basic action information"

        if self.get_current_role() != "participant":
            return False

        await self.disconnect(self._part_manager_peer_id)
        self.out("Disconnecting from manager...")
        self._part_manager_peer_id = None
        return True

    async def ready_to_chat(self):
        """This is only needed to fix the case in which the survey message arrives before the 'stop' action."""

        if self.get_current_role() != "participant":
            return False

        # Clearing the UUID on the manager stream, since the 'ask_gen' that activated this state will be answered in
        # the room stream, and not in the manager stream (that will be used for surveys, hence we want it clear)
        self._part_manager_stream.clear_uuid()
        return True

    async def wait_for_intro(self):
        """Wait for the manager to send the introduction message before allowing to send chat data."""

        if self.get_current_role() != "participant":
            return False

        return self._part_fake_name is None  # It becomes non-None when the intro message arrives

    async def get_messages(self, add_to_history: bool = True):
        """Get new messages from the manager, and load the whole conversation in the input stream of our processor."""

        if self.get_current_role() != "participant":
            return False

        # Getting data from the manager's stream, add it to the existing conversation, load it to the input stream
        msg = self._part_room_stream.get("get_messages")

        # Guessing our own fake name by parsing the welcome/start message that the manager sent us
        # (if self._part_fake_name is None, then no messages has been received yet)
        if msg is not None and self._part_fake_name is None:
            if msg.startswith(WAgent.sender_prefix + WAgent.manager_fake_name + WAgent.sender_suffix):
                pos = WAgent.start_message.find("<YOUR_NAME>")
                sub = WAgent.start_message[0:pos]
                self._part_fake_name = msg[msg.find(sub) + len(sub):].split(" ")[0]

                pos_o = WAgent.start_message.find("<OTHER_NAMES>")
                sub = WAgent.start_message[pos + len("<YOUR_NAME>"):pos_o]
                other_fake_names = msg[msg.find(sub) + len(sub):].split(".")[0]

                self._part_conversation.append(f"In the following transcript, "
                                               f"your identity is: {self._part_fake_name}. Respond naturally.")
                self._part_conversation.append("")
                self._part_conversation.append("### PARTICIPANTS")
                self._part_conversation.append(self._part_fake_name + " (YOU), " + WAgent.manager_fake_name + ", " +
                                               other_fake_names)
                self._part_conversation.append("")
                self._part_conversation.append("### TRANSCRIPT")

                msg = WAgent.__format_message(WAgent.manager_fake_name, f"Dear {self._part_fake_name}, "
                                                                        "we are in the context of a test where "
                                                                        "your way of talking must look as the one of a "
                                                                        "human.")
            else:
                self.err(f"The first message was expected to be the welcome/start message from the "
                         f"manager, but it seems that it is not like that (message: {msg})")
                return True

        # Adding the received message to the message history, to create the context we will pass to our processor
        if msg is not None and add_to_history:

            # Add to history and convert the conversation to a single, long, string, self._part_conversation_as_str
            self.__add_to_history(formatted_msg=msg)

        # Keep the input stream of our processor up-to-date
        # Here we do not see any UUIDs or tags, since this input will be handled by the internal (solid) do_gen
        # to create an output that, afterward, will be used in an ask_gen (that indeed will set the UUID)
        self.set_proc_input(self._part_conversation_as_str)   # Here it can be None, and that's fine
        self.out(f"Conversation so far:\n{self._part_conversation_as_str}")
        return True

    async def set_email(self):
        """Saves the user email into a wildcard."""

        if self.get_current_role() != "participant":
            return False

        # Getting your email address and putting it in the HSM
        self.behav.add_wildcards({"<email>": self.get_profile().get_static_profile()['email']})
        return True

    async def skip_confirmation(self):
        """Skips the filled-profile confirmation for artificial agents."""

        if self.get_current_role() != "participant":
            return False

        return not has_human_processor(self)

    async def hall(self):
        """Clear the status."""

        # Blocking all pending conversations (if any)
        self.__disable_and_clear_all_room_streams()

        # Clearing whatever was set when joining the room
        self._part_conversation = []
        self._part_conversation_as_str = None
        self._part_manager_stream = None
        self._part_room_stream = None
        self._part_fake_name = None

        # Clearing pending requests (preserving "join_room" and "start",
        # since the manager could be fast in sending them after he told you "leave_room", that you might have not run
        # yet
        actions = self.behav.get_all_actions()
        for action in actions:
            if action.name != "join_room" and action.name != "start":
                action.get_list_of_requests().clear()
            else:

                # Avoid storing multiple join_room and start requests, just the last one (safety)
                if len(action.get_list_of_requests()) > 1:
                    action.get_list_of_requests().keep_only_the_most_recent_request()

    async def join_room(self, room_id: int = -1):
        """Join a room (find the room stream and the manager stream)."""

        if self.get_current_role() != "participant":
            return False

        if room_id < 0:
            return False

        # Setting up
        self._part_conversation = []
        self._part_conversation_as_str = None
        self._part_fake_name = None

        # Finding the room stream, where messages will be located
        net_hash_to_stream_dict = self.find_streams(self._part_manager_peer_id,
                                                    f"stream_of_room_id_{room_id}")
        for net_hash, stream_dict in net_hash_to_stream_dict.items():
            for _, stream_obj in stream_dict.items():
                if not stream_obj.props.is_public() and stream_obj.props.is_text():
                    self._part_room_stream = stream_obj
                    self._part_room_stream.clear_uuid()  # Resetting UUIDs on the guest side (important!)
                    self._part_room_stream.enable()  # Enabling
                    break

        # Finding the stream associated to the output of the manager's processor, where the final survey will be sent
        net_hash_to_stream_dict = self.find_streams(self._part_manager_peer_id,
                                                    f"processor")
        for net_hash, stream_dict in net_hash_to_stream_dict.items():
            for _, stream_obj in stream_dict.items():
                if not stream_obj.props.is_public() and stream_obj.props.is_text():
                    self._part_manager_stream = stream_obj
                    self._part_manager_stream.clear_uuid()   # Resetting UUIDs on the guest side (important!)
                    break

        # If the manager is not as expected (i.e., we cannot find the room stream and the manager output stream)
        # we disconnect from it
        if self._part_room_stream is None or self._part_manager_stream is None:
            self.err("Cannot find either the room stream of the processor output stream of the manager (or both)")
            await self.disconnect(self._part_manager_peer_id)
            return False

        return True

    async def leave_room(self):
        """Leaving a room (nothing special happens)."""

        if self.get_current_role() != "participant":
            return False
        return True

    async def start(self):
        """Start a chat (nothing special happens)."""

        if self.get_current_role() != "participant":
            return False

        # Some previous, possibly not completed, "ask_gen" might have left a marker in the manager's processor output
        # stream, better clear the marker to avoid further resets when receiving the survey
        self._part_manager_stream.clear_uuid_if_marked_as_clearable()

        # If you have a slow clock, it could happen that the welcome message arrives at the same time you can the
        # request for action 'start' and you run it. The next state is blocking, so we will go through another cycle
        # in which a participant might send another message, overwriting the mananger's wellcome.
        # So let's call a starting get_messages() here as well.
        await self.get_messages()
        return True

    async def stop(self):
        """Stop a chat (nothing special happens)."""

        if self.get_current_role() != "participant":
            return False

        # Blocking all pending conversations (if any)
        self.__disable_and_clear_all_room_streams()

        # We wait for the survey message from the manager, and then we have to provide the participant with the
        # whole context of the conversation.
        survey_message = self._part_manager_stream.get("stop")
        if survey_message is None or not survey_message.startswith(self.__format_message(WAgent.manager_fake_name,
                                                                                         msg="")):
            return False

        # Adding to history and generating the long string saved in self._part_conversation_as_str
        self.__add_to_history(formatted_msg=survey_message)

        # Move the (altered) message to the input stream
        # Here we also set the UUID, since this is the data that will be used in a (dashed) do_gen requested by the
        # manager, hence the input data must be already aligned with what will be the UUID of the manager's request
        self.set_proc_input(self._part_conversation_as_str, uuid='5urv3y')

        # Forcing ALL the tags of the data stream in the input stream to be the one of the manager's message
        # (if you only set it to the text data stream, the others will have a different tag, making the processor
        # decide to output tag -1 due to incoherence)
        self.set_tag(self.get_proc_input_net_hash(public=False), self._part_manager_stream.get_tag())
        return True

    async def message_prepared(self):
        """Handling a message previously prepared by our own processor."""

        if self.get_current_role() != "participant":
            return False

        # Getting from the output stream the message that was just prepared by the 'do_gen' action
        my_own_prepared_message = self._part_proc_output_stream.get("message_prepared")

        # Saving the message we prepared in the conversation history: notice that the other guests will receive it
        # later (so the conversations are not exactly the same on all sides), but that's expected
        if my_own_prepared_message is not None:

            # Formatting as expected
            my_own_prepared_message = WAgent.__format_message(self._part_fake_name, my_own_prepared_message)

            # Add to history adn convert the conversation to a single, long, string,
            # saved in self._part_conversation_as_str
            self.__add_to_history(formatted_msg=my_own_prepared_message)

        return True

    def proc_callback_inputs(self, inputs):
        """Manager only: add the sender name at the beginning of the broadcast message (assuming identity processor)."""

        inputs = super().proc_callback_inputs(inputs)
        if self.get_current_role() != "manager" or not self.behaving_in_world():
            return inputs

        # The manager will add usernames at the beginning of the messages (not originally sent by him)
        # assuming they are located in the first "string-type" input
        if self.behaving_in_world():
            for i, _input in enumerate(inputs):
                if isinstance(_input, str):

                    # Here we use the sender identity (peer ID) to find the right name to use.
                    # Recall it was saved in the 'do gen' method.
                    if self._mana_sender_peer_id != self._mana_peer_id:
                        sender_room = self._mana_hotel.get_room(self._mana_sender_peer_id)
                        sender_fake_name = sender_room.guest2name[self._mana_sender_peer_id]
                    else:
                        sender_fake_name = WAgent.manager_fake_name

                    # Altering message to add the sender (fake) name
                    inputs[i] = WAgent.__format_message(sender_fake_name, _input)
                    break
        return inputs

    def callback_before_sending_sample(self, content, data_tag: int, net_hash: str, stream_name: str, recipient: str):
        """Right before sending a message with a data sample, we save stats about it, and we also alter it if needed."""

        content = super().callback_before_sending_sample(content, data_tag, net_hash, stream_name, recipient)
        msg = content
        if self.get_current_role() != "manager":
            self.out(f"Sending message {msg} to {recipient}...")
            return msg

        # Let's avoid considering communications that are not about hotel rooms
        if not self._mana_hotel.already_in_a_hotel_room(recipient):
            self.out(f"Sending (not about hotel rooms) message {msg} to {recipient}...")
            return msg

        # Getting sender info
        room = self._mana_hotel.get_room(recipient)
        sender_fake_name = self.__get_sender_from_formatted_message(msg)
        if sender_fake_name != WAgent.manager_fake_name:
            sender_peer_id = room.name2guest[sender_fake_name]
            sender_profile = room.guests[sender_peer_id].get_static_profile()
        else:
            sender_peer_id = self._mana_peer_id
            sender_profile = self.get_profile().get_static_profile()

        # Altering messages in order to support wildcards
        recipient_fake_name = room.guest2name[recipient]
        other_fake_names = ", ".join(set(room.guest2name.values()) - {recipient_fake_name})
        msg = msg.replace("<YOUR_NAME>", recipient_fake_name).replace("<OTHER_NAMES>", other_fake_names)

        # Saving stats about this message
        if (sender_peer_id == self._mana_peer_id or  # Log all messages only from the manager...
                self._mana_streams_of_rooms_sent_tags[room.id_in_hotel] != data_tag):  # ...skip repeated messages
            room_msg = {
                "room_uuid": room.uuid,
                "msg": msg,
                "timestamp": self._node_clock.get_time_as_string(),
                "sender_peer_id": sender_peer_id,
                "sender_fake_name": sender_fake_name,
                "sender_real_name": sender_profile['email'] + '/' + sender_profile['node_name']
            }
            int_timestamp = self._node_clock.get_time_ms(monotonic=True)
            self.stats.store_stat("room_message", room_msg, peer_id=room.uuid, timestamp=int_timestamp)
            self._mana_streams_of_rooms_sent_tags[room.id_in_hotel] = data_tag

        self.out(f"Sending message {msg} to {recipient}...")
        return msg

    async def __kick_guest(self, guest, room):
        """Kicks a single guest of a room (telling him to "leave_room")."""

        self.print(f"Kicking guest {guest} from room ID {room.id_in_hotel}, UUID {room.uuid}")

        # Kicking out from the guest list
        self._mana_hotel.check_out(guest)

        # Telling the guest to "leave_room"
        ret = await self.set_next_action(agent=guest, action="leave_room")
        if not ret:
            await self.disconnect(guest)  # Disconnecting other lost-in-action guests

        # Clearing the waiting lists (if the guest was present, may not always be the case)
        self._mana_guests_ready_to_get_the_survey.discard(guest)
        if guest in self._mana_guests_who_got_the_survey:
            del self._mana_guests_who_got_the_survey[guest]

        # Safety
        if room.count_guests() == 0:
            if room.id_in_hotel in self._mana_rooms_ready_for_start_message:
                del self._mana_rooms_ready_for_start_message[room.id_in_hotel]

    async def __kick_all_guests(self, room: Room):
        """Kicks all guests of a room (telling them to "leave_room")."""

        self.print(f"Kicking all guests from room ID {room.id_in_hotel}, UUID {room.uuid}")
        current_guests = list(room.guests)
        for guest in current_guests:
            await self.__kick_guest(guest, room)

    def __reset_room_stream(self, room):
        """Resets the stream associated to a room of the hotel."""

        self.out(f"Resetting the stream associated to room ID {room.id_in_hotel}, UUID {room.uuid}")
        self._mana_streams_of_rooms[room.id_in_hotel].set(None)  # Clearing existing message
        self._mana_streams_of_rooms[room.id_in_hotel].clear_buffer()  # Forgetting not-sent-yet messages
        self._mana_streams_of_rooms[room.id_in_hotel].clear_uuid()  # Forgetting the UUID (for safety)
        self._mana_streams_of_rooms_tags[room.id_in_hotel] = 0  # Resetting the tag
        self._mana_streams_of_rooms_sent_tags[room.id_in_hotel] = -1  # Resetting the sent tag
        self._mana_streams_of_rooms_buffered_recipients[room.id_in_hotel].clear()  # Forgetting recipients

    def __reset_room(self, room):
        """Reset a room and clear the related data structures."""

        self.print(f"Resetting room ID {room.id_in_hotel}, UUID {room.uuid}")
        room.reset()  # Resetting the room guests, status, and timestamps
        self.__reset_room_stream(room)  # Resetting the room stream

        # We also make sure this room was not left in the list of rooms waiting for the welcome message
        if room.id_in_hotel in self._mana_rooms_ready_for_start_message:
            del self._mana_rooms_ready_for_start_message[room.id_in_hotel]

    def __add_to_history(self, formatted_msg: str):

        # Expected message like "**A:** Hi mate."
        sender, msg_only = WAgent.__unformat_message(formatted_msg)

        # Removing newlines
        msg_only = msg_only.replace("\n", " ").strip()

        # "**A:** Hi mate." received at 17:30:14 becomes:
        # --------------
        # (17:30:14) A:
        # Hi mate.
        #
        # --------------
        timestamp = self._part_room_stream.get_timestamp() \
            if sender != self._part_fake_name else self._part_proc_output_stream.get_timestamp()
        timestamp = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
        self._part_conversation.append(f"({timestamp}) {sender}:")
        self._part_conversation.append(msg_only)
        self._part_conversation.append("")

        # Convert the conversation to a single, long, string
        self._part_conversation_as_str = "\n".join(self._part_conversation)

        # Continuation
        timestamp = self._node_clock.get_time()
        timestamp = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
        continuation = (f"\n### CONTINUATION\nContinue the conversation as {self._part_fake_name}. "
                        f"Write only one message as {self._part_fake_name}. "
                        f"Do not generate dialogue for other participants. "
                        f"Respond in a casual, conversational tone consistent with a human participant."
                        f"\n\n({timestamp}) {self._part_fake_name}:")

        self._part_conversation_as_str += continuation

    def __disable_and_clear_all_room_streams(self):
        """Disable all room-related streams."""

        # Finding the room stream, where messages will be located
        for room_id in range(0, WAgent.tot_rooms):
            net_hash_to_stream_dict = self.find_streams(self._part_manager_peer_id,
                                                        f"stream_of_room_id_{room_id}")
            for net_hash, stream_dict in net_hash_to_stream_dict.items():
                for _, stream_obj in stream_dict.items():
                    if not stream_obj.props.is_public() and stream_obj.props.is_text():
                        stream_obj.clear_uuid()  # Resetting UUIDs on the guest side (important!)
                        stream_obj.set(None)  # Setting a None to clear pending messages
                        stream_obj.disable()

    @staticmethod
    def __format_message(sender_name: str, msg: str):
        """Format a message by adding the sender name."""

        return WAgent.sender_prefix + sender_name + WAgent.sender_suffix + msg

    @staticmethod
    def __unformat_message(msg: str) -> list[str]:
        """Get the message-only-part and the sender from a formatted message."""

        return msg[len(WAgent.sender_prefix):].split(WAgent.sender_suffix, 1)

    @staticmethod
    def __get_message_from_formatted_message(msg: str):
        """Get the message-only-part from a formatted message."""

        return msg[len(WAgent.sender_prefix):].split(WAgent.sender_suffix, 1)[1]

    @staticmethod
    def __get_sender_from_formatted_message(msg: str):
        """Get the sender name from a formatted message."""

        return msg[len(WAgent.sender_prefix):].split(WAgent.sender_suffix)[0]
