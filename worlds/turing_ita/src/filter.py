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
import os
import re
import sys
import unicodedata


class FilterResult:
    """What the filter has to say about one message.

    Attributes:
        clean_msg: The message with every hit masked (it is the text that gets broadcast).
        hits: List of (category, matched text) pairs, in the order they appear in the message.
        severe: The subset of `hits` that counts towards the strikes (hate speech).
    """

    def __init__(self, clean_msg: str, hits: list[tuple[str, str]]) -> None:
        self.clean_msg = clean_msg
        self.hits = hits
        self.severe = [h for h in hits if h[0] in MessageFilter.SEVERE_CATEGORIES]

    def __bool__(self) -> bool:
        return len(self.hits) > 0

    def __str__(self) -> str:
        if not self.hits:
            return "[FilterResult] clean"
        return "[FilterResult] " + ", ".join(f"{cat}:'{txt}'" for cat, txt in self.hits)


class MessageFilter:
    """Interface of a message filter, so that the floor manager does not care about the engine.

    A filter takes the raw text a guest wants to say in the room and returns a `FilterResult`: the
    masked text to broadcast plus the list of what was found. `check` is a coroutine on purpose: a
    future model-based filter can run its (blocking) inference in a thread without changing any of
    the calling code.
    """

    # Categories. The ones in SEVERE_CATEGORIES are the only ones counting towards the strikes:
    # masking somebody's phone number protects that person, it is not something to punish them for.
    PROFANITY = "PAROLACCIA"
    SLUR = "OFFESA"
    PII_EMAIL = "EMAIL"
    PII_PHONE = "TELEFONO"
    PII_IBAN = "IBAN"
    PII_FISCAL_CODE = "CODICE FISCALE"
    PII_VAT = "PARTITA IVA"
    PII_CARD = "CARTA"
    PII_ADDRESS = "INDIRIZZO"
    PII_IP = "IP"
    PII_LINK = "LINK"
    PII_SOCIAL = "CONTATTO"

    SEVERE_CATEGORIES = {SLUR}

    MASKS = {
        PROFANITY: "***",
        SLUR: "***",
        PII_EMAIL: "[email]",
        PII_PHONE: "[telefono]",
        PII_IBAN: "[IBAN]",
        PII_FISCAL_CODE: "[codice fiscale]",
        PII_VAT: "[partita IVA]",
        PII_CARD: "[carta]",
        PII_ADDRESS: "[indirizzo]",
        PII_IP: "[indirizzo IP]",
        PII_LINK: "[link]",
        PII_SOCIAL: "[contatto]",
    }

    async def check(self, msg: str, allowed_names: set[str] | None = None) -> FilterResult:
        """Check one message (async).

        Args:
            msg: The raw text the guest wants to send to the room.
            allowed_names: Words that must never be flagged, whatever the lists say. The floor
                manager passes the fake names of the room here: they are the one thing guests are
                supposed to write, and a name is exactly the kind of word a filter loves to hit.

        Returns:
            A FilterResult.
        """
        raise NotImplementedError


# --------------------------------------------------------------------------------- normalisation

# Leetspeak and lookalikes, folded away before matching, so that "c4zz0" and "cazzo" are the same
# word. This is applied to a copy of the message: the text that gets broadcast is always the original
# one, with the hits (and only the hits) replaced by a mask.
_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "6": "g", "7": "t", "8": "b", "9": "g",
         "@": "a", "$": "s", "€": "e", "£": "e", "!": "i", "|": "i", "*": "a"}

# Cyrillic and Greek letters that look exactly like Latin ones on screen: "сazzo" written with a
# Cyrillic "с" is a different string for a computer and the same word for a reader. Compatibility
# decomposition already handles the other lookalike families (fullwidth, maths, circled letters).
_HOMOGLYPHS = {
    "а": "a", "в": "b", "с": "c", "е": "e", "ѕ": "s", "і": "i", "ј": "j", "к": "k", "м": "m",
    "н": "h", "о": "o", "р": "p", "т": "t", "у": "y", "х": "x", "г": "r", "ѵ": "v",
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "σ": "s",
    "τ": "t", "υ": "u", "χ": "x", "γ": "y", "ω": "w",
}

