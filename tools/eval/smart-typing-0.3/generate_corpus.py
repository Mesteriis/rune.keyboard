#!/usr/bin/env python3
"""Deterministically expand authored seeds into an explicitly clustered stress corpus."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import unicodedata

ROOT = Path(__file__).resolve().parent
SOURCE = "authored-rune-2026-09-02"
ALPHABETS = {"en": "abcdefghijklmnopqrstuvwxyz", "es": "abcdefghijklmnñopqrstuvwxyz", "ru": "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"}
VOWELS = {"en": "aeiou", "es": "aeiouáéíóú", "ru": "аеёиоуыэюя"}
ROWS = {"en": ["qwertyuiop", "asdfghjkl", "zxcvbnm"], "es": ["qwertyuiop", "asdfghjklñ", "zxcvbnm"], "ru": ["йцукенгшщзхъ", "фывапролджэ", "ячсмитьбю"]}
# Common valid single-edit collisions are never used as typo labels.
COLLISIONS = {
    "en": "a an the then them he she it is as at in on to of or do did for form from aboard abroad quite quit quiet lose loose dose does live love glove clover cover lover over liver lover filed field child cold could would should flock block lock click chick back bake cake take make lake late date rate hate mate bait wait paint pain paid said laid pair fair hair chair mere more bore core care dare rare bare bar car far jar war tar ear hear fear gear year bread broad dead read bead brand brake break snake shake stake steak house horse hose mouse rose nose pose chose close coast toast most cost cast last list lost fist first mist must rust dust dusk desk mask task ask book cook look took hook good food foot hood wood stood stool tool too two goo row low cow now how show snow know crop drop shop stop top hop cop pop mop cap cup cut cat cot coat boat bat hat hot hit hut bit fit fat rat red bed bad bid bud dad mad sad led leg log dog fog dig dug bog bug big bag beg pin pen pan pun bin ban bun fin fan fun tin tan ton ten can con son sun sin run ran rain brain drain grain train main gain stain plain plane plan lane lean mean meat meet neat seat seal sear bear tear pear peer beer deer dear tend send sent tent went vent belt melt felt volt bolt word work worm warm ward card cart part port sort fort sport short shirt skirt skin spin span scan scar star start art cart dart heart harm farm arm yard hard shard sharp share spare care case base chase phase phrase thing thin than that chat chart charm chord cord cone bone tone tune tube cube cute cure pure sure sour hour our four flour flower tower power mower lower upper supper super pupil public cubic music women woman man men van map rap tap lap gap wrap strap trap trip drip grip ship slip skip skin spin spit split hit heat heart thread threat wheat what white while whole hole pole sole sale same some came tame time dime lime line fine nine mine wine wide wife life knife rife ride side tide hide guide pride prize price rice nice mice slice spice space pace face race place peace piece niece knees needs seed see sea tea team steam seam seen scene screen green greet street sheet sheep sleep steep step stem stop stamp stump jump lump pump dump damp lamp camp ramp rampart rant rent bent bend band bond pond pound round sound found bound wound mind kind wind find bind blind child mild wild slide glide pride bride bridge fridge ridge range strange orange change chance dance lance glance glass grass brass class clash flash flesh fresh press stress dress address success access assess process recess excess".split(),
    "es": "a al el él la le lo los las les un una uno unas unos de dé te té se sé si sí mi mí tu tú mas más que qué como cómo solo sólo aun aún por para pero perro pera pelo peso paso piso puso posa rosa cosa casa caso masa mesa misa musa mano mono mina luna lona lana lena pena pan par paz mar mal sal sol son con sin tan ten tos dos mes vez voz ver ser ir dar bar caro carro cara cura cora cola copa ropa roca rota ruta rata risa rosa rojo ojo ajo hijo hilo pino vino fino tino sino signo siglo banco barco marco arco saco sabio sabia savia sabia tuvo tubo valla vaya baya halla haya echo hecho hola ola hora ahora oro loro loro toro coro codo todo modo lodo boda boca bota bola cola ola poca loco foco foca toca taco pato gato dato rato trato trajo traje viaje viaja viejo nueva nuevo nueve nieve llave llano lleno lleno seno sano sana sale vale mal mala palo pala sala sola sopa copa capa tapa taza tasa niña niño año ano caña cana mañana mana peña pena sueño sueno dueño duelo leña lena piña pina mañana mañana porción poción canción camión avión acción oración ocasión presión prisión tensión extensión".split(),
    "ru": "и а я у о в с к по на но не ни мы вы он им из за до от то та ту те ты бы был была быть или для что как так там тут тот дом дым дам дамы сама сам сом сон сын сыр сор мир мор мер мэр мел мил мыл мыло мало малина рана рано рамка банка баня башня басня каша наша ваша чаша чашка шашка шапка папка палка полка пилка пила сила село тело дело пело пень день тень лень лён лен лес лез лис лист лифт мост пост рост рот кот код ком кол кон кор корм срок сорок урок круг друг вдруг грудь грусть весть весь вес вещь печь речь речка репка редька беда еда езда игра игла мгла масло маска мясо место тесто текст ток так тик тук лук люк лак рак рок рог рык рёк рек счет счёт свет цвет совет ответ привет поезд поет поёт моет роет воет вон фон тон том там пар пир пер пёр пор пол пил пыл был бил бел бал бол боль моль роль соль ноль нуль стул стол стал стиль сталь стать стая своя твоя моя моя мою мол молю мал малю мать мять мят мёд мед лёд лед лёт лет лётчик летчик ход код год род рот рот рот коса коза кора гора пора нора нога рога река рука мука муха дуга душ дух дуб зуб суп суд сум шум шут жук сук сок бок бог бак бык бук бока пока порка корка горка горе море воля доля поле поля больной большой друг друга друзья писал пищал пиши пищи просить простить платить плавить править ставить славить причём причем всё все ещё еще ёж еж ёлка елка её ее".split(),
}


def stable(seed: str) -> random.Random:
    return random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))


def strip_accents(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")


def mutations(word: str, language: str, vocabulary: set[str]) -> list[tuple[str, str]]:
    possible = []
    def add(value: str, category: str) -> None:
        if (language != "ru" or value.replace("ё", "е") != word.replace("ё", "е")) and value.casefold() != word.casefold() and value.casefold() not in vocabulary and value and value not in {v for v, _ in possible}:
            possible.append((value, category))
    if language == "es" and strip_accents(word) != word:
        add(strip_accents(word), "diacritic")
        for index, char in enumerate(word):
            if strip_accents(char) != char:
                add(word[:index] + strip_accents(char) + word[index + 1:], "diacritic")
    for index in stable(word).sample(range(len(word)), len(word)):
        char = word[index]
        for keyboard_row in ROWS[language]:
            if char in keyboard_row:
                position = keyboard_row.index(char)
                neighbor = keyboard_row[position + 1] if position + 1 < len(keyboard_row) else keyboard_row[position - 1]
                add(word[:index] + neighbor + word[index + 1:], "adjacent_key")
        add(word[:index] + word[index + 1:], "missing_letter")
        add(word[:index] + char + word[index:], "repeated_letter")
        if index + 1 < len(word):
            add(word[:index] + word[index + 1] + char + word[index + 2:], "transposition")
        choices = VOWELS[language] if char in VOWELS[language] else "bcdfgmnpst" if language != "ru" else "бвгджклмнпрст"
        replacement = choices[(choices.find(char) + 1) % len(choices)]
        add(word[:index] + replacement + word[index + 1:], "wrong_vowel" if char in VOWELS[language] else "wrong_consonant")
        extra = ALPHABETS[language][(index * 7 + len(word)) % len(ALPHABETS[language])]
        add(word[:index] + extra + word[index:], "extra_letter")
        for extra in ("аенрст" if language == "ru" else "aenrst"):
            add(word[:index] + extra + word[index:], "extra_letter")
    # Round-robin categories: each family exposes several error mechanisms.
    categories = list(dict.fromkeys(category for _, category in possible))
    selected = []
    for depth in range(len(possible)):
        for category in categories:
            pool = [value for value, cat in possible if cat == category]
            if depth < len(pool):
                selected.append((pool[depth], category))
    return selected


def candidates_for(original: str, choices: list[str], seed: str) -> list[str]:
    from evaluate import edit_distance
    limit = 1 if len(original) < 5 else 2
    unique = list(dict.fromkeys(choice for choice in choices if choice != original and edit_distance(original.casefold(), choice.casefold()) <= limit))
    stable(seed).shuffle(unique)
    return [" " + original] + [" " + choice for choice in unique[:7]]


def base(language: str, split: str, family: str, template: str, prefix: str) -> dict:
    return {"corpusVersion": 2, "language": language, "split": split, "family": family, "template": template, "prefix": prefix, "source": SOURCE}


FILTER_DIGESTS = {
    "ru": "6095f507cc167488ec66ada5a85ac50433503a08ad24a07c6eabdf54352c4e7f",
    "en": "5351ff405b1126ef555791dd4d9798a48e3e9a501a9fc481a9da957752cfb458",
    "es": "dcff3ad4316192f4dc4ff7d26e637c6ff314ef1ca0f3f720c5649018a71056c0",
}


def collision_vocabulary(language: str) -> set[str]:
    path = ROOT.parents[2] / "build/smart-typing-0.3/corpus-inputs" / f"{language}_50k.txt"
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != FILTER_DIGESTS[language]:
        raise ValueError("collision filter digest mismatch")
    return {line.rsplit(" ", 1)[0].casefold() for line in data.decode("utf-8").splitlines()}


def spelling_rows(seeds: dict) -> list[dict]:
    rows = []
    nearby = json.loads((ROOT / "nearby-words.json").read_text(encoding="utf-8"))
    for language, splits in seeds["spelling"].items():
        vocabulary = {word.casefold() for groups in splits.values() for _, words in groups for word in words.split()} | set(COLLISIONS[language]) | collision_vocabulary(language) | {value.casefold() for values in nearby[language].values() for value in values}
        for split, groups in splits.items():
            other_split_words = {word.casefold() for other, other_groups in splits.items() if other != split for _, words in other_groups for word in words.split()}
            for group_index, (prefix, words_text) in enumerate(groups):
                words = words_text.split()
                for word_index, word in enumerate(words):
                    family = word.casefold()
                    alternatives = mutations(word, language, vocabulary)
                    if len(alternatives) < 12:
                        raise ValueError(f"insufficient distinct controlled mutations: {language}/{word}")
                    hard = [value for value in nearby[language].get(word, []) if value.casefold() not in other_split_words]
                    for variant, (typed, category) in enumerate(alternatives[:10]):
                        sid = f"{language}-{split}-typo-{group_index:02}-{word_index}-{variant}"
                        choices = [word, alternatives[(variant + 4) % len(alternatives)][0]] + hard
                        candidates = candidates_for(typed, choices, sid)
                        row = base(language, split, family, f"{split}-spelling-{group_index:02}", prefix)
                        row.update(id=sid, task="spelling", cohort="typo", typed=typed, expectedSpelling=word, candidates=candidates, expectedCandidate=candidates.index(" " + word), category=category, noAuto=len(word) <= 3, ambiguous=len(word) <= 3, position="middle" if variant % 2 else "end", wordLength=len(word))
                        rows.append(row)
                    # Repeated lexical/context observations with different *candidate sets* are
                    # deliberately identified as a candidate-sensitivity panel, not extra sentences.
                    for variant in range(7):
                        sid = f"{language}-{split}-correct-{group_index:02}-{word_index}-{variant}"
                        choices = [alternatives[variant][0], alternatives[variant + 5][0]] + hard
                        candidates = candidates_for(word, choices, sid)
                        row = base(language, split, family, f"{split}-spelling-{group_index:02}", prefix)
                        row.update(id=sid, task="spelling", cohort="correct", typed=word, candidates=candidates, expectedCandidate=0, category="correct_word", noAuto=False, ambiguous=False, position="end", wordLength=len(word), panel="candidate_set_sensitivity")
                        rows.append(row)
    return rows


def acceptance_and_positions(rows: list[dict]) -> None:
    initial_contexts = {
        "en": {"calibration": "The session has started.", "holdout": "The visit is over."},
        "ru": {"calibration": "Встреча началась.", "holdout": "Поездка закончилась."},
        "es": {"calibration": "La sesión ha empezado.", "holdout": "La visita ha terminado."},
    }
    for row in rows:
        if (row["cohort"] == "typo" and row["id"].endswith("-9")) or (row["cohort"] == "correct" and row["id"].endswith("-6")):
            row["typed"] = row["typed"][:1].upper() + row["typed"][1:]
            if "expectedSpelling" in row:
                expected = row["expectedSpelling"]
                row["expectedSpelling"] = expected[:1].upper() + expected[1:]
            row["candidates"] = [" " + candidate[1:2].upper() + candidate[2:] for candidate in row["candidates"]]
            row["prefix"] = initial_contexts[row["language"]][row["split"]]
            row["template"] = row["split"] + "-sentence-initial"
            row["position"] = "initial"
    examples = {
        "ru": [("Нам нужна", "автокрекция", "автокоррекция", "missing_letter"), ("Нас интересует", "арфография", "орфография", "wrong_vowel"), ("Пришло новое", "сообшение", "сообщение", "wrong_consonant")],
        "en": [("Please close", "teh", "the", "transposition"), ("We need to", "recieve", "receive", "transposition"), ("Please check the", "adress", "address", "missing_letter")],
        "es": [("Ha llegado un", "mensage", "mensaje", "wrong_consonant"), ("Hace falta una", "correcion", "corrección", "missing_letter_diacritic"), ("El niño dibuja un", "pinguino", "pingüino", "diacritic")],
    }
    for language, samples in examples.items():
        target_rows = [row for row in rows if row["language"] == language and row["split"] == "calibration" and row["cohort"] == "typo"]
        for target, (prefix, typed, expected, category) in zip(target_rows, samples):
            # Curated examples intentionally override the surface-frequency veto:
            # corpora of subtitles also contain misspellings such as 'teh'.
            target.update(prefix=prefix, template="calibration-curated-" + expected, typed=typed, expectedSpelling=expected, family=expected.casefold(), candidates=[" " + typed, " " + expected], expectedCandidate=1, category=category, noAuto=False, ambiguous=False, position="end", curatedAcceptance=True, wordLength=len(expected))


PROTECTED = {
    "calibration": {
        "name": ["Ирина", "Ольга", "Андрей", "Alice", "George", "Sofía", "Álvaro", "Lucía", "Núria", "Yolanda"],
        "surname": ["Иванов", "Соколова", "Морозов", "Smith", "Taylor", "García", "Muñoz", "Pérez", "Iglesias", "López"],
        "brand": ["Rune", "AIGate", "HomeAssistant", "ESPHome", "PostgreSQL", "Nikon", "IKEA", "Peugeot", "LEGO", "Mozilla"],
        "command": ["kubectl", "git status", "ls -la", "pwd", "mkdir demo", "cat README.md", "wc -l", "sort -u", "head -n 5", "tail -n 8"],
        "camel_case": ["currentWord", "candidateScore", "textBuffer", "readState", "writeValue", "startTimer", "stopWorker", "parseInput", "renderView", "updatePanel"],
        "snake_case": ["word_count", "score_sum", "model_path", "input_size", "output_file", "user_hint", "test_case", "data_row", "item_key", "cache_id"],
        "kebab_case": ["local-model", "typing-state", "score-cache", "input-method", "word-boundary", "text-entry", "auto-replace", "safe-mode", "error-code", "build-tool"],
        "identifier_python": ["__init__", "__name__", "str.encode", "pathlib.Path", "len(items)", "dict.get", "json.loads", "range(10)", "isinstance", "StopIteration"],
        "identifier_cpp": ["std::vector", "std::string", "std::optional", "size_t", "uint32_t", "nullptr", "constexpr", "noexcept", "thread_local", "static_cast"],
        "identifier_kotlin": ["InputConnection", "KeyboardState", "onCreate", "commitText", "setComposingText", "StringBuilder", "IntArray", "sealedClass", "dataObject", "isNullOrEmpty"],
        "all_caps": ["NASA", "HTTP", "JSON", "UTF", "CPU", "RAM", "SSD", "SQL", "IME", "NFC"],
        "digits": ["H2O", "B12", "Q4_K_M", "UTF8", "WiFi6", "USB3", "Android26", "Pixel9", "ISO9001", "A320"],
        "ambiguous_accent": ["resume", "cafe", "solo", "esta", "como", "el", "все", "еще", "причём", "берет"],
        "mixed": ["debug-сборка", "release-версия", "build-сценарий", "лог-parser", "тест-runner", "modo-debug", "reporte-JSON", "archivo-log", "buffer-строка", "modelo-local"],
        "hostname": ["build.example", "cache.example", "dev.example", "test.example", "docs.example", "model.example", "ci.example", "api.example", "git.example", "qa.example"]
    },
    "holdout": {
        "name": ["Мария", "Елена", "Дмитрий", "Chloe", "William", "Íñigo", "José", "Raúl", "Begoña", "Ximena"],
        "surname": ["Петров", "Кузнецова", "Орлов", "Brown", "Wilson", "Fernández", "Núñez", "Hernández", "Jiménez", "Sánchez"],
        "brand": ["Blender", "Krita", "Inkscape", "LibreOffice", "Audacity", "Fujifilm", "Škoda", "Citroën", "GitLab", "JetBrains"],
        "command": ["rg TODO", "find .", "git diff", "git log", "du -sh", "df -h", "uname -a", "python --version", "cmake --build out", "ctest --test-dir out"],
        "camel_case": ["previousToken", "marginValue", "editorFlags", "fetchConfig", "saveResult", "beginSession", "finishRequest", "decodeBytes", "layoutKeys", "refreshStatus"],
        "snake_case": ["token_total", "mean_logp", "artifact_name", "batch_limit", "result_name", "editor_mode", "sample_group", "source_line", "record_tag", "request_hash"],
        "kebab_case": ["native-runtime", "editor-session", "token-cache", "keyboard-layout", "sentence-end", "candidate-list", "undo-action", "strict-mode", "status-value", "test-suite"],
        "identifier_python": ["__repr__", "__main__", "bytes.decode", "hashlib.sha256", "sum(values)", "list.append", "json.dumps", "enumerate", "issubclass", "ValueError"],
        "identifier_cpp": ["std::map", "std::array", "std::span", "ptrdiff_t", "int64_t", "alignas", "consteval", "decltype", "namespace", "reinterpret_cast"],
        "identifier_kotlin": ["EditorInfo", "KeyEvent", "onDestroy", "finishComposingText", "deleteSurroundingText", "CharSequence", "LongArray", "mutableListOf", "lazyValue", "requireNotNull"],
        "all_caps": ["ESA", "HTTPS", "XML", "ASCII", "GPU", "ROM", "HDD", "DDL", "JNI", "NFD"],
        "digits": ["CO2", "D3", "Q8_0", "UTF16", "WiFi7", "USB4", "Android37", "Pixel10", "ISO27001", "B737"],
        "ambiguous_accent": ["naive", "expose", "aun", "mas", "que", "si", "ее", "вел", "узнаем", "небо"],
        "mixed": ["profile-сборка", "debug-режим", "native-библиотека", "score-панель", "runtime-тест", "modo-profile", "informe-XML", "fichero-cache", "token-слово", "modelo-base"],
        "hostname": ["preview.example", "staging.example", "static.example", "cdn.example", "assets.example", "images.example", "search.example", "status.example", "metrics.example", "support.example"]
    }
}


# Authored contrasts, not inferred accent insertion. Each orthographic family
# belongs to exactly one split. English/Spanish/Russian source language is explicit
# even where the surrounding context tests mixed-language protection.
ORTHOGRAPHIC_PAIRS = {
    "calibration": {
        "resume": ("résumé", "en_optional_accent"),
        "cafe": ("café", "en_optional_accent"),
        "solo": ("sólo", "es_ambiguous_accent"),
        "esta": ("está", "es_ambiguous_accent"),
        "como": ("cómo", "es_ambiguous_accent"),
        "el": ("él", "es_ambiguous_accent"),
        "все": ("всё", "ru_yo_e"),
        "еще": ("ещё", "ru_yo_e"),
        "причём": ("причем", "ru_yo_e"),
        "берет": ("берёт", "ru_yo_e"),
    },
    "holdout": {
        "naive": ("naïve", "en_optional_accent"),
        "expose": ("exposé", "en_optional_accent"),
        "aun": ("aún", "es_ambiguous_accent"),
        "mas": ("más", "es_ambiguous_accent"),
        "que": ("qué", "es_ambiguous_accent"),
        "si": ("sí", "es_ambiguous_accent"),
        "ее": ("её", "ru_yo_e"),
        "вел": ("вёл", "ru_yo_e"),
        "узнаем": ("узнаём", "ru_yo_e"),
    },
}


def protected_rows() -> list[dict]:
    rows = []
    for split, categories in PROTECTED.items():
        offset = 10 if split == "calibration" else 200
        categories = {**categories,
            "ipv4": [f"192.0.2.{offset+i}" for i in range(10)],
            "ipv6": [f"2001:db8:{offset+i:x}::1" for i in range(10)],
            "url": [f"https://example.test/{split}/page-{i}" for i in range(10)],
            "email": [f"sample-{split}-{i}@example.test" for i in range(10)],
            "semver": [f"{1 if split == 'calibration' else 2}.{i}.0-beta.{i+1}" for i in range(10)],
            "uuid": [f"{offset+i:08x}-1234-4567-89ab-0123456789ab" for i in range(10)],
            "path": [f"/synthetic/{split}/module-{i}/fixture.kt" for i in range(10)],
            "file_name": [f"fixture_{split}_{i}.jsonl" for i in range(10)],
            "hex_literal": [f"0x{offset+i:04X}" for i in range(10)],
            "version_identifier": [f"rune_{split}_v{offset+i}" for i in range(10)],
            "package_name": [f"org.example.{split}.module{i}" for i in range(10)],
            "code_expression": [f"samples[{offset+i}].score" for i in range(10)],
            "environment_key": [f"RUNE_{split.upper()}_OPTION_{i}" for i in range(10)],
            "branch_name": [f"feature/{split}-fixture-{i}" for i in range(10)],
            "numeric_token": [f"{offset+i}.5ms" for i in range(10)],
        }
        assert len(categories) == 30
        for language in ("ru", "en", "es"):
            prefix = {"ru": {"calibration": "В примере указано", "holdout": "В справочнике найдено"}, "en": {"calibration": "The example contains", "holdout": "The reference lists"}, "es": {"calibration": "El ejemplo contiene", "holdout": "La referencia indica"}}[language][split]
            for category, tokens in categories.items():
                for index, token in enumerate(tokens):
                    sid = f"{language}-{split}-protected-{category}-{index:02}"
                    # Realistic normalizations/edits that a ranker must never auto-apply here.
                    lower = strip_accents(token).lower().replace("ё", "е")
                    pair = ORTHOGRAPHIC_PAIRS[split].get(token) if category == "ambiguous_accent" else None
                    choices = ([pair[0]] if pair else []) + [lower, token.replace("_", " ").replace("-", " "), token[:-1], token + "s"]
                    candidates = candidates_for(token, choices, sid)
                    row = base(language, split, f"protected:{token.casefold()}", f"protected-context-{split}", prefix)
                    row.update(id=sid, task="spelling", cohort="protected", typed=token, candidates=candidates, expectedCandidate=0, category=category, noAuto=True, ambiguous=category == "ambiguous_accent", position="end", wordLength=len(token))
                    if pair:
                        row["orthographicPolicy"] = "preserve_ambiguous_diacritic_or_yo_e"
                        row["orthographicAlternative"], row["orthographicKind"] = pair
                    elif category == "ambiguous_accent":
                        # 'небо' has no valid ё counterpart. It is still a valid protected word.
                        row.update(category="protected_correct_word", ambiguous=False)
                    rows.append(row)
    return rows


PUNCT_PREFIXES = {
    "ru": {
        "calibration": ["Если начнётся дождь", "Когда закончится урок", "Хотя поезд опоздал", "Пока готовится ужин", "Если появится возможность", "Когда откроется выставка", "Хотя дорога была длинной", "Пока идёт совещание", "Если останется время", "Когда растает снег", "Поскольку автобус сломался", "Если погода улучшится", "Когда вернётся экскурсовод", "Хотя задача была сложной", "Пока сохнет краска", "Если придёт ответ", "Когда появится расписание", "Хотя зал был полон", "Пока работает мастер", "Если откроется дверь", "На столе были книги", "В саду росли яблони", "В магазине продаются тетради", "На выставке представлены картины", "Мы обсуждали цены", "Здесь жили инженеры", "В коробке лежали ручки", "Участники принесли плакаты", "На карте отмечены реки", "В списке указаны города", "План прост", "Причина понятна", "Решение принято", "Проверка закончена", "Работа завершена", "Я думаю", "Мы надеемся", "Вы знаете", "Она считает", "Он помнит"],
        "holdout": ["Если стихнет ветер", "Когда приедет врач", "Хотя мост был закрыт", "Пока собирается команда", "Если хватит топлива", "Когда вернётся капитан", "Хотя сцена была тесной", "Пока нагревается печь", "Если найдётся билет", "Когда созреют яблоки", "Поскольку лифт не работает", "Если появится электричество", "Когда уйдут посетители", "Хотя маршрут оказался трудным", "Пока кипит вода", "Если освободится столик", "Когда прозвучит сигнал", "Хотя соревнование затянулось", "Пока открыта касса", "Если удастся договориться", "В сумке были ключи", "На ферме выращивают тыквы", "В киоске продаются открытки", "На концерте звучали вальсы", "Они сравнивали размеры", "Там работали художники", "В корзине лежали груши", "Гости принесли подарки", "На схеме выделены станции", "В каталоге указаны музеи", "Вывод очевиден", "Порядок известен", "Ответ получен", "Поездка окончена", "Подготовка завершена", "Мне кажется", "Они уверены", "Ты понимаешь", "Редактор полагает", "Автор объясняет"]
    },
    "en": {
        "calibration": ["Although the train arrived late", "If the weather gets worse", "When the library opens tomorrow", "While the paint is drying", "Because the road was flooded", "Unless the forecast changes overnight", "After the committee reviews the plan", "Before the guests arrive tonight", "Although the room was crowded", "If the battery runs out", "When the concert finally ends", "While the children are playing", "Because the office closes early", "Unless the engine starts again", "After the letter reaches the editor", "Before the shop shuts today", "Although the deadline was extended", "If the bus is delayed", "When the snow melts completely", "While the guide checks the map", "The box contains pencils", "They sell notebooks", "The menu lists soup", "The garden has roses", "We invited teachers", "The report compares prices", "The shelf holds cameras", "They packed towels", "The map shows rivers", "The form asks for names", "The plan is simple", "The reason is clear", "The decision is final", "The inspection is over", "The work is complete", "I think", "We hope", "You know", "She believes", "He remembers"],
        "holdout": ["Even though the bridge was closed", "Provided that the wind drops tonight", "Once the surgeon returns tomorrow", "As the soup begins to simmer", "Since the elevator is broken", "Until the rescue crew arrives", "Whenever the captain gives the signal", "Whereas the earlier route was shorter", "Even though the stage was narrow", "Provided that enough fuel remains", "Once the match is finally over", "As the orchestra starts to rehearse", "Since the gate closes at sunset", "Until the replacement pump is fitted", "Whenever the referee blows the whistle", "Whereas the previous recipe used butter", "Even though the hall was empty", "Provided that a seat becomes available", "Once the apples have ripened", "As the visitors finish their tour", "The basket contains pears", "They offer postcards", "The program lists dances", "The orchard has plums", "We called musicians", "The survey compares distances", "The cupboard holds bowls", "They brought mittens", "The chart shows islands", "The catalog lists authors", "The conclusion is obvious", "The sequence is known", "The answer is ready", "The journey is over", "The preparation is complete", "It seems", "They expect", "You understand", "The reviewer assumes", "The author explains"]
    },
    "es": {
        "calibration": ["Si empieza a llover", "Cuando termine la clase", "Aunque el tren llegó tarde", "Mientras se prepara la cena", "Si surge una oportunidad", "Cuando abra la exposición", "Aunque el camino era largo", "Mientras dure la reunión", "Si queda tiempo", "Cuando se derrita la nieve", "Como el autobús se averió", "Si mejora el tiempo", "Cuando vuelva el guía", "Aunque la tarea era difícil", "Mientras se seca la pintura", "Si llega una respuesta", "Cuando aparezca el horario", "Aunque la sala estaba llena", "Mientras trabaja el mecánico", "Si se abre la puerta", "En la mesa había libros", "En el jardín crecían manzanos", "La tienda vende cuadernos", "La exposición muestra pinturas", "Hablamos de precios", "Aquí vivían ingenieros", "En la caja había lápices", "Los participantes trajeron carteles", "El mapa señala ríos", "La lista incluye ciudades", "El plan es sencillo", "La razón es clara", "La decisión está tomada", "La revisión ha terminado", "El trabajo está completo", "Yo pienso", "Esperamos", "Tú sabes", "Ella cree", "Él recuerda"],
        "holdout": ["Si se calma el viento", "Cuando llegue la médica", "Aunque el puente estaba cerrado", "Mientras se reúne el equipo", "Si alcanza el combustible", "Cuando regrese el capitán", "Aunque el escenario era pequeño", "Mientras se calienta el horno", "Si aparece una entrada", "Cuando maduren las manzanas", "Como el ascensor está averiado", "Si vuelve la electricidad", "Cuando salgan las visitas", "Aunque la ruta resultó difícil", "Mientras hierve el agua", "Si queda una mesa libre", "Cuando suene la señal", "Aunque la competición se alargó", "Mientras esté abierta la taquilla", "Si logramos un acuerdo", "En la bolsa había llaves", "La granja produce calabazas", "El quiosco vende postales", "En el concierto sonaron valses", "Compararon tamaños", "Allí trabajaban artistas", "En la cesta había peras", "Los invitados trajeron regalos", "El esquema destaca estaciones", "El catálogo enumera museos", "La conclusión es evidente", "El orden es conocido", "La respuesta está lista", "El viaje ha terminado", "La preparación está completa", "Me parece", "Ellos confían", "Tú entiendes", "La editora supone", "El autor explica"]
    }
}


def punctuation_rows() -> list[dict]:
    result = []
    subjects = {"ru": {"calibration": ["мы", "он", "она", "вы", "они"], "holdout": ["команда", "врач", "капитан", "повар", "художник"]}, "en": {"calibration": ["we", "he", "she", "you", "they"], "holdout": ["everyone", "someone", "nobody", "somebody", "anyone"]}, "es": {"calibration": ["nosotros", "él", "ella", "vosotros", "ellos"], "holdout": ["alguien", "nadie", "todos", "algunas", "algunos"]}}
    for language, splits in PUNCT_PREFIXES.items():
        for split, prefixes in splits.items():
            for index, prefix in enumerate(prefixes):
                for word_index, word in enumerate(subjects[language][split]):
                    boundaries = [" ", ", ", ": ", ". "]
                    # Initial subordinate clauses conventionally take a comma. Other
                    # fragment contexts genuinely underdetermine the next boundary.
                    ambiguous = index >= 20
                    expected = 1 if not ambiguous else 0
                    row = base(language, split, f"punct-subject-{split}-{word_index}", f"{split}-punct-{index:02}", prefix)
                    row.update(id=f"{language}-{split}-punct-{index:02}-{word_index}", task="punctuation", cohort="punctuation", currentWord=word, boundaries=boundaries, candidates=[b + (word[:1].upper() + word[1:] if b == ". " else word) for b in boundaries], expectedCandidate=expected, expectedBoundary=boundaries[expected], ambiguous=ambiguous, noAuto=True, category="subordinate_clause" if not ambiguous else "underdetermined_boundary", position="boundary")
                    result.append(row)
    return result


def write_corpus() -> None:
    seeds = json.loads((ROOT / "seeds.json").read_text(encoding="utf-8"))
    spelling = spelling_rows(seeds)
    acceptance_and_positions(spelling)
    punctuation = punctuation_rows()
    protected = protected_rows()
    # Keep all labels fixed before any model scoring. No score artifact is read here.
    all_rows = spelling + punctuation + protected
    from evaluate import FILES, canonical, digest, file_hash, validate
    summary = validate(all_rows)
    for filename in FILES:
        if filename == "protected-tokens.jsonl":
            rows = protected
        else:
            task, language = filename.removesuffix(".jsonl").split("-")
            rows = [row for row in (spelling if task == "spelling" else punctuation) if row["language"] == language]
        # Calibration first allows freezing before the first holdout request.
        rows.sort(key=lambda row: (row["split"] != "calibration", row["id"]))
        (ROOT / filename).write_bytes(b"".join(canonical(row) + b"\n" for row in rows))
    manifest = {"version": 2, "seedSha256": file_hash(ROOT / "seeds.json"), "nearbyWordsSha256": file_hash(ROOT / "nearby-words.json"), "generatorSha256": file_hash(Path(__file__)), "files": {filename: file_hash(ROOT / filename) for filename in FILES}, "summary": summary, "source": SOURCE, "collisionFilters": {lang: {"sha256": sha, "url": f"https://raw.githubusercontent.com/hermitdave/FrequencyWords/525f9b560de45753a5ea01069454e72e9aa541c6/content/2018/{lang}/{lang}_50k.txt", "license": "CC-BY-SA-4.0", "purpose": "veto known surface-form collisions; absence is not proof of typo"} for lang, sha in FILTER_DIGESTS.items()}, "independentSamples": False, "correctPanel": "700 correct rows per language/split are 100 lexical contexts with seven prepared-candidate perturbations each; 300 additional rows are protected token probes.", "splitPolicy": "Authored word families, templates and protected tokens assigned before scoring; spelling word families and punctuation subject families do not cross splits."}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    write_corpus()
