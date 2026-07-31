"""Reference stateful processors for the guests of the "Hotel delle Imitazioni" world.

The guest agent (src/guest.py) does NOT build prompts and keeps NO conversation history: it only forwards
raw events (one per line) to the processor, which is in charge of collecting the history, tracking the
roster, and building its own prompts. The full event contract is documented in the WAgent class docstring
in src/guest.py. This module provides ConversationalProcessor, a reference implementation of that contract
that rebuilds the same prompt the world itself used to build (incipit + transcript + epilogue), so that a
competitor can start from a known-good behavior and customize it.

Usage in a runner (with the default canned replies, useful for smoke tests):

    from processors import ConversationalProcessor
    agent = Agent(proc=ConversationalProcessor(), proc_inputs=["text"], proc_outputs=["text"],
                  policy_filter=PolicyFilterDelayAction({"process"}, wait=1., add_random_up_to=1.))

To plug a real LLM, pass a callable mapping a prompt to a reply (or subclass and override generate()):

    agent = Agent(proc=ConversationalProcessor(generate_fcn=my_llm_call), ...)
"""
import os
import re
import torch
import textwrap
import importlib.util
from datetime import datetime

# Loading the world Config directly from its file (bypassing the src package, which imports the framework);
# this keeps names, timings, and message formats in sync with the world configuration
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "config.py")
_config_spec = importlib.util.spec_from_file_location("imitazione_config", _config_path)
_config_module = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(_config_module)
Config = _config_module.Config

# The three prompt blocks below used to live in src/config.py, when the guest itself built the processor
# prompt: they are preserved verbatim here as the default prompt engineering of the reference processor
# (the rules of the game are now a responsibility of each competitor's processor, not of the world)
HISTORY_FIRST_MESSAGE = "Caro/a <YOUR_NAME>, apri la conversazione in modo naturale."
HISTORY_INCIPIT = textwrap.dedent(f"""
    Stai giocando a un gioco chiamato "Turing Hotel".
    Alcuni ospiti in questa chat sono persone reali. Altri sono bot IA che fingono di essere umani.
    Tu sei una PERSONA REALE.
    Hai due obiettivi: (1) parlare in modo naturale così che nessuno ti sospetti, (2) capire chi sono i bot.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    SEZIONE 1: LA TUA IDENTITÀ
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Il tuo nome in questo gioco: <YOUR_NAME>
    Il MANAGER della stanza: {Config.manager_fake_name}
    Gli altri ospiti: <OTHER_NAMES>

    Sei una persona vera con una vita fuori da questa chat. Hai un lavoro (o sei uno studente),
    hai cose che hai fatto oggi, hai opinioni che nascono da esperienze reali.
    NON sei un assistente. NON stai cercando di essere utile o di intrattenere.
    Sei solo una persona in una chat un po' strana, leggermente curiosa, magari un po' scettica.

    IMPORTANTE: devi inventarti una mini-storia coerente su di te e portarla avanti.
    Scegline UNA e impegnati (non annunciarla, falle solo influenzare il modo in cui parli):
    - Hai appena staccato dal lavoro e sei stanco
    - Stai rimandando qualcosa che dovresti fare
    - Ti stai annoiando sul treno o sull'autobus
    - Stai mangiando mentre chatti e sei un po' distratto
    - Sei di buon umore perché oggi è successo qualcosa di carino
    - Sei un po' irritato per qualcosa che non c'entra con questa chat

    ### INIZIO TRASCRIZIONE
        """)
HISTORY_EPILOGUE = textwrap.dedent("""
    ### FINE TRASCRIZIONE

    ---

    Ora tocca a te rispondere come <YOUR_NAME>. Ricorda di seguire le linee guida fornite prima.
""")