_RUN = re.compile(r"(.)\1{1,}")


def _squeeze(word: str) -> str:
    """Collapse every run of repeated characters to a single one ("caaazzzo" -> "cazo")."""
    return _RUN.sub(r"\1", word)


def _has_long_run(word: str) -> bool:
    """True if the word contains a character repeated 3+ times, i.e. it was probably stretched."""
    return re.search(r"(.)\1{2,}", word) is not None


def _normalize(text: str) -> tuple[str, list[int]]:
    """Fold a message into its matchable form, keeping track of where every character came from.

    Accents are dropped, leetspeak is translated, everything that is not a letter or a digit becomes
    a separator. The returned list maps each character of the normalised text back to its index in
    the original message, which is what lets us mask the original text (not the folded one).

    Args:
        text: The original message.

    Returns:
        A (normalised text, positions) pair.
    """
    out: list[str] = []
    pos: list[int] = []

    for i, ch in enumerate(text):

        # Invisible characters are dropped, not turned into a separator: "ca<zero width space>zzo"
        # is one word written to look like two
        if unicodedata.category(ch) in ("Cf", "Mn"):
            continue

        folded = _HOMOGLYPHS.get(ch.lower(), ch)
        folded = _LEET.get(folded, folded)
        folded = unicodedata.normalize("NFKD", folded)
        folded = "".join(c for c in folded if not unicodedata.combining(c)).lower()

        for c in folded:
            if c.isalnum():
                out.append(c)
                pos.append(i)
            elif out and out[-1] != " ":
                out.append(" ")
                pos.append(i)

    return "".join(out), pos


def _tokenize(norm: str) -> list[tuple[str, int, int]]:
    """Split the normalised text into (word, start, end) triples, with indexes into `norm`."""
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[a-z0-9]+", norm)]


_MAX_GLUE_WINDOW = 6  # How many pieces at most a chopped up word is looked for in
_MIN_GLUE_LEN = 4  # Shorter than this, a glued word is more likely a coincidence than an insult


def _glued_tokens(msg: str, pos: list[int], tokens: list[tuple[str, int, int]],
                  common_words: set[str]) -> list[tuple[str, int, int]]:
    """Put back together words that were chopped up to walk past the lists.

    Three ways of chopping a word are covered, in growing order of how careful we have to be:

    1. spelling it out one letter at a time ("v a f f a n c u l o"): a run of 4+ single letters is
       an anomaly by itself, so it is glued whatever its length;
    2. cutting it with punctuation ("C-og-lio-ne", "c.a.z.z.o"): pieces that are not separated by a
       space are glued back, again unconditionally, because ordinary writing does not do this;
    3. cutting it with spaces ("co gli o ne"): this is the delicate one, since every ordinary
       sentence is made of pieces separated by spaces. Windows of up to `_MAX_GLUE_WINDOW` words are
       glued, but the result is dropped when every piece is a common Italian word ("con te" must
       never become "conte") and when it is too short to be anything but a coincidence.

    The glued words are ADDED to the token list, the original words stay: nothing that used to be
    found stops being found.

    Args:
        msg: The original message (needed to tell a space apart from any other separator).
        pos: The position map returned by `_normalize`.
        tokens: The words of the normalised message.
        common_words: Ordinary words, used to leave ordinary sentences alone.

    Returns:
        The list of glued words, as (word, start, end) triples over the normalised text.
    """
    glued: list[tuple[str, int, int]] = []
    n = len(tokens)

    def _join(pieces):
        return "".join(p[0] for p in pieces), pieces[0][1], pieces[-1][2]

    def _spaced(a, b):
        """True if there is a space between two consecutive words in the ORIGINAL message."""
        return any(c.isspace() for c in msg[pos[a[2] - 1] + 1:pos[b[1]]])

    # (1) Words spelled out one letter at a time
    i = 0
    while i < n:
        j = i
        while j < n and len(tokens[j][0]) == 1:
            j += 1
        if j - i >= 4:
            glued.append(_join(tokens[i:j]))
        i = j + 1 if j == i else j

    # (2) Words cut with punctuation only
    i = 0
    while i < n:
        j = i
        while j + 1 < n and not _spaced(tokens[j], tokens[j + 1]):
            j += 1
        if j > i:
            glued.append(_join(tokens[i:j + 1]))
        i = j + 1

    # (3) Words cut with spaces
    for i in range(n):
        for size in range(2, _MAX_GLUE_WINDOW + 1):
            if i + size > n:
                break
            pieces = tokens[i:i + size]
            word = "".join(p[0] for p in pieces)
            if len(word) < _MIN_GLUE_LEN:
                continue
            if all(p[0] in common_words for p in pieces):
                continue
            glued.append(_join(pieces))

    return glued


