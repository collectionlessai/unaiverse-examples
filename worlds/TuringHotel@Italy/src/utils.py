import re
import random
import atexit
import sys

from rich import box
from .config import Config
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.console import Group
from unaiverse.utils.misc import build_unaid


def parse_vote_msg(
    _msg: str,
    agents: list[str],
    bots: list[str] | None = None,
    humans: list[str] | None = None,
) -> dict[str, str]:
    """
    Parse a free-text message to extract classifications (human or artificial/AI).

    Handles sloppy input: mixed case, typos, varied phrasing, punctuation noise,
    and agent names from the provided list.

    Args:
        _msg:    Free-text vote message.
        agents:  List of valid agent names (e.g. ["Ada", "Ben", "Cal", ...]).
        bots:    Known bot agent names (ground truth).
        humans:  Known human agent names (ground truth).

    Returns:
        Dict mapping canonical agent names to "human" or "ai".
    """
    results: dict[str, str] = {}

    # Build normalization map and regex from the agent list
    agent_norm: dict[str, str] = {n.lower(): n for n in agents}
    agent_re = '(?:' + '|'.join(re.escape(n) for n in agents) + ')'

    def norm(_name: str) -> str:
        """Normalize a matched agent name to its canonical form."""
        return agent_norm[_name.lower()]

    # Full roster of known agents (normalized)
    all_agents: set[str] = set()
    if bots:
        all_agents |= {norm(b) for b in bots}
    if humans:
        all_agents |= {norm(h) for h in humans}

    text = _msg.strip()

    # --- "nobody / none" shortcut ----------------------------------
    if all_agents:
        nobody_pat = re.compile(
            r'^\s*$'
            r'|^(?:nobody|no\s*one|none(?:\s+of\s+them)?'
            r'|they\s*(?:are|\'re)\s+all\s+(?:bots?|ai|robots?|machines?|artificial)'
            r'|all\s+(?:bots?|ai|robots?|machines?|artificial)'
            r'|not\s+any(?:\s*(?:one|body))?'
            r'|nope|nah|zero|nessuno|niente)\s*$',
            re.IGNORECASE,
        )
        if nobody_pat.match(text):
            return {a: 'ai' for a in sorted(all_agents)}

        everybody_pat = re.compile(
            r'^\s*(?:all(?:\s+(?:humans?|real|of\s+them|people|persons?))?'
            r'|they\s*(?:are|\'re)\s+all\s+(?:humans?|real|people|persons?)'
            r'|(?:humans?|people|persons?)(?:\s+only)?'
            r'|every\s*(?:one|body)'
            r'|each\s+(?:one|of\s+them)'
            r'|tutti)\s*$',
            re.IGNORECASE,
        )
        if everybody_pat.match(text):
            return {a: 'human' for a in sorted(all_agents)}

    # Keyword banks
    human_kw = (
        r'(?:humans?|real\s*(?:persons?|humans?)?|persons?|people|actual\s*(?:persons?|humans?)'
        r'|not\s*(?:an?\s*)?(?:ai|bots?|robots?|artificial|machines?)'
        r'|flesh\s*and\s*blood|natural)'
    )
    ai_kw = (
        r'(?:ai|a\.i\.?|artificial(?:\s*intelligence)?|bots?|robots?|machines?'
        r'|not\s*(?:a\s*)?(?:humans?|real|persons?|natural)'
        r'|computers?|automated|virtual\s*(?:agents?|assistants?)?|chatbots?|llms?)'
    )

    # Connectors & fillers between agent and keyword
    ag = f'({agent_re})'
    glue = r'[\s,:\-]+(?:(?:is|was|seems?\s*(?:like)?|looks?\s*like|felt\s*like|appeared?' \
           r'|sounds?\s*like|must\s*(?:be|have\s*been)|has\s*to\s*be' \
           r'|could\s*(?:be|have\s*been)|might\s*(?:be|have\s*been)' \
           r'|is\s*(?:definitely|probably|surely|clearly|obviously|certainly)' \
           r'|was\s*(?:definitely|probably|surely|clearly|obviously|certainly)' \
           r'|turned\s*out\s*(?:to\s*be)?)' \
           r'[\s,:\-]*(?:an?\s*|the\s*)?)?'

    # Pattern 1: "<Agent> is/was/seems ... <keyword>"
    p_agent_then_class = re.compile(
        rf'\b{ag}{glue}({human_kw}|{ai_kw})\b', re.IGNORECASE
    )

    # Pattern 2: "<keyword> ... <Agent>" (e.g. "the human was Ben")
    reverse_glue = r'[\s:\-]*(?:(?:one|agent|was|is)\s*)*'
    p_class_then_agent = re.compile(
        rf'\b({human_kw}|{ai_kw}){reverse_glue}\b{ag}\b', re.IGNORECASE
    )

    # Pattern 3: List style  "Ada, Ben and Cal are human"
    agent_b = r'\b' + agent_re + r'\b'
    agent_sep = r'(?:\s*[,;&/\-]\s*(?:and|&)?\s*|\s+(?:and|&)\s+|\s+)'
    agent_list = rf'({agent_b}(?:{agent_sep}{agent_b})+)'
    list_glue = r'[\s,:\-]+(?:(?:is|are|was|were|all\s*(?:are|were)?|seem|seemed' \
                r'|looks?\s*like|looked?\s*like)' \
                r'[\s,:\-]*(?:all\s*)?(?:(?:definitely|probably|clearly|obviously)\s*)?(?:an?\s*|the\s*)?)?'
    p_list = re.compile(
        rf'\b({agent_list}){list_glue}({human_kw}|{ai_kw})\b', re.IGNORECASE
    )

    def classify(_keyword: str) -> str:
        _kw = _keyword.lower().strip()
        if re.match(r'not\s+', _kw):
            return 'human' if re.search(r'ai|bot|robot|artificial|machine', _kw) else 'ai'
        if re.search(r'human|real|person|flesh|natural', _kw):
            return 'human'
        return 'ai'

    # --- Apply patterns ---

    # Pattern 1
    for m in p_agent_then_class.finditer(text):
        name = norm(m.group(1))
        results[name] = classify(m.group(2))

    # Pattern 2
    for m in p_class_then_agent.finditer(text):
        name = norm(m.group(2))
        if name not in results:
            results[name] = classify(m.group(1))

    # Pattern 3
    for m in p_list.finditer(text):
        raw_list = m.group(1)
        kw = m.group(3)
        found = re.findall(r'\b' + agent_re + r'\b', raw_list, re.IGNORECASE)
        label = classify(kw)
        for a in found:
            n = norm(a)
            if n not in results:
                results[n] = label

    # Pattern 4: Answer-framing — "my guess is Ben, Cal" → human
    frame = (r'(?:(?:my|I)\s+)?(?:guess|vote|answer|pick|choice|bet)'
             r'\s+(?:is|would\s+be|goes?\s+to|for)\s+')
    p_frame = re.compile(
        rf'\b{frame}({agent_b}(?:{agent_sep}{agent_b})*)', re.IGNORECASE
    )
    for m in p_frame.finditer(text):
        found = re.findall(r'\b' + agent_re + r'\b', m.group(1), re.IGNORECASE)
        for a in found:
            n = norm(a)
            if n not in results:
                results[n] = 'human'

    # Pattern 5: Bare agent names with no keywords → default to "human"
    if not results:
        tokens = re.findall(r'\b' + agent_re + r'\b', text, re.IGNORECASE)
        if tokens:
            for t in tokens:
                results[norm(t)] = 'human'

    # Pattern 6: Positional keywords — "bot, bot" or "human, bot, human"
    # When no agent names appear in the text, map keywords to agents by position
    if not results and len(all_agents) > 0:
        if not re.search(r'\b' + agent_re + r'\b', text, re.IGNORECASE):
            kw_pat = re.compile(rf'({human_kw}|{ai_kw})', re.IGNORECASE)
            matches = list(kw_pat.finditer(text))
            if matches:
                # Verify text is ONLY keywords + separators (no stray words)
                stripped = kw_pat.sub('', text)
                if re.fullmatch(r'[\s,;&/\-]*(?:(?:and|&)[\s,;&/\-]*)*', stripped, re.IGNORECASE):
                    if len(matches) == len(all_agents):
                        for i, m in enumerate(matches):
                            results[norm(agents[i])] = classify(m.group(1))

    return results


