"""Retain exact dictionary whitespace witnesses without changing lexical transforms."""
from __future__ import annotations

import json
from pipeline_config import build_root, verify_inputs


def main() -> None:
    root = build_root()
    verify_inputs(root)
    for language, stem in [('ru', 'ru_RU/ru_RU'), ('es', 'es/es_ES')]:
        source = root/f'sources/libreoffice/{stem}.dic'
        rows = [{'line': number, 'source': line, 'trimmed': line.strip()}
                for number, line in enumerate(source.read_text(encoding='utf-8').splitlines(), 1)
                if line != line.strip()]
        (root/f'reports/{language}-whitespace-source-rows.json').write_text(
            json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