# --------------------------------------------------------------------------------- word lists

class Lexicon:
    """One wordlist, compiled for matching.

    Entries are matched on whole words, which is what structurally kills the "Scunthorpe problem":
    "arsenale" cannot match "arse", because "arsenale" is one word and it is not in the list. Only
    entries explicitly ending with "*" match by prefix.
    """

    def __init__(self, entries: list[str]) -> None:
        self.exact: set[str] = set()
        self.squeezed: set[str] = set()  # For stretched writing ("caaaazzzo")
        self.prefixes: list[str] = []
        self.phrases: dict[str, list[tuple[str, ...]]] = {}

        for entry in entries:
            words = entry.split()
            if len(words) > 1:
                self.phrases.setdefault(words[0], []).append(tuple(words))
            elif entry.endswith("*"):
                self.prefixes.append(entry[:-1])
            elif entry:
                self.exact.add(entry)
                self.squeezed.add(_squeeze(entry))

        self.prefixes = sorted(self.prefixes)

    def __len__(self) -> int:
        return len(self.exact) + len(self.prefixes) + sum(len(v) for v in self.phrases.values())

    def has_exact(self, word: str) -> bool:
        """True if this exact word is in the list (also when stretched, e.g. "cazzoooo")."""
        return word in self.exact or (_has_long_run(word) and _squeeze(word) in self.squeezed)

    def has_word(self, word: str) -> bool:
        """Like `has_exact`, but the entries ending with "*" match by prefix too."""
        if self.has_exact(word):
            return True
        for prefix in self.prefixes:
            if len(word) > len(prefix) and word.startswith(prefix):
                return True
        return False

    def match_phrase(self, tokens: list[tuple[str, int, int]], i: int) -> int:
        """Length (in tokens) of the longest list phrase starting at token `i`, 0 if none."""
        best = 0
        for phrase in self.phrases.get(tokens[i][0], ()):
            n = len(phrase)
            if i + n <= len(tokens) and all(tokens[i + k][0] == phrase[k] for k in range(n)):
                best = max(best, n)
        return best


# Words that are an insult only when thrown at somebody: "sei un finocchio" is a slur, "il finocchio
# in insalata" is a vegetable. No wordlist can tell the two apart, so these are flagged only when an
# insult trigger shows up within a few words. Everything unambiguous lives in the wordlists instead.
_AMBIGUOUS = {"finocchio": MessageFilter.SLUR, "finocchi": MessageFilter.SLUR,
              "checca": MessageFilter.SLUR, "checche": MessageFilter.SLUR}

_INSULT_TRIGGERS = {"sei", "siete", "sembri", "sembrate", "sembra", "brutto", "brutta", "brutti",
                    "brutte", "pezzo", "razza", "maledetto", "maledetta", "schifoso", "schifosa"}

