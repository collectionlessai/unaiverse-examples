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
import time
import uuid
from enum import Enum

from unaiverse.utils.logger import log
from .floor import Floor
from .config import Config
from unaiverse.custom import Custom
from unaiverse.streams import Stream
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction
from unaiverse.streams.dataprops import DataProps
from .utils import compute_check_in_proposals, format_message


class GuestStatus(Enum):
    TOLD_TO_JOIN_ROOM = "MOVE>CHAT"
    JUST_ARRIVED_AT_ROUND_TABLE = ">CHAT"
    AT_ROUND_TABLE = "CHAT"
    TOLD_TO_MOVE_TO_VOTING_BOOTH = "MOVE>VOTING"
    JUST_ARRIVED_IN_VOTING_BOOTH = ">VOTING"
    IN_VOTING_BOOTH = "VOTING"


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Setting system level options
        Custom.MAX_INTERACTIONS = 10000
        Custom.MAX_STREAM_DATA_WITHOUT_INTERACTIONS = 100

        # The floor managed by this agent (will be created when accepting role - peer ID needed)
        self.floor = None

        # Floor updates identifier and status to compare to decide who was added/removed
        self._floor_update_tag = 0
        self._floor_at_last_update = None
        self._floor_update_published_at = None

        # The proposed check-ins, stored to pass through actions
        self._proposed_check_ins = {}

        # Guests that presented themselves indicating their sponsoring hotel manager, to then check them in
        # (to distinguish them from guests who connected but never triggered the get_sponsored_guests action
        # in which they communicate who is their hotel manager)
        self._sponsored_guests = {}

        self._guest2vote_info = {}  # Guest who got the survey message -> [UUID of the request message, vote dict]
        self._guest2reminder_time = {}  # Guest who got the survey message -> last reminder message time
        self._wants_to_exist = set()  # Guest who wants to leave

        # Creating the pubsub stream where this manager will broadcast floor-related updates
        # and the direct message stream that is used to send votes to the hotel manager
        self.add_stream(Stream(props=DataProps(name="floor_updates", data_type="text", pubsub=True)))
        self.add_stream(Stream(props=DataProps(name="chat", data_type="text")))
        self.add_stream(Stream(props=DataProps(name="votes", data_type="text")))

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        # Creating the floor to manage (now we have the peer ID of the floor manager)
        self.floor = Floor(floor_manager=self.get_peer_id(),
                           id=str(uuid.uuid4()),
                           managed_guest_profiles=self.world_agents)

    async def remove_agent(self, peer_id: str):
        await super().remove_agent(peer_id)

        # Tell everybody in the room that this agent disconnected
        if self.floor is not None and self.floor.is_in_a_room(peer_id):
            room = self.floor.get_room_of(peer_id)
            disconnected_message = Config.disconnected_message.replace("<SOME_NAME>", room.fake_name_of(peer_id))
            for _guest in room.get_guests():
                if _guest != peer_id:
                    if not await self.send(action_name="get_status_msg",
                                           action_kwargs={"msg": disconnected_message},
                                           target=_guest):
                        await self.disconnect(_guest)

        self.__eject_and_clear_guest(peer_id)  # Send him out and clear all his info
        if peer_id in self._guest2vote_info:
            del self._guest2vote_info[peer_id]

    async def on_tick(self):
        connected_hotel_managers = self.get_agents_by_role("hotel_manager")
        connected_guests = self.get_agents_by_role("guest")
        self.floor.print(f"Hotel managers: {len(connected_hotel_managers)} "
                         f"| Guests: {len(self.floor.get_guests())}/{len(connected_guests)}")

    @action
    async def guest_joined_room(self, interaction: Interaction | None = None):
        if interaction is None:
            return False

        guest = interaction.target[0]
        self.floor.get_room_of(guest).set_status(guest, GuestStatus.JUST_ARRIVED_AT_ROUND_TABLE)
        self._guest2reminder_time[guest] = time.perf_counter()
        return True

    @action
    async def guest_joined_voting_booth(self, interaction: Interaction | None = None):
        if interaction is None:
            return False

        guest = interaction.target[0]
        if self.floor.is_in_a_room(guest):
            room = self.floor.get_room_of(guest)
            if room is not None:
                room.set_status(guest, GuestStatus.JUST_ARRIVED_IN_VOTING_BOOTH)
        return True

    @action
    async def guest_back_to_hall(self, guest: str | None = None, interaction: Interaction | None = None):
        callback_from_process_vote = False
        if guest is None:
            guest = interaction.target[0]
            callback_from_process_vote = True
            log.error(f"Callback guest_back_to_hall guest={guest}, "
                      f"callback_from_process_vote={callback_from_process_vote}")

        if not self.floor.is_in_a_room(guest):
            log.error(f"Not in a room, returning False")
            return False

        hotel_manager = self.floor.get_hotel_manager_of(guest)
        room = self.floor.get_room_of(guest)

        # Saving vote-related info
        if callback_from_process_vote:
            hotel_manager = self.floor.get_hotel_manager_of(guest)
            fake_name = room.fake_name_of(guest)
            fake_names_seen_so_far = room.get_fake_names_seen_by(guest)

            vote_dict = {
                "voter": room.get_unaid_of(guest),
                "vote": None,  # This will be filled when actually receiving the vote from the processor stream
                "ground_truth": {
                    votee_fake_name: (room.get_ground_truth_of(votee), room.get_unaid_of(votee))
                    for votee_fake_name in fake_names_seen_so_far
                    if votee_fake_name != fake_name
                    if (votee := room.guest_whose_fake_name_is(votee_fake_name)) is not None
                },
                "session_id": self.floor.id + ":" + room.id,
                "floor_manager": self.get_peer_id(),
                "hotel_manager": hotel_manager,
                "msgs_from_votee": {
                    votee_fake_name: room.count_messages_recv_by(fake_name=fake_name,
                                                                 from_fake_name=votee_fake_name)
                    for votee_fake_name in fake_names_seen_so_far if votee_fake_name != fake_name
                },
                "msgs_from_voter": {
                    votee_fake_name: room.count_messages_recv_by(fake_name=votee_fake_name,
                                                                 from_fake_name=fake_name)
                    for votee_fake_name in fake_names_seen_so_far if votee_fake_name != fake_name
                }
            }

            log.error(f"Built vote dict")

            if guest in self._guest2vote_info:
                log.error(f"Saved vote dict")
                self._guest2vote_info[guest][1] = vote_dict

        # Telling hotel manager that we reset our state touch with the floor manager he suggested
        log.error(f"Telling hotel manager to run his 'guest_back_to_hall'")
        if not await self.send(action_name="guest_back_to_hall",
                               action_kwargs={"guest": guest},
                               from_state="discovery_complete",
                               target=hotel_manager):
            await self.disconnect(hotel_manager)

        # Telling guest to go back to hall (no matter from what state)
        log.error(f"Sending guest to hall (telling guest to run 'goto_hall')")
        if not await self.send(action_name="goto_hall",
                               from_state="room_voting_booth" if not callback_from_process_vote else "vote_provided",
                               target=guest):
            await self.disconnect(guest)

        # Clearing guest from floor
        log.error(f"Clearing guest")
        self.__eject_and_clear_guest(guest)  # Send him out and clear all his info
        return True

    @action
    async def get_guest_sponsor(self, hotel_manager: str | None = None, interaction: Interaction | None = None):
        if hotel_manager is None or hotel_manager not in self.world_agents or interaction is None:
            return False

        guest = interaction.requester
        role = self.get_role(guest)
        if role == "guest":
            self._sponsored_guests[guest] = hotel_manager  # Check-in order will follow the order in this dict, FIFO
            return True
        else:
            return False

    @action
    async def check_in(self):

        # Getting list of guests to be checked in
        if len(self._sponsored_guests) > 0:

            # A guest to check in is one that is not in a room yet
            guests_to_check_in = [a for a in self._sponsored_guests.keys()
                                  if not self.floor.is_in_a_room(a)]
        else:
            guests_to_check_in = []
        if len(guests_to_check_in) == 0:
            return False

        # Proposing check-ins accordingly to the current status of the hotel
        # If there is no room left, some guests will be reconsidered in the future
        proposed_check_ins, _ = compute_check_in_proposals(self.floor, guests_to_check_in)
        self._proposed_check_ins.update(proposed_check_ins)
        return True

    @action
    async def send_to_room(self):

        # Getting proposed check-ins and asking guests to reach the proposed floor
        at_least_one_sent = False
        for guest, proposed_check_in in self._proposed_check_ins.items():
            hotel_manager = self._sponsored_guests[guest]
            room = self.floor.get_room(proposed_check_in['room_id'])

            # If the floor is in the middle of a naming clash, it won't accept new guests
            if not self.floor.insert(guest, self.floor.get_profile_of(guest), hotel_manager, room):
                continue

            # Sending to room
            if not await self.send(action_name="goto_room",
                                   from_state="ready_for_room",
                                   target=guest,
                                   callback="guest_joined_room"):
                await self.disconnect(guest)
            else:
                # Marking the guest as somebody who was asked to go to a room (handled in the joined_room callback)
                room.set_status(guest, GuestStatus.TOLD_TO_JOIN_ROOM)

                at_least_one_sent = True

        self._proposed_check_ins.clear()
        return at_least_one_sent

    @action
    async def handle_guests_by_status(self):
        something_was_sent = False
        for guest in self.floor.get_managed_guests():
            if self.floor.is_in_a_room(guest):
                room = self.floor.get_room_of(guest)

                # A guest wants to exit or it is timeout! Test ended, GET OUT OF HERE!
                if (room.get_status(guest) == GuestStatus.AT_ROUND_TABLE and
                        (room.get_time_in_current_status(guest) >= Config.test_duration or
                         guest in self._wants_to_exist)):
                    if not await self.send(action_name="goto_voting_booth",
                                           from_state="room_round_table",
                                           callback="guest_joined_voting_booth",
                                           target=guest):
                        await self.disconnect(guest)
                    something_was_sent = True
                    room.set_status(guest, GuestStatus.TOLD_TO_MOVE_TO_VOTING_BOOTH)
                    continue

                # Too much time in voting booth: GET OUT OF THE ROOM!
                if (room.get_status(guest) == GuestStatus.IN_VOTING_BOOTH and
                        room.get_time_in_current_status(guest) > Config.survey_reply_time):
                    await self.guest_back_to_hall(guest)  # Send back to hall
                    something_was_sent = True
                    continue

                # Too much time to join the room we told you: GET OUT OF MY FLOOR!
                if (room.get_status(guest) == GuestStatus.TOLD_TO_JOIN_ROOM and
                        room.get_time_in_current_status(guest) > Config.moving_time):
                    await self.disconnect(guest)
                    continue

                # Too much time in to move to the voting booth and get vote request message: GET OUT OF MY FLOOR!
                if (room.get_status(guest) == GuestStatus.TOLD_TO_MOVE_TO_VOTING_BOOTH and
                        room.get_time_in_current_status(guest) > Config.moving_time):
                    await self.disconnect(guest)
                    continue

                # This guest just confirmed that he entered the room, let's send him the 'start conversation' message,
                # and let's tell the others that he joined
                if room.get_status(guest) == GuestStatus.JUST_ARRIVED_AT_ROUND_TABLE:
                    other_guests_names = sorted([room.fake_name_of(_guest)
                                                 for _guest in room.get_guests()
                                                 if _guest != guest and
                                                 room.get_status(_guest) in {GuestStatus.AT_ROUND_TABLE,
                                                                             GuestStatus.JUST_ARRIVED_AT_ROUND_TABLE}])
                    if len(other_guests_names) == 0:
                        start_message = Config.start_message_nobody
                    else:
                        start_message = Config.start_message
                    start_message = (start_message.
                                     replace("<YOUR_NAME>", room.fake_name_of(guest)).
                                     replace("<OTHER_NAMES>", ", ".join(other_guests_names)))

                    if not await self.send(action_name="get_status_msg",
                                           action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                start_message)},
                                           from_state="room_round_table",
                                           target=guest):
                        await self.disconnect(guest)
                    else:
                        something_was_sent = True
                        joined_message = Config.joined_message.replace("<SOME_NAME>", room.fake_name_of(guest))
                        for _guest in room.get_guests():
                            if _guest != guest:
                                if not await self.send(action_name="get_status_msg",
                                                       action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                            joined_message)},
                                                       from_state="room_round_table",
                                                       target=_guest):
                                    await self.disconnect(_guest)
                    room.set_status(guest, GuestStatus.AT_ROUND_TABLE)
                    continue

                # This guest just confirmed that he left the room, let's send him the process 'survey' request
                # and let's tell the others that he left
                if room.get_status(guest) == GuestStatus.JUST_ARRIVED_IN_VOTING_BOOTH:
                    fake_name = room.fake_name_of(guest)
                    other_guests_names = sorted(list(room.get_fake_names_met_by(fake_name)))
                    survey_msg = (
                        Config.survey_message if len(other_guests_names) > 0 else Config.survey_message_nobody).replace(
                        "<YOUR_NAME>", room.fake_name_of(guest)).replace("<OTHER_NAMES>", ", ".join(other_guests_names))

                    # We send the message to the guest as if it was generated by our processor (even if it is not),
                    # so that the guest will display it on screen (the guest only displays stream-related data, so
                    # sending as bare data_samples with no stream association would keep the message hidden to the GUI)
                    interaction = await self._send(action_name="process",
                                                   from_state="room_voting_booth",
                                                   callback="guest_back_to_hall",
                                                   target=guest)
                    if interaction is None:
                        await self.disconnect(guest)
                    else:
                        something_was_sent = True
                        self._guest2vote_info[guest] = [interaction.uuid, None]
                        if not await self.send(action_name="get_status_msg",
                                               action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                    survey_msg),
                                                              "process_uuid": interaction.uuid},
                                               from_state="room_voting_booth",
                                               target=guest):
                            await self.disconnect(guest)

                        # Telling others that this guest left
                        left_message = Config.left_message.replace("<SOME_NAME>", fake_name)
                        for _guest in room.get_guests():
                            if _guest != guest:
                                if not await self.send(action_name="get_status_msg",
                                                       action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                            left_message)},
                                                       from_state="room_round_table",
                                                       target=_guest):
                                    await self.disconnect(_guest)
                        room.set_status(guest, GuestStatus.IN_VOTING_BOOTH)
                    continue

                # From time to time send a reminder
                if (room.get_status(guest) == GuestStatus.AT_ROUND_TABLE and
                        ((time.perf_counter() - self._guest2reminder_time[guest]) > Config.send_reminder_every)):
                    time_left = Config.test_duration - room.get_time_in_current_status(guest)
                    reminder_msg = (Config.reminder_message.
                                    replace("<TIME_LEFT>", str(time_left)))
                    if time_left > 0:
                        if not await self.send(action_name="get_status_msg",
                                               action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                    reminder_msg)},
                                               from_state="room_round_table",
                                               target=guest):
                            await self.disconnect(guest)
                        else:
                            something_was_sent = True
                    self._guest2reminder_time[guest] = time.perf_counter()

        return something_was_sent

    @action
    async def pub_floor_updates(self):
        """
        An update packet is a string that encodes a JSON with the following format, where ALL elements are -strings-:

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
        time_now = self.clock.get_time()
        if self._floor_update_published_at is None:
            self._floor_update_published_at = time_now
        if (time_now - self._floor_update_published_at) < Config.send_floor_updates_every:
            return False
        else:
            self._floor_update_published_at = time_now

        if self._floor_at_last_update is None:

            # First time: all guests are new
            inserted_guests = [[room.id, guest, self.floor.get_hotel_manager_of(guest)]
                               for room in self.floor.get_rooms()
                               for guest in room.get_guests()]
            ejected_guests = []
        else:

            # Other times: compare with the previous floor status to decide who was added and who was removed
            inserted_guests = [[room.id, guest, self.floor.get_hotel_manager_of(guest)]
                               for room in self.floor.get_rooms()
                               for guest in room.get_guests()
                               if (prev := self._floor_at_last_update.get_room(room.id)) is None
                               or guest not in prev.get_guests()]
            ejected_guests = [[room.id, guest]
                              for room in self._floor_at_last_update.get_rooms()
                              for guest in room.get_guests()
                              if (curr := self.floor.get_room(room.id)) is None
                              or guest not in curr.get_guests()]

        update = {
            "floor_id": self.floor.id,
            "floor_status": [[room.id, room.count_guests()] for room in self.floor.get_rooms()],
            "inserted_guests": inserted_guests,
            "ejected_guests": ejected_guests
        }

        self.get_stream("floor_updates").set(data=json.dumps(update), data_tag=self._floor_update_tag)
        self._floor_update_tag += 1
        live_backup = self.floor.live
        self.floor.live = None
        self._floor_at_last_update = copy.deepcopy(self.floor)
        self.floor.live = live_backup
        return True

    @action
    async def send_votes(self):
        """
        A vote packet is a string that encodes a JSON with the following format:

        {
            "voter": VOTER_UNAID,
            "vote": FULL_VOTE_MESSAGE,
            "ground_truth": (DICT) CANDIDATE_VOTEE_FAKE_NAME -> ("human" | "ai", CANDIDATE_VOTEE_UNAID),
            "session_id": FLOOR_ID:ROOM_ID,
            "floor_manager": FLOOR_MANAGER_PEER_ID,
            "hotel_manager": HOTEL_MANAGER_PEER_ID,
            "msgs_from_votee": (DICT) CANDIDATE_VOTEE_FAKE_NAME -> STRING_REPRESENTING_A_NUMBER,
            "msgs_from_voter": STRING_REPRESENTING_A_NUMBER
        }
        """
        some_votes_were_found = False
        to_remove = []

        for guest, (vote_interaction_uuid, vote_dict) in self._guest2vote_info.items():
            if vote_dict is None:
                continue
            guest_processor_stream = self.get_stream("processor", guest, data_type="text")
            vote_msg = guest_processor_stream.get(requested_by="send_votes", uuid=vote_interaction_uuid)
            if vote_msg is None:
                continue

            vote_dict["vote"] = vote_msg
            hotel_manager = vote_dict["hotel_manager"]

            await self.send(data_samples={"votes": json.dumps(vote_dict)},
                            target=hotel_manager)

            some_votes_were_found = True
            to_remove.append(guest)

        for guest in to_remove:
            del self._guest2vote_info[guest]
        return some_votes_were_found

    @action
    async def apply_violations(self, guests: list[str] | None = None):
        if guests is None or len(guests) == 0:
            return False

        for guest in guests:
            await self.send(action_name="get_status_msg",
                            action_kwargs={"msg": Config.violation_message},
                            target=guest)
            await self.disconnect(guest)  # These two lines do not need any if... we want to send and disconnect
        return True

    @action
    async def get_msg_and_broadcast(self, msg: str | None = None, interaction: Interaction | None = None):
        guest = interaction.requester

        if self.floor.is_in_a_room(guest) and (msg is not None and len(msg) > 0):

            # Room messages are altered by adding the fake name of the sender
            # (Here we know that the processor of the floor manager has a single input, and it is text)
            fake_name = self.floor.get_room_of(guest).fake_name_of(guest)
            altered_msg = format_message(fake_name, msg)
            room = self.floor.get_room_of(guest)

            if msg.strip().lower() == Config.exit_trigger_message.lower():
                self._wants_to_exist.add(guest)
                return True

            # Broadcasting to the other guests
            for _guest in room.get_guests():
                _fake_name = room.fake_name_of(_guest)
                if _fake_name != fake_name and room.get_status(_guest) == GuestStatus.AT_ROUND_TABLE:

                    # We send the message to the guest as if it was generated by our processor (even if it is not),
                    # so that the guest will display it on screen (the guest only displays stream-related data, so
                    # sending as bare data_samples with no stream association would keep the message hidden to the GUI)
                    if not await self.send(action_name="get_msgs",
                                           data_samples={"chat": altered_msg},
                                           target=_guest):
                        await self.disconnect(_guest)
                    else:
                        room.inc_message_exchanges(fake_name_from=fake_name, fake_name_to=_fake_name)
            return True
        else:
            return False

    def __eject_and_clear_guest(self, guest):
        if guest in self._sponsored_guests:
            del self._sponsored_guests[guest]
        if guest in self._wants_to_exist:
            self._wants_to_exist.remove(guest)
        if guest in self._guest2reminder_time:
            del self._guest2reminder_time[guest]
        if self.floor is not None:  # Keep this
            log.error("Ejecting from floor now!")
            self.floor.eject(guest)
