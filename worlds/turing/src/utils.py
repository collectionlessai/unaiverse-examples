import re
import random
import atexit
from rich import box

from unaiverse.utils.logger import log
from .config import Config
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.console import Group
from unaiverse.networking.node.profile import NodeProfile


def parse_vote_msg(_msg: str) -> dict[str, str]:
    """
    Parse a free-text message to extract classifications (human or artificial/AI).

    Handles sloppy input: mixed case, typos, varied phrasing, punctuation noise,
    and agent names like A, B, ..., Z, A2, B2, ..., A3, etc.

    Returns:
        Dict mapping normalised agent names (e.g. "A", "B2") to "human" or "ai".
    """
    results: dict[str, str] = {}

    # Normalise whitespace for matching (keep original for nothing)
    text = _msg.strip()

    # Agent name pattern
    # Matches: A, b, Z, A2, b12, etc.  Captures (letter, optional digit suffix)
    agent = r'[A-Za-z](?:\d+)?'

    # Build a group version for reuse
    ag = f'({agent})'

    # Keyword banks
    human_kw = (
        r'(?:human|real\s*(?:person|human)?|person|actual\s*(?:person|human)'
        r'|not\s*(?:an?\s*)?(?:ai|bot|robot|artificial|machine)'
        r'|flesh\s*and\s*blood|natural)'
    )
    ai_kw = (
        r'(?:ai|a\.i\.?|artificial(?:\s*intelligence)?|bot|robot|machine'
        r'|not\s*(?:a\s*)?(?:human|real|person|natural)'
        r'|computer|automated|virtual\s*(?:agent|assistant)?|chatbot|llm)'
    )

    # Connectors & fillers between agent and keyword
    glue = r'[\s,:\-]*(?:is|was|seems?\s*(?:like)?|looks?\s*like|felt\s*like|appeared?' \
           r'|sounds?\s*like|must\s*(?:be|have\s*been)|has\s*to\s*be' \
           r'|could\s*(?:be|have\s*been)|might\s*(?:be|have\s*been)' \
           r'|is\s*(?:definitely|probably|surely|clearly|obviously|certainly)' \
           r'|was\s*(?:definitely|probably|surely|clearly|obviously|certainly)' \
           r'|turned\s*out\s*(?:to\s*be)?)' \
           r'[\s,:\-]*(?:an?\s*|the\s*)?'

    # Pattern 1: "<Agent> is/was/seems ... <keyword>"
    p_agent_then_class = re.compile(
        rf'\b{ag}{glue}({human_kw}|{ai_kw})\b', re.IGNORECASE
    )

    # Pattern 2: "<keyword> ... <Agent>" (e.g. "the human was B")
    reverse_glue = r'[\s,:\-]*(?:(?:one|agent|was|is)\s*)*'
    p_class_then_agent = re.compile(
        rf'\b({human_kw}|{ai_kw}){reverse_glue}{ag}\b', re.IGNORECASE
    )

    # Pattern 3: List style  "A, B and C are human"
    agent_list = rf'({agent}(?:\s*[,;&/]\s*{agent})*\s*(?:and|&)\s*{agent}|{agent}(?:\s*[,;&/]\s*{agent})+)'
    list_glue = r'\s*(?:are|were|all\s*(?:are|were)?|seem|seemed)' \
                r'[\s,:\-]*(?:all\s*)?(?:(?:definitely|probably|clearly|obviously)\s*)?(?:an?\s*|the\s*)?'
    p_list = re.compile(
        rf'\b({agent_list}){list_glue}({human_kw}|{ai_kw})\b', re.IGNORECASE
    )

    def classify(_keyword: str) -> str:
        """Decide whether a matched keyword means human or ai."""
        kw = _keyword.lower().strip()
        # "not human" → ai, "not ai" → human
        if re.match(r'not\s+', kw):
            return 'human' if re.search(r'ai|bot|robot|artificial|machine', kw) else 'ai'
        if re.search(r'human|real|person|flesh|natural', kw):
            return 'human'
        return 'ai'

    def normalize_agent(name: str) -> str:
        return name.upper().strip()

    # Apply list pattern first (higher structure)
    for m in p_list.finditer(text):
        agents_str = m.group(1)
        keyword = m.group(3)
        label = classify(keyword)
        found = re.findall(rf'\b({agent})\b', agents_str, re.IGNORECASE)
        for a in found:
            # Filter out stray words that look like single letters (e.g. "and" → "a")
            if len(a) == 1 and a.lower() in ('i',):
                continue
            results[normalize_agent(a)] = label

    # Apply agent-then-class
    for m in p_agent_then_class.finditer(text):
        a, keyword = m.group(1), m.group(2)
        if len(a) == 1 and a.lower() in ('i', 'a'):
            # skip pronoun "I" and article "a" unless followed by digit
            continue
        results.setdefault(normalize_agent(a), classify(keyword))

    # Apply class-then-agent
    for m in p_class_then_agent.finditer(text):
        keyword, a = m.group(1), m.group(2)
        if len(a) == 1 and a.lower() in ('i',):
            continue
        results.setdefault(normalize_agent(a), classify(keyword))

    return results