_INSULT_WINDOW = 3  # How many words before/after are looked at, when deciding on an ambiguous word


# The lists loaded by RuleBasedFilter below. They double as the signature of a valid "wordlists"
# folder: a candidate directory is taken only if it holds all of them, so a same-named folder that
# happens to sit somewhere on sys.path cannot be mistaken for ours. Keep in sync with __init__.
_WORDLISTS = ("allowlist.txt", "common_it.txt", "slurs_it.txt", "slurs_en.txt",
              "profanity_it.txt", "profanity_en.txt")

_WORDLISTS_ENV = "TURING_ITA_WORDLISTS"  # Escape hatch: point it at the folder and skip the search

_wordlists_dir_found: str | None = None  # Resolved once, the answer cannot change within a process


def _holds_wordlists(directory: str) -> bool:
    """True if `directory` is a wordlists folder, i.e. it holds every list we are going to read."""
    return all(os.path.isfile(os.path.join(directory, name)) for name in _WORDLISTS)


def _wordlists_dir() -> str:
    """Locate the "wordlists" directory on the local filesystem.

    Only .py files travel to the other nodes, so these lists are never part of the world bundle: they
    have to be found on disk, in a checkout of this world. Two things make that awkward. This module
    is routinely loaded from an in-memory source (the framework builds both the role dummy agents and
    the running manager agents that way), and there __file__ is not defined at all, because the
    in-memory loader gives its modules a virtual origin and no location; and the working directory is
    whatever the launcher happened to be started from, which is not necessarily the world folder. We
    therefore try, in this order: the environment variable, the directory of this module (plain import
    from disk), every sys.path entry and finally the working directory, looking at each base both
    directly and through a "src" subfolder. sys.path is the one that carries us home when the world is
    hosted from elsewhere: running "uv run .../turing_ita/run_w.py" from the repository root puts the
    world folder in sys.path[0] whatever the working directory is, and the framework itself appends
    the world folder to sys.path before building the behaviors.
    """
    global _wordlists_dir_found
    if _wordlists_dir_found is not None:
        return _wordlists_dir_found

    env_dir = os.environ.get(_WORDLISTS_ENV)
    if env_dir:
        if not _holds_wordlists(env_dir):
            raise FileNotFoundError(f"{_WORDLISTS_ENV} is set to '{env_dir}', but that directory does not hold "
                                    f"the expected lists: {', '.join(_WORDLISTS)}")
        _wordlists_dir_found = env_dir
        return env_dir

    bases: list[str] = []
    module_file = globals().get("__file__")  # Undefined when this module is loaded from memory
    if module_file:
        bases.append(os.path.dirname(os.path.abspath(module_file)))
    for entry in list(sys.path) + [os.getcwd()]:
        base = os.path.abspath(entry) if entry else os.getcwd()
        bases += [base, os.path.join(base, "src")]

    for base in bases:
        directory = os.path.join(base, "wordlists")
        if _holds_wordlists(directory):
            _wordlists_dir_found = directory
            return directory
    next_to = f"next to '{module_file}', " if module_file else ""
    raise FileNotFoundError(f"Could not locate the turing_ita 'wordlists' directory: looked {next_to}under every "
                            f"sys.path entry and under '{os.getcwd()}'. Run from a checkout of this world, or set "
                            f"{_WORDLISTS_ENV} to the directory holding {', '.join(_WORDLISTS)}")


def load_wordlist(name: str) -> list[str]:
    """Read one of the shipped wordlists, dropping comments and blank lines."""
    path = os.path.join(_wordlists_dir(), name)
    with open(path, encoding="utf-8") as f:
        return [ln.strip().lower() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]


# --------------------------------------------------------------------------------- PII validators

def _digits(text: str) -> str:
    return "".join(c for c in text if c.isdigit())