def test_parse_vote_msg_names():
    agents = [
        "Ada", "Ben", "Cal", "Dax", "Eli", "Fin", "Gus", "Hal", "Ivy", "Jai",
        "Kit", "Leo", "Mae", "Nia", "Oli", "Pia", "Rio", "Sid", "Tai", "Uma",
        "Vic", "Wes", "Yun", "Zed", "Bex", "Lio", "Nox", "Rye", "Tov", "Zia",
    ]

    def pv(_msg, **kwargs):
        return parse_vote_msg(_msg, agents=agents, **kwargs)

    tests = [
        # --- Basic keyword patterns ---
        ("Ben bot", {"Ben": "ai"}),
        ("Ben is a bot", {"Ben": "ai"}),
        ("ben human", {"Ben": "human"}),
        ("Ada is human", {"Ada": "human"}),
        ("Ada was definitely a robot", {"Ada": "ai"}),
        ("the human was Ben", {"Ben": "human"}),
        ("Ada, Ben and Cal are human", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Eli is ai, Fin bot", {"Eli": "ai", "Fin": "ai"}),
        ("Ada is not a bot", {"Ada": "human"}),
        ("Ben is not human", {"Ben": "ai"}),
        ("Ada human, Ben bot", {"Ada": "human", "Ben": "ai"}),
        ("Ben and Ada are bots", {"Ben": "ai", "Ada": "ai"}),
        ("Ben and Ada is a bot", {"Ben": "ai", "Ada": "ai"}),
        ("Ada, Ben and Cal are humans", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Ada and Ben were robots", {"Ada": "ai", "Ben": "ai"}),
        # --- Bare agent names default to human ---
        ("Ada", {"Ada": "human"}),
        ("Ada, Ben, Cal", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Ada Ben", {"Ada": "human", "Ben": "human"}),
        ("ada ben cal", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        # --- Mixed separators in lists ---
        ("I think Ada, Ben, Cal are human",
         {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("I think Ada and Ben, Cal are human",
         {"Ada": "human", "Ben": "human", "Cal": "human"}),
        # --- Unrecognised keyword ignored ---
        ("Ada human, Ben bot, Cal dunno", {"Ada": "human", "Ben": "ai"}),
        # --- "look like" in list context ---
        ("Ada human, Ben and Cal look like bots",
         {"Ada": "human", "Ben": "ai", "Cal": "ai"}),
        # --- Space-separated list with keyword ---
        ("Ada Ben cal dax Eli are bots",
         {"Ada": "ai", "Ben": "ai", "Cal": "ai", "Dax": "ai", "Eli": "ai"}),
        ("Ada,Ben,Cal bots", {"Ada": "ai", "Ben": "ai", "Cal": "ai"}),
        ("Ada, Ben, Cal human", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Ada, and Ben, and Cal human",
         {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Ada-Ben-Cal human", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Ada;Ben;Cal human", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Ada; Ben, Cal human", {"Ada": "human", "Ben": "human", "Cal": "human"}),
        ("Ada, Ben bots, Cal human", {"Ada": "ai", "Ben": "ai", "Cal": "human"}),
        # --- Complex multi-clause ---
        ("I was thinking that Ada and Zed are the humans. I think Cal is artificial",
         {"Ada": "human", "Zed": "human", "Cal": "ai"}),
        ("I was thinking that ada and zed are the humans. I think cal is artificial",
         {"Ada": "human", "Zed": "human", "Cal": "ai"}),
        ("Nice test! My guess is Ben, Cal. Pretty sure Dax-Eli are not humans",
         {"Ben": "human", "Cal": "human", "Dax": "ai", "Eli": "ai"}),
        # --- Nonsense / refusals → empty (no roster) ---
        ("I don't know", {}),
        ("Who knows", {}),
        ("cannot say", {}),
        ("sorry", {}),
        ("no votes", {}),
        ("fuck off", {}),
        # --- Case insensitivity ---
        ("ADA is human", {"Ada": "human"}),
        ("ada BOT", {"Ada": "ai"}),
        ("BEN and CAL are bots", {"Ben": "ai", "Cal": "ai"}),
        # --- Agent names that could be English words ---
        ("i'd say Sid bot", {"Sid": "ai"}),
        ("It's Mae", {"Mae": "human"}),
        ("Ivy is human", {"Ivy": "human"}),
        ("Rye bot", {"Rye": "ai"}),
    ]

    roster = {"bots": ["Ada"], "humans": ["Ben", "Cal"]}
    all_ai = {"Ada": "ai", "Ben": "ai", "Cal": "ai"}
    all_human = {"Ada": "human", "Ben": "human", "Cal": "human"}

    roster_tests = [
        # --- "nobody" / "none" with roster → all ai ---
        ("nobody", all_ai, roster),
        ("Nobody", all_ai, roster),
        ("no one", all_ai, roster),
        ("none", all_ai, roster),
        ("None of them", all_ai, roster),
        ("nope", all_ai, roster),
        ("nah", all_ai, roster),
        ("zero", all_ai, roster),
        ("all bots", all_ai, roster),
        ("all ai", all_ai, roster),
        ("they're all bots", all_ai, roster),
        ("they are all ai", all_ai, roster),
        ("not anyone", all_ai, roster),
        ("not anybody", all_ai, roster),
        ("nessuno", all_ai, roster),
        ("", all_ai, roster),
        ("  ", all_ai, roster),
        # --- "all humans" / "everyone" with roster → all human ---
        ("all", all_human, roster),
        ("all humans", all_human, roster),
        ("all human", all_human, roster),
        ("all real", all_human, roster),
        ("all of them", all_human, roster),
        ("all people", all_human, roster),
        ("humans", all_human, roster),
        ("human", all_human, roster),
        ("humans only", all_human, roster),
        ("human only", all_human, roster),
        ("people", all_human, roster),
        ("everyone", all_human, roster),
        ("everybody", all_human, roster),
        ("each one", all_human, roster),
        ("each of them", all_human, roster),
        ("they are all humans", all_human, roster),
        ("they're all humans", all_human, roster),
        ("they're all real", all_human, roster),
        ("tutti", all_human, roster),
        # --- "nobody" / "everyone" without roster → empty ---
        ("nobody", {}, None),
        ("none", {}, None),
        ("", {}, None),
        ("all", {}, None),
        ("humans", {}, None),
        ("everyone", {}, None),
        # --- Normal votes still work with roster ---
        ("Ada", {"Ada": "human"}, roster),
        ("Ben bot", {"Ben": "ai"}, roster),
        ("Ada human, Ben bot", {"Ada": "human", "Ben": "ai"}, roster),
        ("Ada, Ben, Cal", {"Ada": "human", "Ben": "human", "Cal": "human"}, roster),
        # --- Positional keywords (no agent names, map by order) ---
        ("Bot", {"Ada": "ai"}, {"bots": [], "humans": ["Ada"]}),
        ("bot", {"Ada": "ai"}, {"bots": [], "humans": ["Ada"]}),
        ("Bot, Bot", {"Ada": "ai", "Ben": "ai"}, {"bots": [], "humans": ["Ada", "Ben"]}),
        ("human, bot", {"Ada": "human", "Ben": "ai"}, {"bots": ["Ben"], "humans": ["Ada"]}),
        ("bot, human, bot", {"Ada": "ai", "Ben": "human", "Cal": "ai"},
         {"bots": ["Ada", "Cal"], "humans": ["Ben"]}),
        ("human", {"Ada": "human"}, {"bots": [], "humans": ["Ada"]}),
        ("human, human, human", {"Ada": "human", "Ben": "human", "Cal": "human"},
         {"bots": [], "humans": ["Ada", "Ben", "Cal"]}),
        ("robot, ai, human", {"Ada": "ai", "Ben": "ai", "Cal": "human"},
         {"bots": ["Ada", "Ben"], "humans": ["Cal"]}),
        ("not human, human", {"Ada": "ai", "Ben": "human"},
         {"bots": ["Ada"], "humans": ["Ben"]}),
        ("not a bot, bot", {"Ada": "human", "Ben": "ai"},
         {"bots": ["Ben"], "humans": ["Ada"]}),
    ]

    passed = 0
    total = 0

    for msg, expected in tests:
        total += 1
        result = pv(msg)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            print(f"  {status}: {msg!r}\n    expected {expected}\n    got      {result}")
        else:
            print(f"  {status}: {msg!r} -> {result}")
            passed += 1

    for msg, expected, r in roster_tests:
        total += 1
        if r is not None:
            result = pv(msg, bots=r["bots"], humans=r["humans"])
        else:
            result = pv(msg)
        status = "PASS" if result == expected else "FAIL"
        roster_label = " [roster]" if r else " [no roster]"
        if status == "FAIL":
            print(f"  {status}: {msg!r}{roster_label}\n    expected {expected}\n    got      {result}")
        else:
            print(f"  {status}: {msg!r}{roster_label} -> {result}")
            passed += 1

    print(f"\n{passed}/{total} passed")


def test_parse_vote_msg_letters():
    agents = ["A", "B", "C", "D", "E", "F", "G"]

    def pv(_msg, **kwargs):
        return parse_vote_msg(_msg, agents=agents, **kwargs)

    tests = [
        # --- Basic keyword patterns ---
        ("B bot", {"B": "ai"}),
        ("B is a bot", {"B": "ai"}),
        ("b human", {"B": "human"}),
        ("A is human", {"A": "human"}),
        ("A was definitely a robot", {"A": "ai"}),
        ("the human was B", {"B": "human"}),
        ("A, B and C are human", {"A": "human", "B": "human", "C": "human"}),
        ("A2 is ai, B2 bot", {"A2": "ai", "B2": "ai"}),
        ("A is not a bot", {"A": "human"}),
        ("B is not human", {"B": "ai"}),
        ("A human, B bot", {"A": "human", "B": "ai"}),
        ("B and A are bots", {"B": "ai", "A": "ai"}),
        ("B and A is a bot", {"B": "ai", "A": "ai"}),
        ("A, B and C are humans", {"A": "human", "B": "human", "C": "human"}),
        ("A and B were robots", {"A": "ai", "B": "ai"}),
        # --- Bare agent names default to human ---
        ("A", {"A": "human"}),
        ("A, B, C", {"A": "human", "B": "human", "C": "human"}),
        ("A B", {"A": "human", "B": "human"}),
        ("a b c", {"A": "human", "B": "human", "C": "human"}),
        # --- Mixed separators in lists ---
        ("I think A, B, C are human", {"A": "human", "B": "human", "C": "human"}),
        ("I think A and B, C are human", {"A": "human", "B": "human", "C": "human"}),
        # --- Unrecognised keyword ignored ---
        ("A human, B bot, C dunno", {"A": "human", "B": "ai"}),
        # --- "look like" in list context ---
        ("A human, B and C look like bots", {"A": "human", "B": "ai", "C": "ai"}),
        # --- Space-separated list with keyword ---
        ("A B c d E are bots", {"A": "ai", "B": "ai", "C": "ai", "D": "ai", "E": "ai"}),
        ("A,B,C bots", {"A": "ai", "B": "ai", "C": "ai"}),
        ("A, B, C human", {"A": "human", "B": "human", "C": "human"}),
        ("A, and B, and C human", {"A": "human", "B": "human", "C": "human"}),
        ("A, and B, an C", {"A": "human", "B": "human", "C": "human"}),
        ("A-B-C human", {"A": "human", "B": "human", "C": "human"}),
        ("A;B;C human", {"A": "human", "B": "human", "C": "human"}),
        ("A; B, C human", {"A": "human", "B": "human", "C": "human"}),
        ("A, B bots, C human", {"A": "ai", "B": "ai", "C": "human"}),
        # --- Complex multi-clause ---
        ("I wat thinking that A and z are the humans. I think C is artificial",
         {"A": "human", "Z": "human", "C": "ai"}),
        ("Nice test! Thanks for this. My guess is B, C. Pretty sure D-E are not humans",
         {"B": "human", "C": "human", "D": "ai", "E": "ai"}),
        # --- Nonsense / refusals → empty (no roster) ---
        ("I don't know", {}),
        ("Who knows", {}),
        ("cannot say", {}),
        ("sorry", {}),
        ("no votes", {}),
        ("fuck off", {}),
        # --- Single-letter agents that overlap with contraction fragments ---
        ("It's T", {"T": "human"}),
        ("It's S", {"S": "human"}),
        ("i'd say d bot", {"D": "ai"}),
        ("i'd say a bot", {"A": "ai"}),
    ]

    roster = {"bots": ["A"], "humans": ["B", "C"]}
    all_ai = {"A": "ai", "B": "ai", "C": "ai"}
    all_human = {"A": "human", "B": "human", "C": "human"}

    roster_tests = [
        # --- "nobody" / "none" with roster → all ai ---
        ("nobody", all_ai, roster),
        ("Nobody", all_ai, roster),
        ("no one", all_ai, roster),
        ("none", all_ai, roster),
        ("None of them", all_ai, roster),
        ("nope", all_ai, roster),
        ("nah", all_ai, roster),
        ("zero", all_ai, roster),
        ("all bots", all_ai, roster),
        ("all ai", all_ai, roster),
        ("they're all bots", all_ai, roster),
        ("they are all ai", all_ai, roster),
        ("not anyone", all_ai, roster),
        ("not anybody", all_ai, roster),
        ("nessuno", all_ai, roster),
        ("", all_ai, roster),
        ("  ", all_ai, roster),
        # --- "all humans" / "everyone" with roster → all human ---
        ("all", all_human, roster),
        ("all humans", all_human, roster),
        ("all human", all_human, roster),
        ("all real", all_human, roster),
        ("all of them", all_human, roster),
        ("all people", all_human, roster),
        ("humans", all_human, roster),
        ("human", all_human, roster),
        ("humans only", all_human, roster),
        ("human only", all_human, roster),
        ("people", all_human, roster),
        ("everyone", all_human, roster),
        ("everybody", all_human, roster),
        ("each one", all_human, roster),
        ("each of them", all_human, roster),
        ("they are all humans", all_human, roster),
        ("they're all humans", all_human, roster),
        ("they're all real", all_human, roster),
        ("tutti", all_human, roster),
        # --- "nobody" / "everyone" without roster → empty ---
        ("nobody", {}, None),
        ("none", {}, None),
        ("", {}, None),
        ("all", {}, None),
        ("humans", {}, None),
        ("everyone", {}, None),
        # --- Normal votes still work with roster ---
        ("A", {"A": "human"}, roster),
        ("B bot", {"B": "ai"}, roster),
        ("A human, B bot", {"A": "human", "B": "ai"}, roster),
        ("A, B, C", {"A": "human", "B": "human", "C": "human"}, roster),
    ]

    passed = 0
    total = 0

    # Tests without roster
    for msg, expected in tests:
        total += 1
        result = pv(msg)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            print(f"  {status}: {msg!r}\n    expected {expected}\n    got      {result}")
        else:
            print(f"  {status}: {msg!r} -> {result}")
            passed += 1

    # Tests with roster
    for entry in roster_tests:
        msg, expected, r = entry
        total += 1
        if r is not None:
            result = pv(msg, bots=r["bots"], humans=r["humans"])
        else:
            result = pv(msg)
        status = "PASS" if result == expected else "FAIL"
        roster_label = f" [roster]" if r else " [no roster]"
        if status == "FAIL":
            print(f"  {status}: {msg!r}{roster_label}\n    expected {expected}\n    got      {result}")
        else:
            print(f"  {status}: {msg!r}{roster_label} -> {result}")
            passed += 1

    print(f"\n{passed}/{total} passed")


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
                              if r.count_guests(count_temp_too=True) == 1 and
                              not r.are_fake_names_clashing()]

            # Filtering: rooms with that can still accept guests (ordinary rooms)
            ordinary_rooms = [r for r in rooms
                              if (1 < r.count_guests(count_temp_too=True) < Config.max_guests_per_room) and
                              not r.are_fake_names_clashing()]

            # Ops, no free spots in rooms with somebody already there: go overbooking!
            # (of course, there are no critical rooms in this case)
            if len(critical_rooms) + len(ordinary_rooms) == 0:
                ordinary_rooms = [r for r in rooms
                                  if (1 < r.count_guests(count_temp_too=True) < (Config.max_guests_per_room +
                                                                                 Config.max_overbooked_guests) and
                                      not r.are_fake_names_clashing())]

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
        title=f"\n🏨 [bold]Turing Hotel: {'Hotel' if is_hotel else 'Single Floor'} Status[/bold]",
        box=box.HEAVY_EDGE,
        show_lines=False  # We will draw our own floor separators
    )

    table.add_column("Floor", style="cyan", justify="center")
    table.add_column("Room", style="magenta")
    table.add_column("Occupancy", justify="center")
    table.add_column("Overbooked", justify="center")
    table.add_column(f"Guests (Name | {'Status~Timer' if not is_hotel else 'Freshness'} | Type)")

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
                if not is_hotel:
                    status = (room.guest2status[g].value + "~") if g in room.guest2status else ""
                    time_in_status = room.get_time_in_current_status(g)
                else:
                    status = ""
                    time_in_status = room.get_time_spent_in_room_by(g)
                guest_info.append(f"• {name} | [bold]{status}{time_in_status}[/bold] | [{color}]{label}[/]")

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

    def kill_active_live():
        """Tear down whatever "Live" currently owns the terminal. Call BEFORE constructing a new one."""
        live = getattr(sys, "_active_live_session", None)
        if live is not None:
            if live is None:
                return
            try:
                live: Live
                live.stop()
            except Exception:
                pass
            try:
                atexit.unregister(live.stop)
            except Exception:
                pass

    def set_active_live(live):
        """Install a new "Live" as the terminal owner. Call AFTER constructing and starting it."""
        setattr(sys, "_active_live_session", live)
        atexit.register(live.stop)

    # Rendering
    if structure.live is None:
        kill_active_live()
        structure.live = Live(screen, screen=False, auto_refresh=False)  # Lazy init
        structure.live.start()
        set_active_live(structure.live)
    else:
        structure.live.update(screen, refresh=True)  # Update