def compute_check_in_proposals(structure, guests_to_check_in: list):
    # Clearing temp room assignments (if any)
    for room in structure.get_rooms():
        room.clear_temp_assignments()

    # Data that will be returned
    proposed_check_ins = {}  # Checked in guests (peer ID to dictionary {"floor_id": FLOOR_ID, "room_id": ROOM_ID})
    cannot_check_in = []  # Guests for which check in was not possible (no free rooms for them)

    # Shuffling guests waiting in the hall
    guests_to_check_in = random.sample(guests_to_check_in, len(guests_to_check_in))

    # Init counters and conditioning variables
    g = 0
    sc = 0
    so = 0
    critical_rooms = []
    ordinary_rooms = []
    randomize_rooms_considering_updated_counts = True

    # Consider guests one by one
    while g < len(guests_to_check_in):

        # We shuffle and re-count room occupation at the beginning and whenever we looped over all the rooms
        if randomize_rooms_considering_updated_counts:

            # Shuffling rooms (all of them, despite being full or empty or whatever)
            rooms = random.sample(list(structure.get_rooms()), len(structure.rooms))

            # Filtering: rooms with only 1 guest (critical rooms)
            critical_rooms = [r for r in rooms
                              if r.count_guests(count_temp_too=True) == 1]

            # Filtering: rooms with that can still accept guests (ordinary rooms)
            ordinary_rooms = [r for r in rooms
                              if (1 < r.count_guests(count_temp_too=True) < Config.max_guests_per_room)]

            # Ops, no free spots in rooms with somebody already there: go overbooking!
            # (of course, there are no critical rooms in this case)
            if len(critical_rooms) + len(ordinary_rooms) == 0:
                ordinary_rooms = [r for r in rooms
                                  if (1 < r.count_guests(count_temp_too=True) < (Config.max_guests_per_room +
                                                                                 Config.max_overbooked_guests))]

            # Ops (x2), overbooking did not help! Let's consider empty rooms, one by one
            if len(critical_rooms) + len(ordinary_rooms) == 0:
                empty_rooms = [r for r in rooms
                               if r.count_guests(count_temp_too=True) == 0]
                if len(empty_rooms) > 0:
                    ordinary_rooms = [empty_rooms[0]]  # We only take the first one, so we will fill it before switching

            # Ops (x3), no ways, no spots left at all, ...
            if len(critical_rooms) + len(ordinary_rooms) == 0:
                cannot_check_in = guests_to_check_in[g:]
                return proposed_check_ins, cannot_check_in

            # Blocking re-counts
            randomize_rooms_considering_updated_counts = False

        # Getting guest
        guest = guests_to_check_in[g]

        # First: try to send the guest to one of the critical rooms
        if sc < len(critical_rooms):
            room = critical_rooms[sc]
            if hasattr(structure, "get_floor_of_room"):
                floor = structure.get_floor_of_room(room.id)
            else:
                floor = structure
            sc += 1

            # If the floor is valid, we assign the guest to it
            proposed_check_ins[guest] = {"floor_id": floor.id, "room_id": room.id}
            room.add_temp_assignment(guest)

        # Second: we try to send the guest somewhere else, using a general criterion
        if guest not in proposed_check_ins and so < len(ordinary_rooms):
            room = ordinary_rooms[so]
            if hasattr(structure, "get_floor_of_room"):
                floor = structure.get_floor_of_room(room.id)
            else:
                floor = structure
            so += 1

            # If the floor is valid, we assign the guest to it
            proposed_check_ins[guest] = {"floor_id": floor.id, "room_id": room.id}
            room.add_temp_assignment(guest)

        # Third: if we went over all the rooms, we recount their occupation (considering also temp assignments
        # we did so far) and we will go over them again
        if so >= len(ordinary_rooms):
            sc = 0  # Reset
            so = 0  # Reset
            randomize_rooms_considering_updated_counts = True

        # If the current guest was checked-in, we move to the next one, otherwise we will reconsider the guest
        if guest in proposed_check_ins:
            g += 1

    return proposed_check_ins, cannot_check_in


