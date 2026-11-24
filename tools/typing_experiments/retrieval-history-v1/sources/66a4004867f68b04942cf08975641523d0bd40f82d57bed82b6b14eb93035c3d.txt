"""Frozen host experiment; preceding context only, no labels or runtime authority.

The caller must pass the production fullTokenGeneration and text strictly before
its original token. None is an abstention; baseline fallback belongs to evaluation.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import hashlib
from importlib import metadata
import math
from pathlib import Path
import re


PINNED = {"pymorphy3": "2.0.6", "pymorphy3-dicts-ru": "2.4.417150.4580142",
          "dawg2-python": "0.9.0"}
WORD = re.compile(r"[а-яё]+", re.IGNORECASE)
CONTEXT = re.compile(r"[а-яё]+(?:[ \t]+[а-яё]+){0,2}[ \t]*\Z", re.IGNORECASE)
MORPH_WEIGHT = 16.0
STYLE_WEIGHT = 8.0
ORIGINAL_PENALTY = 64.0
MINIMUM_MARGIN = 24.0


@dataclass(frozen=True, repr=False)
class MorphAnalysis:
    lemma: str
    pos: str | None = None
    case: str | None = None
    number: str | None = None
    gender: str | None = None
    tense: str | None = None
    person: str | None = None
    grammemes: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        object.__setattr__(self, "grammemes", frozenset(self.grammemes))

    def __repr__(self):
        return "MorphAnalysis(redacted)"


@dataclass(frozen=True, repr=False)
class Decision:
    word: str | None
    reason: str
    scores: tuple[dict, ...] = ()

    def __repr__(self):
        return f"Decision(reason={self.reason!r}, candidateCount={len(self.scores)}, redacted)"


class PymorphyLexicon:
    """Lazy pinned dictionary lookup, bounded LRU; guesses never become evidence."""

    def __init__(self, cache_size: int = 4096):
        if type(cache_size) is not int or not 1 <= cache_size <= 16384:
            raise ValueError("INVALID_CACHE_SIZE")
        self._cache_size = cache_size
        self._cache = OrderedDict()
        self._analyzer = None
        self._dictionary_type = None

    def __repr__(self):
        return f"PymorphyLexicon(cached={len(self._cache)}, redacted)"

    def _load(self):
        if self._analyzer is None:
            _versions()
            import pymorphy3
            from pymorphy3.units import DictionaryAnalyzer
            self._analyzer = pymorphy3.MorphAnalyzer(units=[DictionaryAnalyzer()])
            self._dictionary_type = DictionaryAnalyzer

    def analyses(self, word: str) -> tuple[MorphAnalysis, ...]:
        if not _word(word):
            return ()
        key = word.lower()
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        self._load()
        result = []
        for parsed in self._analyzer.parse(key):
            stack = parsed.methods_stack
            if not stack or not all(isinstance(item[0], self._dictionary_type) for item in stack):
                continue
            tag = parsed.tag
            analysis = MorphAnalysis(parsed.normal_form, tag.POS, tag.case, tag.number,
                                     tag.gender, tag.tense, tag.person, frozenset(tag.grammemes))
            if analysis not in result:
                result.append(analysis)
        value = tuple(result)
        self._cache[key] = value
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return value

    def receipt(self) -> dict:
        """Content hashes bind installed code and dictionary; no local paths or text."""
        versions = _versions()
        packages = {}
        for name, version in versions.items():
            distribution = metadata.distribution(name)
            hashes = {}
            for entry in sorted(distribution.files or (), key=str):
                relative = str(entry)
                if ".." in Path(relative).parts or relative.endswith(".pyc"):
                    continue
                path = Path(distribution.locate_file(entry))
                if path.is_file():
                    hashes[relative] = _file_hash(path)
            if not hashes:
                raise ValueError("PACKAGE_FILES_UNAVAILABLE")
            packages[name] = {"version": version, "files": hashes}
        return {"schemaVersion": 1, "dictionaryOnly": True, "packages": packages}


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _versions() -> dict:
    versions = {name: metadata.version(name) for name in PINNED}
    if versions != PINNED:
        raise ValueError("UNPINNED_MORPHOLOGY")
    return versions


def _word(value) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 32 and WORD.fullmatch(value) is not None


def _integer(value, low, high) -> bool:
    return type(value) is int and low <= value <= high


def _number(value, low, high) -> bool:
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def _case(word):
    if word.islower():
        return "LOWER"
    if word[0].isupper() and word[1:].islower():
        return "TITLE"
    return None


GENERATION_FIELDS = {"original", "completion", "isValidWord", "protectedReason",
                     "prohibitsAutoReplace", "alternatives", "localSearch",
                     "inspectedStates", "verifiedTerminals"}
CANDIDATE_FIELDS = {"text", "canonicalKey", "terminalKey", "language", "isFallback",
                    "languagePrior", "frequencyRank", "unitDistance", "editCost",
                    "repeatedCharacterEdits", "repetitionBonus", "lengthDifference",
                    "casePattern", "kind", "canonicalCaseUnambiguous", "canonicalCaseAutoEligible"}
COMPLETIONS = {"COMPLETE", "PROTECTED", "VALID_WORD", "STATES_EXHAUSTED", "VERIFIED_EXHAUSTED",
               "CANCELLED", "UNAVAILABLE", "READER_FAILURE"}


def _candidate_valid(candidate: dict, original: str, *, local: bool) -> bool:
    if not isinstance(candidate, dict) or candidate.keys() - CANDIDATE_FIELDS:
        return False
    required = {"text", "canonicalKey", "terminalKey", "language", "isFallback", "frequencyRank",
                "unitDistance", "editCost", "casePattern"}
    if not required <= candidate.keys():
        return False
    text = candidate["text"]
    if not _word(text) or not _word(candidate["terminalKey"]):
        return False
    if (candidate["canonicalKey"] != text.lower() or candidate["terminalKey"] != text.lower()
            or text.lower() == original.lower() or candidate["casePattern"] != _case(text)
            or _case(text) != _case(original)):
        return False
    if candidate["language"] != "ru" or candidate["isFallback"] is not False:
        return False
    if candidate.get("kind", "SPELLING") != "SPELLING":
        return False
    if not _integer(candidate["frequencyRank"], 1, 2**31 - 1):
        return False
    if not _integer(candidate["unitDistance"], 1, 1 if local else 32):
        return False
    cost = candidate["editCost"]
    if not _number(cost, 0, 64) or cost * 4 != int(cost * 4):
        return False
    for key in ("repeatedCharacterEdits", "lengthDifference"):
        if key in candidate and not _integer(candidate[key], 0, 32):
            return False
    if "repetitionBonus" in candidate and not _number(candidate["repetitionBonus"], 0, 64):
        return False
    if "languagePrior" in candidate and not _integer(candidate["languagePrior"], 0, 2**31 - 1):
        return False
    for key in ("canonicalCaseUnambiguous", "canonicalCaseAutoEligible"):
        if key in candidate and type(candidate[key]) is not bool:
            return False
    return True


def _validate(generation, prefix):
    if not isinstance(prefix, str) or len(prefix) > 4096:
        return "invalid_prefix"
    if not isinstance(generation, dict) or generation.keys() != GENERATION_FIELDS:
        return "invalid_generation"
    original = generation["original"]
    if not _word(original) or _case(original) is None:
        return "unsupported_original"
    if (type(generation["isValidWord"]) is not bool or type(generation["prohibitsAutoReplace"]) is not bool
            or not isinstance(generation["completion"], str)
            or generation["completion"] not in COMPLETIONS):
        return "invalid_generation"
    if generation["isValidWord"] or generation["protectedReason"] is not None:
        return "protected_or_valid"
    completion = generation["completion"]
    if completion not in {"COMPLETE", "STATES_EXHAUSTED", "VERIFIED_EXHAUSTED"}:
        return "incomplete_generation"
    if generation["prohibitsAutoReplace"] != (completion != "COMPLETE"):
        return "invalid_generation"
    local = generation["localSearch"]
    if not isinstance(local, dict) or local.keys() != {"completion", "inspectedStates", "verifiedTerminals", "alternatives"}:
        return "invalid_local_search"
    if local["completion"] != "COMPLETE":
        return "incomplete_local_search"
    for snapshot in (generation, local):
        if (not _integer(snapshot["inspectedStates"], 0, 8192)
                or not _integer(snapshot["verifiedTerminals"], 0, 64)
                or not isinstance(snapshot["alternatives"], list)
                or len(snapshot["alternatives"]) > snapshot["verifiedTerminals"]):
            return "invalid_bounds"
        seen = set()
        for candidate in snapshot["alternatives"]:
            if not _candidate_valid(candidate, original, local=snapshot is local):
                return "invalid_candidate"
            key = candidate["canonicalKey"]
            if key in seen:
                return "duplicate_candidate"
            seen.add(key)
    if (local["inspectedStates"] > generation["inspectedStates"]
            or local["verifiedTerminals"] > generation["verifiedTerminals"]):
        return "invalid_bounds"
    return None


# Ambiguous prepositions retain their possible cases; these are soft rewards.
PREPOSITIONS = {"в": {"accs", "loct"}, "на": {"accs", "loct"}, "с": {"gent", "ablt"},
    "по": {"datv", "loct", "accs"}, "за": {"accs", "ablt"}, "под": {"accs", "ablt"},
    "о": {"loct", "accs"}, "об": {"loct", "accs"}, "к": {"datv"}, "ко": {"datv"},
    "из": {"gent"}, "у": {"gent"}, "для": {"gent"}, "без": {"gent"}, "до": {"gent"},
    "от": {"gent"}, "после": {"gent"}, "около": {"gent"}, "перед": {"ablt"},
    "над": {"ablt"}, "между": {"ablt", "gent"}}


def _agreement(left, right):
    if left.pos != "ADJF" or right.pos not in {"NOUN", "NPRO"}:
        return False
    if not left.case or not left.number or left.case != right.case or left.number != right.number:
        return False
    return left.number == "plur" or (left.gender is not None and left.gender == right.gender)


def _morphology(words, context, analyses):
    if not words or not analyses:
        return 0.0
    best = 0.0
    for analysis in analyses:
        bonus = 0.0
        for index in range(len(words) - 1, -1, -1):
            if words[index] in PREPOSITIONS and any(p.pos == "PREP" for p in context[index]):
                if (analysis.case in PREPOSITIONS[words[index]]
                        and all(any(p.pos == "ADJF" for p in tags) for tags in context[index + 1:])):
                    bonus += 0.75
                break
        if any(_agreement(previous, analysis) for previous in context[-1]):
            bonus += 0.75
        if words[-1] == "давай" and context[-1] and analysis.pos == "VERB" and analysis.number == "plur" and analysis.person == "1per":
            bonus += 1.0
        if words[-1] == "несколько" and context[-1] and analysis.pos == "NOUN" and analysis.number == "plur":
            bonus += 0.75 + (0.25 if analysis.case == "gent" else 0.0)
        best = max(best, min(1.0, bonus))
    return best


def decide(generation: dict, prefix: str, lexicon, *, style=None) -> Decision:
    """Score local candidates; malformed evidence abstains without echoing inputs."""
    error = _validate(generation, prefix)
    if error:
        return Decision(None, error)
    if style is not None and not callable(getattr(style, "bonus", None)):
        return Decision(None, "invalid_style")
    match = CONTEXT.search(prefix)
    # A mixed-script token suffix is not an independently observed Russian word.
    if not match or (match.start() and (prefix[match.start() - 1].isalnum() or prefix[match.start() - 1] == "_")):
        return Decision(None, "no_context")
    words = match.group().lower().split()[-3:]
    context = [lexicon.analyses(word) for word in words]
    ranked = []
    for candidate in generation["localSearch"]["alternatives"]:
        base = 8.0 * candidate["editCost"] + 2.0 * (candidate["frequencyRank"] - 1).bit_length()
        morphology = _morphology(words, context, lexicon.analyses(candidate["text"]))
        style_bonus = 0.0
        if style is not None:
            try:
                style_bonus = style.bonus(" ".join(words), candidate["text"])
            except (TypeError, ValueError, OverflowError):
                return Decision(None, "invalid_style")
            if not _number(style_bonus, 0, 1):
                return Decision(None, "invalid_style")
        penalty = base - MORPH_WEIGHT * morphology - STYLE_WEIGHT * style_bonus
        ranked.append({"word": candidate["text"], "basePenalty": base, "morphologyBonus": morphology,
                       "styleBonus": style_bonus, "penalty": penalty})
    ranked.sort(key=lambda item: (item["penalty"], item["word"]))
    scores = tuple(ranked)
    if not ranked:
        return Decision(None, "no_candidates")
    winner = ranked[0]
    if not winner["morphologyBonus"] and not winner["styleBonus"]:
        return Decision(None, "no_context_evidence", scores)
    rival = min(ORIGINAL_PENALTY, ranked[1]["penalty"] if len(ranked) > 1 else ORIGINAL_PENALTY)
    if rival - winner["penalty"] < MINIMUM_MARGIN:
        return Decision(None, "insufficient_margin", scores)
    return Decision(winner["word"], "context_supported", scores)