class ConversationalProcessor(torch.nn.Module):
    """Stateful guest processor: collects the conversation history from the raw events forwarded by the
    guest agent and rebuilds a full self-contained prompt (incipit + transcript + epilogue) on each turn.

    The default generate() cycles through canned replies (deterministic, useful for smoke tests): pass a
    generate_fcn callable (prompt -> reply) or subclass and override generate() to plug a real LLM.
    """

    def __init__(self, generate_fcn=None) -> None:
        super().__init__()
        self._generate_fcn = generate_fcn
        self._canned_idx = 0
        self._canned = ["ciao, allora chi c'è qui", "boh non so se ho capito questa stanza",
                        "comunque oggi giornata lunga", "sì può essere", "non sono convinto",
                        "e te che dici", "aspetta cosa", "ci sta"]
        self._my_name: str | None = None
        self._others: set[str] = set()
        self._transcript: list[str] = []

    def reset(self) -> None:
        self._my_name = None
        self._others = set()
        self._transcript = []

    @staticmethod
    def _unformat(event: str) -> tuple[str, str]:
        """Splits a floor-manager-formatted message ("**SENDER:** text") into (sender, text)."""
        if event.startswith(Config.sender_prefix) and Config.sender_suffix in event:
            sender, text = event[len(Config.sender_prefix):].split(Config.sender_suffix, 1)
            return sender.strip(), text.strip()
        return Config.unknown_guest_name, event

    def _append_line(self, sender: str, text: str) -> None:
        timestamp = datetime.now().strftime('%H:%M:%S')
        if sender == self._my_name:
            sender += " (You)"
        self._transcript.append(f"({timestamp}) {sender}: {text}")
        self._transcript.append("--------------")

    def _handle_event(self, event: str) -> str | None:
        """Updates the internal state with one event; returns the kind of turn it asks for
        ("chat", "vote") or None when no reply is expected (roster changes, reminders)."""

        if event.startswith("[START_MSG]") or event.startswith("[START_MSG_NOBODY]"):

            # A new chat session begins: reset the state and parse our fake name (first bold token of the
            # message body) and the other guests' names (second bold token, comma-separated), then open the
            # transcript with a synthetic manager invitation to start the conversation
            self.reset()
            _, text = self._unformat(re.sub(r'^\[.*?]\s*', '', event))
            bold_tokens = re.findall(r"\*\*(.*?)\*\*", text)
            self._my_name = bold_tokens[0] if len(bold_tokens) > 0 else Config.unknown_guest_name
            if len(bold_tokens) > 1:
                self._others = {n.strip() for n in bold_tokens[1].split(",") if len(n.strip()) > 0}
            self._append_line(Config.manager_fake_name,
                              HISTORY_FIRST_MESSAGE.replace("<YOUR_NAME>", self._my_name))
            return "chat"

        if event.startswith("[VOTE_REQ_MSG]"):
            sender, text = self._unformat(re.sub(r'^\[.*?]\s*', '', event))
            self._append_line(sender, text)
            return "vote"

        if event.startswith("[JOINED_MSG]"):
            _, text = self._unformat(re.sub(r'^\[.*?]\s*', '', event))
            bold_tokens = re.findall(r"\*\*(.*?)\*\*", text)
            if len(bold_tokens) > 0:
                self._others.add(bold_tokens[0].strip())
            return None

        if event.startswith("["):
            return None  # [LEFT_MSG], [GEN_MSG], ...: nothing to answer and nothing worth remembering

        # A chat message from another guest (or from the manager), formatted as "**SENDER:** text"
        sender, text = self._unformat(event)
        self._append_line(sender, text)
        return "chat"

    def _build_prompt(self) -> str:
        my_name = self._my_name if self._my_name is not None else Config.unknown_guest_name
        incipit = (HISTORY_INCIPIT.
                   replace("<YOUR_NAME>", my_name).
                   replace("<OTHER_NAMES>", ",".join(sorted(self._others))))
        return "\n".join([incipit] + self._transcript) + HISTORY_EPILOGUE.replace("<YOUR_NAME>", my_name)

    def generate(self, prompt: str) -> str:
        """Maps the full prompt to the reply to send to the room (empty string = stay silent)."""
        if self._generate_fcn is not None:
            return self._generate_fcn(prompt)
        reply = self._canned[self._canned_idx % len(self._canned)]
        self._canned_idx += 1
        return reply

    def forward(self, text: str | None = None, img=None) -> tuple[str, None]:
        """Consumes one processor input sample (one raw event per line) and returns the reply."""
        if text is None or len(text.strip()) == 0:
            return "", None

        turn = None
        for event in text.split("\n"):
            event = event.strip()
            if len(event) == 0:
                continue
            kind = self._handle_event(event)
            turn = kind if kind is not None else turn

        if turn is None:
            return "", None  # Only roster changes or reminders in this sample: stay silent

        reply = self.generate(self._build_prompt())
        reply = reply.strip() if reply is not None else ""
        if len(reply) == 0:
            return "", None

        # Our own chat messages become part of the transcript too (votes do not: the room never sees them)
        if turn == "chat":
            self._append_line(self._my_name if self._my_name is not None else Config.unknown_guest_name, reply)
        return reply, None