def build_unaid(profile: NodeProfile):
    return profile.get_static_profile()['email'] + '/' + profile.get_static_profile()['node_name']


def format_message(sender_name: str, msg: str):
    tag = ""
    if msg.startswith("["):
        p = msg.find("]", 1)
        if p > 0 and len(msg) >= p + 2:
            tag = msg[0:(p + 2)]
            msg = msg[p + 2:]
    return tag + Config.sender_prefix + sender_name + Config.sender_suffix + msg


def unformat_message(msg: str) -> list[str]:
    return msg[len(Config.sender_prefix):].split(Config.sender_suffix, 1)


def print_live(structure, status_msg: str):
    if not hasattr(structure, "live"):
        return
    is_hotel = hasattr(structure, "floor_manager2floor")

    # Create a table
    table = Table(
        title=f"\n🏨 [bold]Turing Hotel: {'Whole Hotel' if is_hotel else 'Single Floor'} Status[/bold]",
        box=box.HEAVY_EDGE,
        show_lines=False  # We will draw our own floor separators
    )

    table.add_column("Floor", style="cyan", justify="center")
    table.add_column("Room", style="magenta")
    table.add_column("Occupancy", justify="center")
    table.add_column("Overbooked", justify="center")
    if not is_hotel:
        table.add_column("Guests (Name | Status~Timer | Type)")
    else:
        table.add_column("Guests (Name | Timer | Type)")

    floors = structure.get_floors() if is_hotel else [structure]
    for i, floor in enumerate(floors):
        for j, room in enumerate(floor.get_rooms()):
            num_guests = room.count_guests()
            is_overbooked = num_guests > Config.max_guests_per_room

            # Format the guest list as a vertical stack within the cell
            guest_info = []
            for g in room.guests:
                profile = structure.get_profile_of(g)
                if profile is None:
                    name = g
                    label = "?"
                    color = "red"
                else:
                    name = build_unaid(profile)
                    label = "H" if g in room.human_guests else "A"
                    color = "green" if g in room.human_guests else "yellow"
                time_in_room = room.get_time_in_current_status(g)
                status = (room.guest2status[g].value + "~") if g in room.guest2status else ""
                guest_info.append(f"• {name} | [bold]{status}{time_in_room}[/bold] | [{color}]{label}[/]")

            # Use only first room of the floor to show floor name for clarity
            floor_display = (floor.id[0:5] + "...") if j == 0 else ""

            table.add_row(
                floor_display,
                (room.id[0:5] + "..."),
                f"{num_guests}/{Config.max_guests_per_room}",
                "[red]YES[/red]" if is_overbooked else "[green]NO[/green]",
                "\n".join(guest_info)
            )

        # Add a horizontal line after each floor except the last one
        if i < len(floors) - 1:
            table.add_section()

    # Group table and message together
    screen = Group(table, Text(text=f"\n{status_msg}", style="blue"))

    # Rendering
    if structure.live is None:
        structure.live = Live(screen, screen=False, auto_refresh=False)  # Lazy init
        structure.live.start()
        atexit.register(structure.live.stop)
    else:
        structure.live.update(screen, refresh=True)  # Update
