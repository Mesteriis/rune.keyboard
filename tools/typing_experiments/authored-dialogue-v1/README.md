---
language:
- ru
license: cc-by-4.0
task_categories:
- conversational
- text-generation
task_ids:
- dialogue-modeling
tags:
- russian
- everyday
- dialogues
- spoken-language
- colloquial
pretty_name: Russian Everyday Dialogues
size_categories:
- n<1K
---

# Russian Everyday Dialogues / Русские повседневные диалоги

A dataset of 20 natural conversational Russian dialogues covering everyday situations.
Создан носителем языка с 18-летним опытом работы в международной среде.

## Dataset Description

This dataset contains short, natural Russian dialogues typical of everyday urban life in Russia.
Each example reflects authentic spoken language patterns, not formal or literary Russian.

### Situations covered
- 🛒 **Магазин / Shopping** — 7 dialogues
- 🚌 **Транспорт / Public Transport** — 6 dialogues
- ☕ **Кафе / Café** — 7 dialogues

## Dataset Structure

Each record contains:

| Field | Type | Description |
|---|---|---|
| `id` | int | Unique identifier |
| `situation` | string | Context: магазин / транспорт / кафе |
| `user` | string | Human utterance |
| `assistant` | string | Natural response |
| `register` | string | нейтральный / разговорный |
| `tags` | list | Semantic tags |

### Example

```json
{
  "id": 1,
  "situation": "магазин",
  "user": "Извините, а где у вас молоко?",
  "assistant": "Молоко в молочном отделе, это в конце второго ряда, слева от йогуртов.",
  "register": "нейтральный",
  "tags": ["магазин", "навигация", "вежливое обращение"]
}
```

## Use Cases

- Training conversational AI models in Russian
- Fine-tuning language models for spoken Russian
- Russian language learning applications
- Dialogue system development

## Data Collection

Dialogues were written by a native Russian speaker with extensive experience
in international business communication (Russian/German/English).
All dialogues reflect natural, contemporary spoken Russian.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
You are free to share and adapt this dataset with attribution.

## Citation

```
@dataset{russian_everyday_dialogues_2025,
  title={Russian Everyday Dialogues},
  author={Myskina, Ekaterina},
  year={2025},
  publisher={Hugging Face},
  url={https://huggingface.co/datasets/kukunechka/russian-everyday-dialogues}
}
```
