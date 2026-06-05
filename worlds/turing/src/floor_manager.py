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
import json
import time
import uuid
import asyncio
from enum import Enum
from .floor import Floor
from .config import Config
from unaiverse.custom import Custom
from unaiverse.streams import Stream
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction
from unaiverse.streams.dataprops import DataProps
from concurrent.futures import ThreadPoolExecutor
from .utils import compute_check_in_proposals, format_message
asyncio.get_event_loop().set_default_executor(ThreadPoolExecutor(max_workers=128))


# The floor manager keeps an internal estimate of the status of each guest, accordingly to the following possible states
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

        # Setting system level options (push it up w.r.t. the default ones...this manager has some work to do!)
        Custom.MAX_INTERACTIONS = 10000
        Custom.MAX_STREAM_DATA_WITHOUT_INTERACTIONS = 100
        self.im.max_interactions = Custom.MAX_INTERACTIONS  # Overwrite this, since it was set at object creation

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

        # Attributes that handle some guest-status related info
        self._guest2vote_info = {}  # Guest who got the survey message -> [UUID of the request message, vote dict]
        self._guest2reminder_time = {}  # Guest who got the survey message -> last reminder message time
        self._wants_to_exit = set()  # Guest who wants to leave

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        # Creating the floor to manage (now we have the peer ID of the floor manager, we couldn't create it earlier)
        self.floor = Floor(floor_manager=self.get_peer_id(),
                           id=str(uuid.uuid4()),
                           managed_guest_profiles=self.world_agents)

        # Creating the pubsub stream where this manager will broadcast floor-related updates
        # and the direct message stream that is used to send votes to the hotel manager
        self.add_stream(Stream(props=DataProps(name="floor_updates", data_type="text", pubsub=True)))  # pubsub
        self.add_stream(Stream(props=DataProps(name="chat", data_type="text")))  # Ordinary conversation
        self.add_stream(Stream(props=DataProps(name="votes", data_type="text")))  # Votes only

        # Updating profile (recall that this class is created when joining the world, so the profile must be updated)
        self.update_streams_in_profile()

    async def remove_agent(self, peer_id: str):
        await super().remove_agent(peer_id)

        # Tell everybody in the room that this agent disconnected
        if self.floor is not None and self.floor.is_in_a_room(peer_id):
            room = self.floor.get_room_of(peer_id)

            # Send this message only if the agent was chatting (i.e., not if he was in the voting booth)
            if room.get_status(peer_id) in {GuestStatus.JUST_ARRIVED_AT_ROUND_TABLE, GuestStatus.AT_ROUND_TABLE}:
                disconnected_message = Config.disconnected_message.replace("<SOME_NAME>", room.fake_name_of(peer_id))
                others = [g for g in list(room.get_guests()) if g != peer_id]

                # Do not check if this fails: if you do, and then you disconnect when it fails,
                # this will in turn call remove_agent, creating a weird loop
                await asyncio.gather(*[
                    self.send(action_name="get_status_msg",
                              action_kwargs={"msg": format_message(Config.manager_fake_name, disconnected_message)},
                              target=_guest,
                              volatile=True)
                    for _guest in others
                ], return_exceptions=True)

        # Send the guest out of the floor/room and clear all his vote-related info
        # (the other status-related sets and dicts are cleared by the following method; but NOT the vote info, since
        # the floor manager will pick up a vote from this guest at a later stage, maybe even after he disconnected)
        self.__eject_and_clear_guest(peer_id)

    async def on_tick(self):

        # Print info on screen
        connected_hotel_managers = self.get_agents_by_role("hotel_manager")
        connected_guests = self.get_agents_by_role("guest")
        self.floor.print(f"[Managed/Connected] Hotel managers: */{len(connected_hotel_managers)} "
                         f"| Guests: {len(self.floor.get_guests())}/{len(connected_guests)}")

    @action
    async def guest_joined_room(self, interaction: Interaction | None = None):
        """Callback triggered when a guest confirmed to have joined a room."""
        if interaction is None:  # Safety check
            return False

        # The guest is the target of the original interaction we sent (recall this is a callback)
        guest = interaction.target[0]

        # Update guest status
        self.floor.get_room_of(guest).set_status(guest, GuestStatus.JUST_ARRIVED_AT_ROUND_TABLE)
        self._guest2reminder_time[guest] = time.perf_counter()  # Started counting time for remind-messages purpose
        return True

    @action
    async def guest_joined_voting_booth(self, interaction: Interaction | None = None):
        """Callback triggered when a guest confirmed to have joined the voting booth."""
        if interaction is None:  # Safety
            return False

        # The guest is the target of the original interaction we sent (recall this is a callback)
        guest = interaction.target[0]

        # Update guest status
        if self.floor.is_in_a_room(guest):  # Safety: this is supposed to be True
            room = self.floor.get_room_of(guest)
            if room is not None:  # Safety: this is supposed to be not None
                room.set_status(guest, GuestStatus.JUST_ARRIVED_IN_VOTING_BOOTH)
        return True

    @action
    async def guest_back_to_hall(self, guest: str | None = None, interaction: Interaction | None = None):
        """This method is booth used as a callback and also explicitly called."""

        # Let's distinguish if we are in the context of a callback from a vote-process-operation-completed,
        # or if we are just calling the method somewhere else
        callback_from_process_vote = False
        if guest is None:
            assert interaction is not None
            guest = interaction.target[0]
            callback_from_process_vote = True

        # Safety
        if not self.floor.is_in_a_room(guest):
            return True  # Return true to complete the action and hence burn the interaction

        # Getting info
        hotel_manager = self.floor.get_hotel_manager_of(guest)
        room = self.floor.get_room_of(guest)

        # Saving vote-related info
        if callback_from_process_vote:
            hotel_manager = self.floor.get_hotel_manager_of(guest)
            fake_name = room.fake_name_of(guest)
            fake_names_seen_so_far = room.get_fake_names_seen_by(fake_name)

            # This dictionary is almost filled, it misses the actual vote (it will be sent in its own stream)
            vote_dict = {
                "voter": room.get_unaid_of(guest),
                "voter_nature": room.get_ground_truth_of(guest),
                "vote": None,  # This will be filled when actually receiving the vote from the processor stream
                "ground_truth": {
                    votee_fake_name: (room.get_ground_truth_of_fake_name(votee_fake_name),
                                      room.get_unaid_of_fake_name(votee_fake_name))
                    for votee_fake_name in fake_names_seen_so_far
                    if votee_fake_name != fake_name
                    if room.guest_whose_fake_name_is(votee_fake_name) is not None
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

            # We save the vote dictionary as second element of the tuple below
            # Recall that the first one is the UUID of the voting interaction
            if guest in self._guest2vote_info:
                self._guest2vote_info[guest][1] = vote_dict

        # Telling hotel manager that we reset our state touch with the floor manager he suggested
        # Independent peers, independent sends.
        hm_ret, g_ret = await asyncio.gather(
            self.send(action_name="guest_back_to_hall",
                      action_kwargs={"guest": guest},
                      from_state="discovery_complete",
                      target=hotel_manager,
                      volatile=True),
            self.send(action_name="goto_hall",
                      from_state="room_voting_booth" if not callback_from_process_vote else "vote_provided",
                      target=guest,
                      volatile=True),
            return_exceptions=True
        )
        if isinstance(hm_ret, Exception) or not hm_ret:
            await self.disconnect(hotel_manager)
        if isinstance(g_ret, Exception) or not g_ret:
            await self.disconnect(guest)

        # Clearing guest from floor
        self.__eject_and_clear_guest(guest)  # Send him out and clear all his info (but not the vote-info)
        return True

    @action
    async def get_guest_sponsor(self, hotel_manager: str | None = None, interaction: Interaction | None = None):
        if hotel_manager is None or hotel_manager not in self.world_agents or interaction is None:
            return True  # Always return True to burn the interaction

        guest = interaction.requester
        assert guest is not None
        role = self.get_role(guest)
        if role == "guest":
            self._sponsored_guests[guest] = hotel_manager  # Check-in order will follow the order in this dict, FIFO
        return True

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
        # must stay sequential because Room.insert mutates room state (fake-name allocation)
        ready = []  # list of (guest, room) that were accepted by the floor
        for guest, proposed_check_in in self._proposed_check_ins.items():
            hotel_manager = self._sponsored_guests[guest]
            room = self.floor.get_room(proposed_check_in['room_id'])

            # If the floor is in the middle of a naming clash, it won't accept new guests
            if not self.floor.insert(guest, self.floor.get_profile_of(guest), hotel_manager, room):
                continue
            ready.append((guest, room))

        # Send phase — parallel, one send per guest
        results = await asyncio.gather(*[
            self.send(action_name="goto_room",
                      from_state="ready_for_room",
                      target=guest,
                      callback="guest_joined_room")
            for guest, _ in ready
        ], return_exceptions=True)

        at_least_one_sent = False
        for (guest, room), ret in zip(ready, results):
            if isinstance(ret, Exception) or not ret:
                await self.disconnect(guest)
            else:
                # Marking the guest as somebody who was asked to go to a room (handled in the joined_room callback)
                room.set_status(guest, GuestStatus.TOLD_TO_JOIN_ROOM)
                at_least_one_sent = True

        self._proposed_check_ins.clear()
        return at_least_one_sent

    @action
    async def handle_guests_by_status(self):
        """Handle each single guest in a different way, in function of his current status."""

        # We run it in "parallel" over all guests
        results = await asyncio.gather(
            *[self.__handle_single_guest_by_status(guest) for guest in list(self.floor.get_guests())],
            return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                log.error(f"Exception in '__handle_single_guest_by_status': {str(r)}")
        return any(r is True for r in results if not isinstance(r, Exception))

    async def __handle_single_guest_by_status(self, guest: str) -> bool:
        """Handle a specific guest in function of his current status."""

        if not self.floor.is_in_a_room(guest):  # Safety
            return False
        room = self.floor.get_room_of(guest)

        # A guest wants to exit, or it is retry_timeout! Test ended, GET OUT OF HERE!
        if (room.get_status(guest) == GuestStatus.AT_ROUND_TABLE and
                (room.get_time_in_current_status(guest) >= Config.test_duration or
                 guest in self._wants_to_exit)):
            if not await self.send(action_name="goto_voting_booth",
                                   from_state="room_round_table",
                                   callback="guest_joined_voting_booth",
                                   target=guest):
                await self.disconnect(guest)
            room.set_status(guest, GuestStatus.TOLD_TO_MOVE_TO_VOTING_BOOTH)
            return True

        # Too much time in voting booth: GET OUT OF THE ROOM!
        if (room.get_status(guest) == GuestStatus.IN_VOTING_BOOTH and
                room.get_time_in_current_status(guest) > Config.survey_reply_time):
            await self.guest_back_to_hall(guest)
            return True

        # Too much time to join the room we told you: GET OUT OF MY FLOOR!
        if (room.get_status(guest) == GuestStatus.TOLD_TO_JOIN_ROOM and
                room.get_time_in_current_status(guest) > Config.moving_time):
            await self.disconnect(guest)
            return False

        # Too much time to move to the voting booth: GET OUT OF MY FLOOR!
        if (room.get_status(guest) == GuestStatus.TOLD_TO_MOVE_TO_VOTING_BOOTH and
                room.get_time_in_current_status(guest) > Config.moving_time):
            await self.disconnect(guest)
            return False

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

            sent = False
            if not await self.send(action_name="get_status_msg",
                                   action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                        start_message)},
                                   from_state="room_round_table",
                                   target=guest,
                                   volatile=True):
                await self.disconnect(guest)
            else:
                sent = True
                joined_message = Config.joined_message.replace("<SOME_NAME>", room.fake_name_of(guest))
                await asyncio.gather(*[
                    self.__send_or_disconnect(_guest,
                                              action_name="get_status_msg",
                                              action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                   joined_message)},
                                              from_state="room_round_table",
                                              volatile=True)
                    for _guest in room.get_guests() if _guest != guest
                ])
            room.set_status(guest, GuestStatus.AT_ROUND_TABLE)
            return sent

        # This guest just confirmed that he left the room, let's send him the 'process-survey' request
        # and let's tell the others that he left
        if room.get_status(guest) == GuestStatus.JUST_ARRIVED_IN_VOTING_BOOTH:
            fake_name = room.fake_name_of(guest)
            other_guests_names = sorted(list(room.get_fake_names_met_by(fake_name)))

            # Interacting with the guest's processor
            survey_msg = (
                Config.survey_message if len(other_guests_names) > 0 else Config.survey_message_nobody).replace(
                "<YOUR_NAME>", room.fake_name_of(guest)).replace("<OTHER_NAMES>", ", ".join(other_guests_names))

            interaction = await self._send(action_name="process",
                                           from_state="room_voting_booth",
                                           callback="guest_back_to_hall",
                                           target=guest)
            if interaction is None:
                await self.disconnect(guest)
                return False

            # Interacting with the guests for two reasons:
            # (1) Send the "vote-request" message to the handled guest
            # (2) Tell other guest that the handled guest left
            self._guest2vote_info[guest] = [interaction.uuid, None]
            left_message = Config.left_message.replace("<SOME_NAME>", fake_name)
            await asyncio.gather(
                self.__send_or_disconnect(guest,
                                          action_name="get_status_msg",
                                          action_kwargs={"msg": format_message(Config.manager_fake_name, survey_msg),
                                                         "process_uuid": interaction.uuid},
                                          from_state="room_voting_booth",
                                          volatile=True),
                *[self.__send_or_disconnect(_guest,
                                            action_name="get_status_msg",
                                            action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                 left_message)},
                                            from_state="room_round_table",
                                            volatile=True)
                  for _guest in room.get_guests() if _guest != guest]
            )
            room.set_status(guest, GuestStatus.IN_VOTING_BOOTH)
            return True

        # From time to time send a reminder
        if (room.get_status(guest) == GuestStatus.AT_ROUND_TABLE and
                ((time.perf_counter() - self._guest2reminder_time[guest]) > Config.send_reminder_every)):
            time_left = Config.test_duration - room.get_time_in_current_status(guest)
            sent = False
            if time_left > 0:
                reminder_message = (Config.reminder_message.replace("<TIME_LEFT>", str(time_left)).
                                    replace("<YOUR_NAME>", room.fake_name_of(guest)))
                if not await self.send(action_name="get_status_msg",
                                       action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                            reminder_message)},
                                       from_state="room_round_table",
                                       target=guest,
                                       volatile=True):
                    await self.disconnect(guest)
                else:
                    sent = True
            self._guest2reminder_time[guest] = time.perf_counter()  # Remember the last time a reminder was sent
            return sent

        return False

    async def __send_or_disconnect(self, target: str, **send_kwargs) -> None:
        """Sends an interaction and disconnect the target if sending failed."""
        if not await self.send(target=target, **send_kwargs):
            await self.disconnect(target)

    @action
    async def pub_floor_updates(self):
        """Publish packets telling the status of this floor (who joined, who was ejected, how many guests are there).

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

        # Check if it is time to send the update
        time_now = self.clock.get_time()
        if self._floor_update_published_at is None:
            self._floor_update_published_at = time_now
        if (time_now - self._floor_update_published_at) < Config.send_floor_updates_every:
            return False
        else:
            self._floor_update_published_at = time_now

        # Determining who was inserted or rejected by comparing with the previously saved floor status
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

        # Update packet
        update = {
            "floor_id": self.floor.id,
            "floor_status": [[room.id, room.count_guests()] for room in self.floor.get_rooms()],
            "inserted_guests": inserted_guests,
            "ejected_guests": ejected_guests
        }

        # Setting data on the pubsub stream
        floor_updates_stream = self.get_stream("floor_updates")
        assert floor_updates_stream is not None
        floor_updates_stream.set(data=json.dumps(update), data_tag=self._floor_update_tag)
        self._floor_update_tag += 1

        # Saving the floor status for future comparisons
        live_backup = self.floor.live
        self.floor.live = None
        self._floor_at_last_update = self.floor.copy_floor_status()
        self.floor.live = live_backup
        return True

    @action
    async def send_votes(self):
        """Send votes to the hotel manager.

        A vote packet is a string that encodes a JSON with the following format:

        {
            "voter": VOTER_UNAID,
            "voter_nature": "human" | "ai"
            "vote": FULL_VOTE_MESSAGE,
            "ground_truth": (DICT) CANDIDATE_VOTEE_FAKE_NAME -> ("human" | "ai", CANDIDATE_VOTEE_UNAID),
            "session_id": FLOOR_ID:ROOM_ID,
            "floor_manager": FLOOR_MANAGER_PEER_ID,
            "hotel_manager": HOTEL_MANAGER_PEER_ID,
            "msgs_from_votee": (DICT) CANDIDATE_VOTEE_FAKE_NAME -> STRING_REPRESENTING_A_NUMBER,
            "msgs_from_voter": STRING_REPRESENTING_A_NUMBER
        }
        """
        list_of_vote_dicts_by_hotel_manager = {}
        to_remove = []

        # Votes are expected to be found on the guest's processor, with a UUID that we saved in advance
        for guest, (vote_interaction_uuid, vote_dict) in self._guest2vote_info.items():
            if vote_dict is None:

                # If the vote_dict is None, then the guest was asked to go to the voting booth and was asked for a vote,
                # but, if he disconnected, he never made it
                if guest not in self.world_agents:
                    to_remove.append(guest)
                continue

            # Getting the stream where the vote is
            guest_processor_stream = self.get_stream("processor", guest, data_type="text")

            # If the guest disconnected when he is in the voting booth, but still did not vote, then we remove his
            # vote dictionary (that is still missing the actual vote message) - the second check
            # (guest not in self.world_agents) should be redundant
            if guest_processor_stream is None or (guest not in self.world_agents):
                to_remove.append(guest)
                continue

            # Getting the actual vote message (the string)
            vote_msg = guest_processor_stream.get(requested_by="send_votes", uuid=vote_interaction_uuid)
            if vote_msg is None:
                continue

            vote_dict["vote"] = vote_msg
            hotel_manager = vote_dict["hotel_manager"]

            if hotel_manager not in list_of_vote_dicts_by_hotel_manager:
                list_of_vote_dicts_by_hotel_manager[hotel_manager] = []
            list_of_vote_dicts_by_hotel_manager[hotel_manager].append(vote_dict)
            to_remove.append(guest)

        for guest in to_remove:
            del self._guest2vote_info[guest]

        # We send all the collected votes to each hotel manager (recall that a hotel manager only gets votes from
        # the guests that he sponsored), by loading in on our "votes" stream, paired with an "empty" interaction
        # targeted to the hotel manager
        if list_of_vote_dicts_by_hotel_manager:
            await asyncio.gather(*[
                self.send(data_samples={"votes": json.dumps(list_of_vote_dicts)},
                          target=hotel_manager)
                for hotel_manager, list_of_vote_dicts in list_of_vote_dicts_by_hotel_manager.items()
            ], return_exceptions=True)

        return len(list_of_vote_dicts_by_hotel_manager) > 0

    @action
    async def apply_violations(self, guests: list[str] | None = None):
        """Kill those guests that were reported as illegally connected to this floor. """

        if guests is None or len(guests) == 0:
            return True  # Always return True to burn the interaction

        # We tell each violating guest that he indeed did a violation, and we disconnect him, that will in turn
        # trigger "remove_agent", fully pushing the guest out of the floor.
        # Send all violation messages in parallel, then disconnect (disconnect must follow send).
        await asyncio.gather(*[
            self.send(action_name="get_status_msg",
                      action_kwargs={"msg": Config.violation_message},
                      target=guest)
            for guest in guests
        ], return_exceptions=True)

        # This happens after send, no matter if send succeeded or not
        await asyncio.gather(*[self.disconnect(guest) for guest in guests], return_exceptions=True)

        return True

    @action
    async def get_msg_and_broadcast(self, msg: str | None = None, interaction: Interaction | None = None):
        """Get a message from a guest and broadcast it to all the other ones in the same room."""
        if interaction is None:
            return False

        guest = interaction.requester

        if self.floor.is_in_a_room(guest) and (msg is not None and len(msg) > 0):
            fake_name = self.floor.get_room_of(guest).fake_name_of(guest)
            altered_msg = format_message(fake_name, msg)
            room = self.floor.get_room_of(guest)

            if msg.strip().lower() == Config.exit_trigger_message.lower():
                self._wants_to_exit.add(guest)
                return True

            async def _broadcast_to(_guest):
                _fake_name = room.fake_name_of(_guest)
                if _fake_name != fake_name and room.get_status(_guest) == GuestStatus.AT_ROUND_TABLE:
                    if not await self.send(action_name="get_msgs",
                                           data_samples={"chat": altered_msg},
                                           target=_guest,
                                           volatile=True):
                        await self.disconnect(_guest)
                    else:
                        room.inc_message_exchanges(fake_name_from=fake_name, fake_name_to=_fake_name)

            # Try to broadcast in "parallel"
            await asyncio.gather(*[_broadcast_to(g) for g in room.get_guests()])

        return True

    def __eject_and_clear_guest(self, guest):
        """Send a guest of the floor/room, without clearing his vote-related info (they might be needed to get his vote
        after he disconnected)."""

        if guest in self._sponsored_guests:
            del self._sponsored_guests[guest]
        if guest in self._wants_to_exit:
            self._wants_to_exit.remove(guest)
        if guest in self._guest2reminder_time:
            del self._guest2reminder_time[guest]
        if self.floor is not None:  # Keep this
            self.floor.eject(guest)
