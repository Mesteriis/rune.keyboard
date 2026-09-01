# IME acceptance checklist

Green Gradle build не подтверждает реальное поведение клавиатуры. Перед релизом пройти этот список на эмуляторе и хотя бы одном физическом устройстве.

Debug-сборка содержит изолированный QA-экран, отсутствующий в release APK:

```bash
adb shell am start -n io.github.mesteriis.rune.keyboard/.qa.ImeQaActivity
```

На нём доступны обычное, `TYPE_NULL`, multiline с `NO_ENTER_ACTION`, custom-action с ID `0` и signed-decimal поля, а также локальная Unicode-заготовка `A😀` для проверки Backspace без clipboard.

## Установка и lifecycle

- приложение устанавливается без удаления другой клавиатуры;
- Rune появляется в системном списке IME, включается и выбирается;
- setup-экран корректно обновляет статус после возврата из Settings;
- смена светлой/тёмной темы, поворот, screen off/on и пересоздание процесса не приводят к crash/ANR;
- долгое нажатие `RU`/`EN` переключает IME или открывает picker.

## Ввод

- EN и RU: все буквы, `Ё` long press, Shift, double-tap Caps Lock;
- `TYPE_NULL`: латиница и кириллица доходят через raw key events;
- symbols, number, signed/decimal number, phone, date/time, email и URL;
- Space, punctuation, короткий и удерживаемый Backspace;
- удаление emoji/символа вне BMP не оставляет половину surrogate pair;
- Enter проверен для multiline, DONE, GO, NEXT, PREVIOUS, SEARCH и SEND;
- выделенный текст заменяется обычным вводом и полностью удаляется Backspace;
- password-поле не включает автокапитализацию и нигде не появляется в логах.

## Наблюдаемость без содержимого ввода

- отфильтрованный logcat не содержит введённые символы, password или surrounding text;
- нет `FATAL EXCEPTION`, ANR, повторных/пропущенных нажатий;
- быстрый набор и удержание Backspace не создают заметных пауз UI.

Рекомендуемая матрица: API 26, 30, 34, 37; обязательный ближайший smoke — доступный ARM64 AVD API 36. Физическая приёмка остаётся отдельным gate.
