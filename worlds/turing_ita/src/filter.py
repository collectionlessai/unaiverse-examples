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
_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b",
         "@": "a", "$": "s", "€": "e", "£": "e", "!": "i", "|": "i", "*": "a"}

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
        folded = _LEET.get(ch, ch)
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


def _join_spelled_out(tokens: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    """Glue back words that were spelled out one letter at a time ("c a z z o", "c-a-z-z-o").

    A run of 4+ single-character tokens is joined into one token (the single letters are kept too,
    so nothing that used to match still stops matching).
    """
    joined = list(tokens)
    i = 0
    while i < len(tokens):
        j = i
        while j < len(tokens) and len(tokens[j][0]) == 1:
            j += 1
        if j - i >= 4:
            joined.append(("".join(t[0] for t in tokens[i:j]), tokens[i][1], tokens[j - 1][2]))
        i = j + 1 if j == i else j
    return joined


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

    def has_word(self, word: str) -> bool:
        """True if this single word is in the list (also when stretched, e.g. "cazzoooo")."""
        if word in self.exact:
            return True
        if _has_long_run(word) and _squeeze(word) in self.squeezed:
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


def load_wordlist(name: str) -> list[str]:
    """Read one of the wordlists shipped next to this file, dropping comments and blank lines."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wordlists", name)
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

    Two things it does well: it never disagrees with itself (same message, same verdict, forever),
    and on structured personal data it is essentially exact, because every hit is confirmed by the
    checksum the data itself carries (IBAN, credit card, "codice fiscale", VAT number).

    Two things it cannot do, and a model-based filter would: recognise personal data written in
    plain words ("mi chiamo Mario Bianchi e abito a Rovezzano"), and recognise an insult built out
    of perfectly clean words. Those are the reasons `MessageFilter` exists as an interface.
    """

    # Order matters: the first pattern that claims a piece of text wins, so e-mails are looked for
    # before links (an e-mail contains a domain) and IBANs before plain numbers.
    def __init__(self, use_pii: bool = True) -> None:
        self.allow = Lexicon(load_wordlist("allowlist.txt"))
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
        tokens = _join_spelled_out(_tokenize(norm))

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

    # Obfuscation: leetspeak, stretching, letters spelled out one by one, accents
    for msg, expected in [("ma che c4zz0 dici", "ma che *** dici"),
                          ("ma che caaaazzzo dici", "ma che *** dici"),
                          ("ma che c-a-z-z-o dici", "ma che *** dici"),
                          ("ma che CAZZO dici", "ma che *** dici")]:
        r = check(msg)
        assert r.clean_msg == expected, f"{msg!r} -> {r.clean_msg!r}"

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