def valid_iban(text: str) -> bool:
    """ISO 13616 check (move the first 4 characters to the end, letters to numbers, mod 97 == 1)."""
    s = "".join(c for c in text.upper() if c.isalnum())
    if not (15 <= len(s) <= 34) or not s[:2].isalpha() or not s[2:4].isdigit():
        return False
    s = s[4:] + s[:4]
    n = 0
    for c in s:
        n = (n * 10 + int(c)) % 97 if c.isdigit() else (n * 100 + (ord(c) - 55)) % 97
    return n == 1


def valid_luhn(text: str) -> bool:
    """Luhn checksum, used by credit card numbers."""
    d = _digits(text)
    if not (13 <= len(d) <= 19):
        return False
    total = 0
    for i, c in enumerate(reversed(d)):
        v = int(c)
        if i % 2 == 1:
            v *= 2
            if v > 9:
                v -= 9
        total += v
    return total % 10 == 0


_CF_ODD = {**{str(i): v for i, v in enumerate([1, 0, 5, 7, 9, 13, 15, 17, 19, 21])},
           **{c: v for c, v in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                                   [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11,
                                    3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23])}}


def valid_fiscal_code(text: str) -> bool:
    """Italian "codice fiscale": shape plus its control character."""
    s = text.upper()
    if len(s) != 16 or not s.isalnum():
        return False
    total = 0
    for i, c in enumerate(s[:15]):
        if i % 2 == 0:  # Odd position, 1-based
            total += _CF_ODD[c]
        else:
            total += int(c) if c.isdigit() else ord(c) - 65
    return s[15] == chr(total % 26 + 65)


def valid_vat(text: str) -> bool:
    """Italian "partita IVA": 11 digits with a Luhn-like check digit."""
    d = _digits(text)
    if len(d) != 11:
        return False
    total = 0
    for i, c in enumerate(d[:10]):
        v = int(c)
        if i % 2 == 1:  # Even position, 1-based
            v *= 2
            if v > 9:
                v -= 9
        total += v
    return int(d[10]) == (10 - total % 10) % 10


def valid_ip(text: str) -> bool:
    """Four octets in 0..255 (so that version numbers like 4.56.1.2 do not look like addresses)."""
    parts = text.split(".")
    return len(parts) == 4 and all(p.isdigit() and len(p) <= 3 and int(p) <= 255 for p in parts)


