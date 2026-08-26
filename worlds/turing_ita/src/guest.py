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
import io
import csv
import time
import base64
import random
import urllib.request
from .config import Config
from unaiverse.custom import Custom
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction
from unaiverse.networking.node.profile import NodeProfile
from unaiverse.uai import AnswerOutcome, encode_reply
from .utils import normalize_event, strip_service_tag, vote_list_values, vote_near_miss_event, vote_retry_prompt


class WAgent(Agent):
    """Guest of the Turing Test Hotel.

    Contract between the guest and its processor (READ THIS if you are bringing your own processor):
    the guest does NOT build prompts and keeps NO conversation history. It only forwards raw events to the
    processor input stream ("processor_in", text type), and the processor is in charge of collecting the
    history, tracking the roster, and building whatever prompt it wants. In detail:

    - Each processor input sample contains one or more EVENTS, oldest first, separated by
      Config.event_separator (U+001E, the ASCII RECORD SEPARATOR). An event keeps its internal newlines;
      the separator is stripped from every event before batching, so splitting a sample on it is always
      lossless. Multiple events appear only when they arrive faster than the processor consumes them; in
      the common case a sample is just the last message.
    - Chat messages arrive as formatted by the floor manager: "**SENDER:** message text".
    - Service events come from the manager and always start with "**MANAGER:** " (their internal
      "[START_MSG]"/"[GEN_MSG]"/... tag routes them inside the world and is STRIPPED before the push);
      their body may span several lines. The start message opens a new chat session: it is the WORLD
      GUIDE — it explains the game mechanics and carries your fake name and the other guests' names, but
      deliberately NO behavioral instructions, since behavior and persona are each competitor's own
      responsibility — and the processor must RESET its own history when receiving it. The other service
      events tell about roster changes and reminders.
    - The vote request (who was human) is always delivered ALONE, as the only event of the sample of a
      dedicated "process" interaction: beside the framing text it carries a ```uai form (the framework
      hands a model processor the form's instruction in place of the raw block), and the answer to it is
      collected as the vote — the names judged human, comma separated, or a whole-room shortcut (see
      Config.vote_instruction). An empty answer is not a vote: the framework asks a model again, and when
      it insists on silence nothing travels.
    - Every delivered sample triggers one "process" turn. The text returned by the processor is sent to the
      room as the guest's message; returning an EMPTY string means "stay silent on this turn".
    - An anti-flooding COOLDOWN is enforced by the guest itself (Config.msg_cooldown seconds): whatever the
      processor does, at most one message every Config.msg_cooldown seconds reaches the room. Messages
      produced while the cooldown is running are queued (at most Config.max_queued_msgs of them, the oldest
      ones are dropped) and sent, in order, as soon as the cooldown expires.
    - The "[START_MSG]" delivery itself triggers the first turn: the processor is expected to open the
      conversation (proactively, without waiting for other guests' messages) or return an empty string.

    The raw shapes of every event are the *_message templates in src/config.py, and the wire-shape
    invariants a processor can rely on are pinned by test_processor_event_contract in src/utils.py.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Setting system level options
        Custom.MAX_INTERACTIONS = 100
        Custom.MAX_STREAM_DATA_WITHOUT_INTERACTIONS = 10
        self.im.max_interactions = Custom.MAX_INTERACTIONS

        self._pending_events: list[str] = []  # Events not consumed by the processor yet (re-sent as a batch)
        self._ignore_messages: bool = True
        self._init_message_printed: bool = False

        # These variables start with "__" to protect them from the auto-clearing procedure
        self.__hotel_manager: str | None = None  # The peer ID of the selected hotel manager
        self.__prev_hotel_manager: str | None = None
        self.__floor_manager: str | None = None  # The peer ID of the selected floor manager
        self.__queued_msgs: list[str] = []  # Messages waiting for the anti-flooding cooldown to expire
        self.__last_msg_sent_time: float = -1.  # When the last message was sent to the room (-1: never)
        self.__flood_warned: bool = False  # Whether the "too fast" notice was already printed in this burst
        self.__found_in_form_filled_list: bool = False
        self.__form_filled_list_last_check: float = -1.

    async def add_agent(self, peer_id: str, profile: NodeProfile,
                        add_proc_streams: bool = True, add_env_streams: bool = True,
                        add_pubsub_streams: bool = True) -> bool:

        # Ignoring all pubsub streams
        return await super().add_agent(peer_id, profile,
                                       add_proc_streams=add_proc_streams, add_env_streams=add_env_streams,
                                       add_pubsub_streams=False)

    async def on_tick(self):
        assert self.behav is not None

        # Checking if we lost connection to the hotel manager
        if self.__hotel_manager is not None and await self.disconnected(agent=self.__hotel_manager):
            log.user("❌ Ops! Lost connection to the hotel manager!")
            self.__hotel_manager = None  # Clearing
            await self.disconnect_floor_manager()  # Disconnecting floor manager too (will clear too)

            self.reset_status()
            await self.behav.act_ghost_transition(to_state="wait_for_ready")

        # Checking if we lost connection to the floor manager
        elif self.__floor_manager is not None and await self.disconnected(agent=self.__floor_manager):
            log.user("❌ Arg! Lost connection to the floor manager!")
            self.__floor_manager = None
            await self.disconnect_hotel_manager()  # Disconnecting hotel manager (will clear too)

            self.reset_status()
            await self.behav.act_ghost_transition(to_state="wait_for_ready")

        # Checking time spent in current state
        state = self.behav.get_state()
        if ((state is None or state.name != "init") and
                self.behav.get_time_spent_in_current_state() > Config.max_time_in_every_state):
            log.user("❌ Uhm! Too much time passed without interactions, better get out of the hotel")
            await self.disconnect_hotel_manager()  # Disconnecting hotel manager (will clear too)
            await self.disconnect_floor_manager()  # Disconnecting floor manager too (will clear too)

            self.reset_status()
            await self.behav.act_ghost_transition(to_state="wait_for_ready")

        # Sending what is waiting for the anti-flooding cooldown to expire (if anything, and if it expired)
        await self.__flush_queued_msgs()

    def reset_status(self) -> None:
        self._pending_events = []
        self._ignore_messages = True
        self.__queued_msgs = []  # Whatever was waiting for the cooldown will never be sent
        self.__last_msg_sent_time = -1.  # The cooldown is per-conversation: a new chat starts with no cooldown
        self.__flood_warned = False

        # Clearing stdin from pending data
        self.stdin.clear_all_data()

        # De-register all current interactions
        self.im.unregister_all()

    @action
    async def init(self):
        if not self._init_message_printed:
            nickname = self.get_profile().get_static_profile()['nickname']
            is_human = self.get_profile().get_static_profile()["node_type"] == Agent.HUMAN
            if not self.__is_in_form_filled_user_list(nickname, is_human):
                init_message = (Config.init_message.
                                replace("<FORM_LINK>",
                                        base64.b64decode(('=' + Config.form[is_human][1:])[::-1].encode()).decode()).
                                replace("<YOUR_NICKNAME>", nickname))
                log.user(init_message)
                self._init_message_printed = True
        return True

    @action
    async def goto_hall(self):
        return True

    @action
    async def check_confirmation(self):
        nickname = self.get_profile().get_static_profile()['nickname']
        is_human = self.get_profile().get_static_profile()["node_type"] == Agent.HUMAN
        return self.__is_in_form_filled_user_list(nickname, is_human)

    @action
    async def connect_to_hotel_manager(self):

        # Getting the full list of hotel managers in the world
        all_hotel_managers = self.get_agents_by_role("hotel_manager", handshake_completed=False)

        # Putting the previous manager to the bottom of the list (if we disconnected from him there must be a reason...)
        if self.__prev_hotel_manager is not None:
            all_hotel_managers = [hm for hm in all_hotel_managers if hm != self.__prev_hotel_manager]
            all_hotel_managers.append(self.__prev_hotel_manager)

        connected = False
        selected_hotel_manager = None

        # Keep trying all managers!
        while not connected:
            if len(all_hotel_managers) == 0:
                return False

            # Selecting a random hotel manager from the list
            random_index = random.randrange(len(all_hotel_managers))
            selected_hotel_manager = all_hotel_managers[random_index]

            # Connecting to the selected manager
            connected = await self.connect_to(selected_hotel_manager)  # If already connected, it returns False

            # Discarding this manager, in case of failure
            if not connected:
                all_hotel_managers.remove(selected_hotel_manager)

        self.__prev_hotel_manager = self.__hotel_manager
        self.__hotel_manager = selected_hotel_manager
        return True

    @action
    async def hotel_manager_ack(self):
        if self.__hotel_manager is None:
            return False
        return await self.connected(self.__hotel_manager, handshake_completed=True)

    @action
    async def disconnect_hotel_manager(self):
        if self.__hotel_manager is not None:
            await self.disconnect(self.__hotel_manager)
            self.__hotel_manager = None
        return True

    @action
    async def connect_to_floor_manager(self, floor_manager: str | None = None):
        if await self.connect_to(floor_manager):
            self.__floor_manager = floor_manager
            self.reset_status()  # Resetting status to be ready for a new chat
            return True
        else:
            return False

    @action
    async def send_guest_sponsor(self):
        if not await self.send(action_name="get_guest_sponsor",
                               action_kwargs={
                                   "hotel_manager": self.__hotel_manager},
                               from_state="getting_sponsorships",
                               target=self.__floor_manager,
                               volatile=True):
            await self.disconnect_floor_manager()
            return False
        return True

    @action
    async def floor_manager_ack(self):
        if self.__floor_manager is None:
            return False
        return await self.connected(self.__floor_manager, handshake_completed=True)

    @action
    async def disconnect_floor_manager(self):
        if self.__floor_manager is not None:
            await self.disconnect(self.__floor_manager)
            self.__floor_manager = None
        return True

    @action
    async def goto_room(self):
        return True

    @action
    async def goto_voting_booth(self):
        self.stdin.clear_all_data()
        self._pending_events = []  # Whatever the processor did not consume in the room will never be processed
        self.__queued_msgs = []  # Same for what was waiting for the cooldown: we are out of the room now
        self.__flood_warned = False
        return True

    @action
    async def get_status_msg(self, msg: str, process_uuid: str | None = None):
        msg_no_tag = strip_service_tag(msg)

        if msg.startswith("[START_MSG]") or msg.startswith("[START_MSG_NOBODY]"):

            # A new chat session begins: we forward the raw event (the processor resets its own history on
            # it) and we start listening. The push itself triggers the opening "process" turn, so that the
            # processor can proactively open the conversation without waiting for other guests' messages
            self._ignore_messages = False
            self.__push_to_processor(msg_no_tag)

        elif msg.startswith("[VIOLATION_MSG]"):

            # A violation notice must reach whoever is playing even before any room started (the guest is
            # about to be disconnected): there is no turn to take, it is only printed below
            pass

        elif self._ignore_messages:
            return True  # Consume the interaction

        elif msg.startswith("[VOTE_REQ_MSG]"):

            # Vote request: pushed ALONE (its contract promises the only event of its sample, whatever
            # roster noise reached us in the booth), under the UUID communicated by sending this status
            # message, so that the "process" action parked on that UUID fires and the processor answers
            # with its vote. It carries a form, and it arrives here as an action argument rather than as
            # a stream sample, so it is remembered explicitly: a person's typed answer is read against it
            # on the way out
            self.uai_remember_form(self.__floor_manager, msg_no_tag)
            self.__push_to_processor(msg_no_tag, process_uuid=process_uuid, alone=True)

        elif msg.startswith(("[JOINED_MSG]", "[LEFT_MSG]", "[GEN_MSG]", "[DISCO_MSG]")):

            # Roster changes, reminders and disconnections: forwarded raw, the processor decides
            self.__push_to_processor(msg_no_tag)

        else:
            return True  # Consume the interaction (unknown status messages are neither printed nor forwarded)

        # Print every known status message (without the initial [...] tag). Rendering of protocol blocks
        # happens in the logger, per sink: a terminal reads the alt of a block, a sink that declared uai
        # support gets the raw block to render its own way
        log.user(msg_no_tag)
        return True  # Consume the interaction

    @action
    async def get_msgs(self, interaction: Interaction | None = None):
        if interaction is None:
            return False
        if interaction.requester != self.__floor_manager or self._ignore_messages:
            return True  # Consume the interaction

        # Getting messages (one or more) received from the floor managers in the "chat" stream
        # We can use self.stdin since this action is stimulated by an interaction from the floor manager
        msgs_tags_times = self.stdin.get("chat", requested_by="get_msgs", all_uuids=True)

        # The self.stdin.get, with all_uuids set to true, will return a list of tuples (msg, tag, timestamp).
        # It could be empty
        if len(msgs_tags_times) == 0:
            return True  # Consume the interaction

        # Forwarding each received message to our processor, that is in charge of collecting the history
        for msg, tag, timestamp in sorted(msgs_tags_times, key=lambda x: x[2]):
            self.__push_to_processor(msg)

        return True

    @action
    async def send_msg(self):
        if self._ignore_messages:
            return True  # Don't stop the transition

        # Getting my last self-generated message. We can find this message in the self.stdout of this action.
        # This is because such self.stdout is the output of the processor, bind to system UUID since
        # this action will only be triggered by system interactions.
        # This is exactly where our message is already stored due a previous call to a solid "process".
        msgs = self.stdout.get(requested_by="send_msgs", data_type="text")
        if msgs is None or len(msgs) == 0:
            return True  # Don't stop the transition

        # The call above returns a list with data about all the text streams (they might be more than one)
        msg = msgs[0]  # We assume the first one is the right one

        # An empty output means the processor chose to stay silent on this turn
        if msg is None or len(msg.strip()) == 0:
            return True  # Don't stop the transition

        # Anti-flooding cooldown: my message is queued and sent as soon as the cooldown expires (right now,
        # if it already did). Dropping the oldest queued messages, when too many of them piled up: they are
        # the most out-of-date ones with respect to what is being said in the room
        self.__queued_msgs.append(msg)
        cooldown_left = self.__cooldown_left()

        # Telling the guest what is going on, once per burst: the notice is LOCAL (it is printed for
        # whoever is playing, it is never sent to the room, so it cannot give anybody away)
        if len(self.__queued_msgs) >= Config.max_queued_msgs and not self.__flood_warned:
            self.__flood_warned = True
            log.user(f"⚠️ Ho mandato messaggi troppo velocemente, sono in cooldown: posso inviarne uno "
                     f"ogni {Config.msg_cooldown:g} secondi, i prossimi verranno scartati")
        elif cooldown_left > 0. and len(self.__queued_msgs) == 1:
            log.user(f"⏳ Cooldown anti-flooding: il messaggio verrà inviato tra {cooldown_left:.1f} secondi")

        if len(self.__queued_msgs) > Config.max_queued_msgs:
            dropped = len(self.__queued_msgs) - Config.max_queued_msgs
            self.__queued_msgs = self.__queued_msgs[dropped:]
            log.user(f"⏳ Stai scrivendo troppo in fretta: {dropped} messaggio/i in coda è/sono stato/i scartato/i")

        await self.__flush_queued_msgs()
        return True  # Don't stop the transition

    @action
    async def process(self, interaction: Interaction | None = None) -> bool:
        """This is just an override to clear the push buffer when it gets consumed by the processor."""
        ret = await super().process(interaction)
        if ret:
            self._pending_events = []
        return ret

    def uai_postprocess(self, text: str, spec: dict, **kwargs) -> AnswerOutcome:
        """The vote is answered in words as the list of the names judged human (or a whole-room shortcut):
        this is the world's own slot filler, run before the general policy would read the list as something
        else. A list naming somebody unknown goes to the fell-short policy with exactly those tokens, so
        that whoever wrote it is asked again about them. The words that filled the form travel inside the
        block as its raw: the hotel manager stores them as the vote message the voter actually wrote."""
        values, unknown = vote_list_values(spec, text)
        if values is not None:
            self.uai_forget_form(spec)
            return AnswerOutcome(text=encode_reply(spec, values, raw=[text]))
        if unknown:
            return self.uai_answer_fell_short(text, spec, vote_near_miss_event(spec, text, unknown),
                                                   kwargs.get("attempt", 0), kwargs.get("model_view"),
                                                   attempts=[text])
        return super().uai_postprocess(text, spec, **kwargs)

    def uai_answer_fell_short(self, text: str, spec: dict, event, attempt: int,
                                   model_view: str | None = None, attempts: list | None = None) -> AnswerOutcome:
        """Same policy as the framework (who is asked again, how many times, who is told): only the wording
        of the second request to a model is this world's own, since the generic one asks for 'field: value'
        lines and this form is answered with a list of names."""
        outcome = super().uai_answer_fell_short(text, spec, event, attempt, model_view, attempts=attempts)
        if outcome.retry is not None and spec.get("name") == Config.vote_form_name:
            return AnswerOutcome(retry=vote_retry_prompt(spec, text, event, model_view))
        return outcome

    def __cooldown_left(self) -> float:
        """Seconds still to wait before another message can be sent to the room (<= 0 means: send it now)."""
        if Config.msg_cooldown <= 0. or self.__last_msg_sent_time < 0.:
            return 0.
        return Config.msg_cooldown - (time.time() - self.__last_msg_sent_time)

    async def __flush_queued_msgs(self) -> None:
        """Send the oldest message waiting in the anti-flooding queue, if the cooldown expired (async)."""
        if len(self.__queued_msgs) == 0 or self.__floor_manager is None or self._ignore_messages:
            return

        # Still cooling down: the queued messages stay there, a following tick will take care of them
        if self.__cooldown_left() > 0.:
            return

        msg = self.__queued_msgs.pop(0)

        # Limiting message to max size
        if Config.max_message_size > 0:
            if len(msg) > Config.max_message_size:
                msg = msg[:Config.max_message_size]
                log.user(f"✂️ Messaggio troppo lungo: invio solo i primi {Config.max_message_size} caratteri")

        self.__last_msg_sent_time = time.time()
        if len(self.__queued_msgs) == 0:
            self.__flood_warned = False  # Burst over: the notice can be printed again on the next one

        # Sending my clean message to the floor manager
        interaction = await self._send(action_name="get_msg_and_broadcast",
                                       action_kwargs={"msg": msg},
                                       from_state="collect_msgs",
                                       target=self.__floor_manager,
                                       volatile=True)
        if interaction is None:
            await self.disconnect(self.__floor_manager)

    def __push_to_processor(self, msg: str | None,
                            process_uuid: str | None = Custom.SYSTEM_INTERACTION_UUID,
                            alone: bool = False) -> None:
        if msg is None:
            return

        # An event keeps its newlines (a fence is only a fence with them, and nothing else needs
        # flattening); what it cannot contain is the separator the batching below joins events with,
        # which normalize_event strips, so that splitting a sample on it is always lossless
        msg = normalize_event(msg)
        if len(msg) == 0:
            return

        input_stream = self.get_stream("processor_in", data_type="text")
        assert input_stream is not None

        # A sample is normally the whole backlog of unconsumed events; a message pushed "alone" (the
        # vote request, promised as the only event of its sample) bypasses the backlog and is the whole
        # sample by itself
        if alone:
            payload = msg
        else:
            self._pending_events.append(msg)
            payload = Config.event_separator.join(self._pending_events)

        # Setting the event(s) to our processor's default input (given UUID), so that it will be considered
        # in the next "process" action that is bound to the given UUID (for humans this stream is disabled,
        # so this is a no-op: humans read the room through the printed messages)
        input_stream.set(payload, uuid=process_uuid)

    def __is_in_form_filled_user_list(self, nickname: str, is_human: bool) -> bool:
        if (not hasattr(Config, "registered_users_form_sheets") or
                not hasattr(Config, "registered_users_form_column_id")):
            return True

        if self.__found_in_form_filled_list:
            return True

        if (self.clock.get_time() - self.__form_filled_list_last_check) <= 5.0:  # Try every 5s
            return False
        else:
            self.__form_filled_list_last_check = self.clock.get_time() + 2.0  # Assuming it will take 2s to get response

        form_column_id = Config.registered_users_form_column_id
        form_sheets = Config.registered_users_form_sheets

        url = (f"{base64.b64decode(('=' + form_sheets[is_human][1:])[::-1].encode()).decode()}"
               f"/gviz/tq?tqx=out:csv")
        try:
            try:
                from pyodide.http import open_url  # Only exists in Pyodide (guests running in a browser)
            except ImportError:
                open_url = None
            text = None
            if open_url is not None:
                # No sockets in the browser sandbox: urllib CANNOT work there; this is a synchronous
                # XHR through the browser (the Google endpoint sends the needed CORS headers)
                text = open_url(url).read()  # noqa
            else:
                with urllib.request.urlopen(url, timeout=6) as r:
                    text = r.read().decode("utf-8", errors="replace")
            if text is not None:
                for row in csv.reader(io.StringIO(text)):
                    if len(row) > form_column_id:
                        if row[form_column_id].strip().lower() == nickname.strip().lower():
                            self.__found_in_form_filled_list = True
        except Exception as e:
            log.error(f"Could not read the registration-form sheet: {e}")
            return False
        return self.__found_in_form_filled_list
