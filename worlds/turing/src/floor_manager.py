import copy
import json
import uuid
from enum import Enum
from .floor import Floor
from .config import Config
from unaiverse.custom import Custom
from unaiverse.streams import Stream
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction
from unaiverse.streams.dataprops import DataProps
from .utils import compute_check_in_proposals, format_message


class GuestStatus(Enum):
    WAITING_TO_JOIN_ROOM = "WAIT"
    JUST_ARRIVED_AT_ROUND_TABLE = "<CHAT>"
    AT_ROUND_TABLE = "CHAT"
    JUST_ARRIVED_IN_VOTING_BOOTH = "<VOTING>"
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

        self._guest2vote_request = {}  # Guest who got the survey message -> (UUID of the request message, ask time)
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
            self.floor.eject(peer_id)  # Send him out

        # Clearing remaining attributes (some of them might be also have already cleared, better be sure)
        if peer_id in self._sponsored_guests:
            del self._sponsored_guests[peer_id]
        if peer_id in self._guest2vote_request:
            del self._guest2vote_request[peer_id]
        if peer_id in self._wants_to_exist:
            self._wants_to_exist.remove(peer_id)

    def on_tick(self):
        connected_hotel_managers = self.get_agents_by_role("hotel_manager")
        connected_guests = self.get_agents_by_role("guest")
        self.floor.print(f"Hotel managers: {len(connected_hotel_managers)} "
                         f"| Guests: {len(self.floor.get_guests())}/{len(connected_guests)}")

    async def guest_joined_room(self, interaction: Interaction | None = None):
        log.error("CALLBACK")
        if interaction is None:
            log.error("FALSE")
            return False

        guest = interaction.target[0]
        self.floor.get_room_of(guest).guest2status[guest] = GuestStatus.JUST_ARRIVED_AT_ROUND_TABLE
        log.error("TRUE")
        return True

    async def guest_joined_voting_booth(self, interaction: Interaction | None = None):
        if interaction is None:
            return False

        guest = interaction.target[0]
        if self.floor.is_in_a_room(guest):
            room = self.floor.get_room_of(guest)
            if room is not None:
                room.guest2status[guest] = GuestStatus.JUST_ARRIVED_IN_VOTING_BOOTH
        return True

    @action
    async def get_guest_sponsor(self, hotel_manager: str | None = None, interaction: Interaction | None = None):
        log.error(hotel_manager)
        log.error(hotel_manager not in self.world_agents)
        log.error(interaction is None)
        if hotel_manager is None or hotel_manager not in self.world_agents or interaction is None:
            log.error("RET FALSE")
            return False

        guest = interaction.requester
        role = self.get_role(guest)
        log.error(f"role = {role}")
        if role == "guest":
            self._sponsored_guests[guest] = hotel_manager  # Check-in order will follow the order in this dict, FIFO
            return True
        else:
            return False

    @action
    async def check_in(self):

        # Getting list of guests to be checked in
        log.error(f"self._sponsored_guests={self._sponsored_guests}")
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

            # Sending to room
            if not await self.send(action_name="goto_room",
                                   from_state="ready_for_room",
                                   target=guest,
                                   callback="guest_joined_room"):
                await self.disconnect(guest)
            else:
                hotel_manager = self._sponsored_guests[guest]
                room = self.floor.get_room(proposed_check_in['room_id'])

                # Remembering this decision
                if self.floor.insert(guest, self.floor.get_profile_of(guest), hotel_manager, room):

                    # Marking the guest as somebody who was asked to go to a room (handled in the joined_room callback)
                    room.guest2status[guest] = GuestStatus.WAITING_TO_JOIN_ROOM

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
                if (room.guest2status[guest] is GuestStatus.AT_ROUND_TABLE and
                        (room.get_time_spent_in_room_by(guest) >= Config.test_duration or guest in self._wants_to_exist)):
                    if not await self.send(action_name="goto_voting_booth",
                                           from_state="room_round_table",
                                           callback="guest_joined_voting_booth",
                                           target=guest):
                        await self.disconnect(guest)
                    something_was_sent = True
                    continue

                # Too much time in voting both: GET OUT OF HERE!
                if (room.guest2status[guest] is GuestStatus.IN_VOTING_BOOTH and
                        ((self.clock.get_time() - self._guest2vote_request[guest][1]) > Config.survey_reply_time)):
                    await self.disconnect(guest)
                    continue

                # This guest just confirmed that he entered the room, let's send him the 'start conversation' message,
                # and let's tell the others that he joined
                if room.guest2status[guest] is GuestStatus.JUST_ARRIVED_AT_ROUND_TABLE:
                    other_guests_names = sorted([room.fake_name_of(_guest)
                                                 for _guest in room.get_guests() if _guest != guest])
                    start_message = (Config.start_message.
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
                    room.guest2status[guest] = GuestStatus.AT_ROUND_TABLE
                    continue

                # From time to time send a reminder
                if int(self.clock.get_time()) % Config.send_reminder_every == 0:
                    for _guest in room.get_guests():
                        if room.guest2status[_guest] is not GuestStatus.AT_ROUND_TABLE:
                            continue
                        if not await self.send(action_name="get_status_msg",
                                               action_kwargs={"msg": format_message(Config.manager_fake_name,
                                                                                    Config.reminder_message)},
                                               from_state="room_round_table",
                                               target=_guest):
                            await self.disconnect(_guest)
                        else:
                            something_was_sent = True

                # This guest just confirmed that he left the room, let's send him the process 'survey' request
                # and let's tell the others that he left
                if room.guest2status[guest] is GuestStatus.JUST_ARRIVED_IN_VOTING_BOOTH:
                    log.error(f"Looking for the fake name of {guest}")
                    log.error(f"Fake names of guests: {room.fake2guest}")
                    fake_name = room.fake_name_of(guest)
                    other_guests_names = sorted([room.fake_name_of(_guest)
                                                 for _guest in room.get_guests() if _guest != guest])
                    survey_msg = (
                        Config.survey_message if len(other_guests_names) > 0 else Config.survey_message_nobody).replace(
                        "<YOUR_NAME>", room.fake_name_of(guest)).replace("<OTHER_NAMES>", ", ".join(other_guests_names))

                    # We send the message to the guest as if it was generated by our processor (even if it is not),
                    # so that the guest will display it on screen (the guest only displays stream-related data, so
                    # sending as bare data_samples with no stream association would keep the message hidden to the GUI)
                    interaction = await self._send(action_name="process",
                                                   from_state="room_voting_booth",
                                                   streams=["chat"],
                                                   target=guest)
                    if interaction is None:
                        await self.disconnect(guest)
                    else:
                        something_was_sent = True
                        log.error(f"@@@@ ADDING to self._guest2vote_request, guest={guest}")
                        self._guest2vote_request[guest] = (interaction.uuid, self.clock.get_time())
                        if not await self.send(action_name="get_msgs",
                                               data_samples={"chat": format_message(Config.manager_fake_name,
                                                                                    survey_msg)},
                                               from_state="room_voting_booth",
                                               id=interaction.id,
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
                        room.guest2status[guest] = GuestStatus.IN_VOTING_BOOTH
                    continue

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
                               if guest not in self._floor_at_last_update.get_room(room.id).get_guests()]
            ejected_guests = [[room.id, guest]
                              for room in self._floor_at_last_update.get_rooms()
                              for guest in room.get_guests()
                              if guest not in self.floor.get_room(room.id).get_guests()]

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
        floor_manager = self.get_peer_id()
        some_votes_were_found = False

        for guest in self.floor.get_guests():
            if guest not in self._guest2vote_request:
                continue
            vote_interaction_uuid, vote_asked_time = self._guest2vote_request[guest]
            guest_processor_stream = self.get_stream("processor", guest, data_type="text")
            vote_msg = guest_processor_stream.get(requested_by="send_votes", uuid=vote_interaction_uuid)
            if vote_msg is None:
                continue

            room = self.floor.get_room_of(guest)
            hotel_manager = self.floor.get_hotel_manager_of(guest)
            fake_name = room.fake_name_of(guest)
            fake_names_seen_so_far = room.get_fake_names_seen_by()

            vote_dict = {
                "voter": room.get_unaid_of(guest),
                "vote": vote_msg,
                "ground_truth": {
                    votee_fake_name: (room.get_ground_truth_of(votee), room.get_unaid_of(votee))
                    for votee_fake_name in fake_names_seen_so_far
                    if votee_fake_name != fake_name
                    if (votee := room.guest_whose_fake_name_is(votee_fake_name)) is not None
                },
                "session_id": self.floor.id + ":" + room.id,
                "floor_manager": floor_manager,
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

            await self.send(data_samples={"votes": json.dumps(vote_dict)},
                            target=hotel_manager)
            del self._guest2vote_request[guest]
            self.floor.eject(guest)
            some_votes_were_found = True
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
            for _fake_name in room.get_fake_names():
                _guest = room.guest_whose_fake_name_is(fake_name)
                if _fake_name != fake_name:

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