class RuleBasedFilter(MessageFilter):
    """Wordlists plus regular expressions, no dependencies, no model, no network.

    Three things it does well: it never disagrees with itself (same message, same verdict, forever);
    on structured personal data it is essentially exact, because every hit is confirmed by the
    checksum the data itself carries (IBAN, credit card, "codice fiscale", VAT number); and it is
    hard to walk past, because the message is folded (accents, leetspeak, lookalike letters,
    invisible characters, stretching) and the words somebody chopped up are glued back together
    before anything is looked up. See `_normalize` and `_glued_tokens`.

    Two things it cannot do, and a model-based filter would: recognise personal data written in
    plain words ("mi chiamo Mario Bianchi e abito a Rovezzano"), and recognise an insult built out
    of perfectly clean words. Those are the reasons `MessageFilter` exists as an interface.
    """

    # Order matters: the first pattern that claims a piece of text wins, so e-mails are looked for
    # before links (an e-mail contains a domain) and IBANs before plain numbers.
    def __init__(self, use_pii: bool = True) -> None:
        self.allow = Lexicon(load_wordlist("allowlist.txt"))
        self.common_words = set(load_wordlist("common_it.txt"))
        self.lexicons = [
            (self.SLUR, Lexicon(load_wordlist("slurs_it.txt") + load_wordlist("slurs_en.txt"))),
            (self.PROFANITY, Lexicon(load_wordlist("profanity_it.txt") + load_wordlist("profanity_en.txt"))),
        ]
        self.use_pii = use_pii
        self.pii = [
            (self.PII_EMAIL, re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]{2,}"), None),
            (self.PII_LINK, re.compile(r"(?:https?://|www\.)\S+", re.I), None),
            (self.PII_SOCIAL, re.compile(r"(?:t\.me/|wa\.me/|instagram\.com/|tiktok\.com/|"
                                         r"telegram\.me/)\S+|(?<![\w.])@[A-Za-z][\w.]{2,}"), None),
            (self.PII_IBAN, re.compile(r"\b[A-Z]{2}\d{2}[ ]?(?:[A-Za-z0-9]{4}[ ]?){2,7}[A-Za-z0-9]{1,4}\b"),
             valid_iban),
            (self.PII_FISCAL_CODE, re.compile(r"\b[A-Za-z]{6}\d{2}[A-Za-z]\d{2}[A-Za-z]\d{3}[A-Za-z]\b"),
             valid_fiscal_code),
            (self.PII_CARD, re.compile(r"\b(?:\d[ -]?){13,19}\b"), valid_luhn),
            (self.PII_VAT, re.compile(r"\b\d{11}\b"), valid_vat),
            # The lookarounds keep the international form from firing in the middle of a longer
            # number (an IBAN that did not pass its checksum is full of "00" runs)
            (self.PII_PHONE, re.compile(r"(?:(?:\+|00)\s?39[ .-]?)?\b3\d{2}[ .-]?\d{3}[ .-]?\d{3,4}\b|"
                                        r"(?<![\w])(?:\+|00)\d{2}[ .-]?\d{6,12}(?!\d)"), None),
            (self.PII_IP, re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), valid_ip),
            (self.PII_ADDRESS, re.compile(r"\b(?:via|viale|piazza|p\.zza|corso|vicolo|largo|strada|"
                                          r"contrada|localita)\s+[\w'’.-]+(?:\s+[\w'’.-]+){0,3}[,\s]+\d+\b",
                                          re.I), None),
        ]

    async def check(self, msg: str, allowed_names: set[str] | None = None) -> FilterResult:
        if msg is None or len(msg.strip()) == 0:
            return FilterResult(msg, [])

        allowed = set()
        for name in (allowed_names or ()):
            normalized, _ = _normalize(name)
            allowed.update(normalized.split())

        spans: list[tuple[int, int, str, str]] = []  # (start, end, category, matched text)

        # Personal data, looked for in the original text: an e-mail or an IBAN only makes sense with
        # its dots, its "@" and its digits, which normalisation would fold away
        if self.use_pii:
            for category, pattern, validator in self.pii:
                for m in pattern.finditer(msg):
                    if validator is None or validator(m.group(0)):
                        spans.append((m.start(), m.end(), category, m.group(0)))

        # Bad words, looked for in the normalised text
        norm, pos = _normalize(msg)
        tokens = _tokenize(norm)

        skip_until = 0
        for i, (word, start, end) in enumerate(tokens):
            if i < skip_until:
                continue

            # Phrases are looked at before single words, and before the allowlist: "madonna" alone is
            # the mother of Jesus and stays, "porca madonna" is not and goes
            n = self.allow.match_phrase(tokens, i)
            if n > 0:
                skip_until = i + n
                continue

            matched = False
            for category, lexicon in self.lexicons:
                n = lexicon.match_phrase(tokens, i)
                if n > 0:
                    last_end = tokens[i + n - 1][2]
                    spans.append((pos[start], pos[last_end - 1] + 1, category,
                                  msg[pos[start]:pos[last_end - 1] + 1]))
                    skip_until = i + n
                    matched = True
                    break
            if matched:
                continue

            if word in allowed or self.allow.has_word(word):
                continue

            if word in _AMBIGUOUS:
                if self.__aimed_at_somebody(tokens, i):
                    spans.append((pos[start], pos[end - 1] + 1, _AMBIGUOUS[word],
                                  msg[pos[start]:pos[end - 1] + 1]))
                continue

            for category, lexicon in self.lexicons:
                if lexicon.has_word(word):
                    spans.append((pos[start], pos[end - 1] + 1, category, msg[pos[start]:pos[end - 1] + 1]))
                    break

        # Second pass, on the words that somebody chopped up to walk past the first one. Only exact
        # entries count here: prefixes and phrases on a glued word are guesswork on top of guesswork
        for word, start, end in _glued_tokens(msg, pos, tokens, self.common_words):
            if word in allowed or self.allow.has_exact(word):
                continue
            category = _AMBIGUOUS.get(word)  # Bothering to hide it is intent enough, no context needed
            if category is None:
                for candidate, lexicon in self.lexicons:
                    if lexicon.has_exact(word):
                        category = candidate
                        break
            if category is not None:
                spans.append((pos[start], pos[end - 1] + 1, category, msg[pos[start]:pos[end - 1] + 1]))

        return FilterResult(*self.__mask(msg, spans))

    @staticmethod
    def __aimed_at_somebody(tokens: list[tuple[str, int, int]], i: int) -> bool:
        """True if an ambiguous word at position `i` looks thrown at somebody rather than used."""
        near = tokens[max(0, i - _INSULT_WINDOW):i] + tokens[i + 1:i + 1 + _INSULT_WINDOW]
        return any(word in _INSULT_TRIGGERS for word, _, _ in near)

    @staticmethod
    def __mask(msg: str, spans: list[tuple[int, int, str, str]]) -> tuple[str, list[tuple[str, str]]]:
        """Replace every span with its mask, dropping the spans that overlap an earlier one."""
        if not spans:
            return msg, []

        # Longest first among those starting at the same point, so that "figlio di puttana" wins
        # over "puttana" and one hit is reported instead of two
        spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))

        kept: list[tuple[int, int, str, str]] = []
        last_end = -1
        for span in spans:
            if span[0] >= last_end:
                kept.append(span)
                last_end = span[1]

        out = []
        cursor = 0
        for start, end, category, text in kept:
            out.append(msg[cursor:start])
            out.append(MessageFilter.MASKS[category])
            cursor = end
        out.append(msg[cursor:])

        return "".join(out), [(c, t) for _, _, c, t in kept]


def test_rule_based_filter() -> None:
    """Self-test of the rule based filter, in the same spirit as the tests in utils.py.

    Run it with:  python -m worlds.turing_ita.src.filter
    """
    import asyncio

    f = RuleBasedFilter()
    names = {"Grazia", "Antonio", "Orso", "Gatto"}

    def check(msg):
        return asyncio.run(f.check(msg, allowed_names=names))

    # Clean messages must come out untouched: over-filtering is worse than under-filtering here,
    # a masked word makes a human guest look like a censored bot
    clean = [
        "Ciao Grazia, come va? Io sono appena tornato dal lavoro",
        "Ho comprato le rape e i piselli al mercato, poi ho fatto una passeggiata",
        "Che palle questa giornata, sono stanco morto",
        "Antonio secondo me tu sei un bot, sei troppo veloce a rispondere",
        "L'arsenale di Venezia e' bellissimo, ci sono stato l'anno scorso",
        "Il finocchio in insalata mi piace, con l'arancia",
        "Sono nato nel 1994 e ho 31 anni, abito al nord",
        "Mi hanno regalato un cane, si chiama Orso come te :)",
    ]
    for msg in clean:
        r = check(msg)
        assert not r.hits, f"false positive on {msg!r}: {r}"

    # Profanity: masked, no strike
    r = check("ma che cazzo dici, sei un coglione")
    assert r.clean_msg == "ma che *** dici, sei un ***", r.clean_msg
    assert len(r.hits) == 2 and not r.severe, r

    # Obfuscation. Every one of these is somebody trying to walk past the lists
    for msg, expected in [("ma che c4zz0 dici", "ma che *** dici"),               # Leetspeak
                          ("ma che caaaazzzo dici", "ma che *** dici"),           # Stretched
                          ("ma che CAZZO dici", "ma che *** dici"),               # Shouted
                          ("ma che CaZzO dici", "ma che *** dici"),               # Alternating case
                          ("ma che c-a-z-z-o dici", "ma che *** dici"),           # Cut, one letter
                          ("ma che c.a.z.z.o dici", "ma che *** dici"),           # Cut, dots
                          ("ma che c a z z o dici", "ma che *** dici"),           # Spelled out
                          ("ma che C-og-lio-ne sei", "ma che *** sei"),           # Cut in pieces
                          ("ma che co gli o ne sei", "ma che *** sei"),           # Pieces and spaces
                          ("ma che cazz o dici", "ma che *** dici"),              # One letter adrift
                          ("ti mando a vaffan culo", "ti mando a ***"),           # Cut in two
                          ("ma che ca\u200bzzo dici", "ma che *** dici"),          # Zero width space
                          ("ma che \u0441azzo dici", "ma che *** dici"),           # Cyrillic lookalike
                          ("ma che ｃａｚｚｏ dici", "ma che *** dici")]:            # Fullwidth
        r = check(msg)
        assert r.clean_msg == expected, f"{msg!r} -> {r.clean_msg!r}"

    # ...and glueing words back together must not invent insults in ordinary sentences
    for msg in ["con te non ci parlo piu'", "in fondo a destra c'e' il bar",
                "se ci penso mi viene da ridere", "la mia amica e' andata via",
                "ho fatto un salto in centro a fare la spesa"]:
        assert not check(msg).hits, f"false positive on {msg!r}: {check(msg)}"

    # Hate speech: masked AND severe (it is what feeds the strikes)
    r = check("sei un frocio di merda")
    assert len(r.severe) == 1 and r.severe[0][0] == MessageFilter.SLUR, r
    assert r.clean_msg == "sei un *** di ***", r.clean_msg

    # Multi-word entries win over their parts
    r = check("sei un figlio di puttana")
    assert len(r.hits) == 1, r
    assert r.clean_msg == "sei un ***", r.clean_msg

    # Personal data: masked, never severe
    r = check("scrivimi a mario.rossi@gmail.com oppure al 333 456 7890")
    assert [c for c, _ in r.hits] == [MessageFilter.PII_EMAIL, MessageFilter.PII_PHONE], r
    assert not r.severe, r
    assert r.clean_msg == "scrivimi a [email] oppure al [telefono]", r.clean_msg

    r = check("il mio iban e' IT60X0542811101000000123456, non dirlo a nessuno")
    assert [c for c, _ in r.hits] == [MessageFilter.PII_IBAN], r

    r = check("codice fiscale RSSMRA85T10A562S")
    assert [c for c, _ in r.hits] == [MessageFilter.PII_FISCAL_CODE], r

    # ...and one with the right shape but the wrong control character is not a "codice fiscale"
    assert not check("codice fiscale RSSMRA85T10A562A").hits

    r = check("carta 4539578763621486 scadenza 12/26")
    assert [c for c, _ in r.hits] == [MessageFilter.PII_CARD], r

    r = check("abito in via Giuseppe Garibaldi 42, vieni quando vuoi")
    assert [c for c, _ in r.hits] == [MessageFilter.PII_ADDRESS], r

    r = check("seguimi su instagram.com/mariorossi o scrivimi @mario.rossi")
    assert [c for c, _ in r.hits] == [MessageFilter.PII_SOCIAL, MessageFilter.PII_SOCIAL], r

    # Checksums: a number shaped like an IBAN but broken is not an IBAN
    assert not check("IT60X0542811101000000123457").hits

    # The fake names of the room are never touched, whatever a list says
    assert not check("ciao Gatto, ciao Orso").hits

    print("test_rule_based_filter: OK")


if __name__ == "__main__":
    test_rule_based_filter()
