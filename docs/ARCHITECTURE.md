# Архитектура Rune Keyboard

## Цели

Rune оптимизируется под низкую задержку, предсказуемый lifecycle и минимальную поверхность риска. Это один Android-модуль без сети, Compose, DI-контейнера, базы данных, фоновых задач и сторонних runtime-зависимостей.

## Поток ввода

```text
Android editor / EditorInfo
          │
          ▼
RuneInputMethodService ── lifecycle, InputConnection, system feedback
          │
          ▼
KeyboardReducer ───────── (state, action, editor context) → state + command
          │
          ├──────────────► EditorCommandExecutor → InputConnection
          │
          ▼
KeyboardLayoutProvider ── immutable KeySpec rows
          │
          ▼
RuneKeyboardView ──────── accessible View keys and touch/repeat handling
```

`RuneInputMethodService` остаётся оркестратором Android lifecycle. Переходы Shift/language/symbols и mapping Enter вынесены в синхронный reducer и покрываются обычными JVM-тестами. Рендер не пересобирается на каждом обычном символе: только при изменении состояния или контекста редактора.

Rune регистрирует один двуязычный системный subtype. Переключение EN/RU происходит внутри reducer и сохраняется как несекретная preference, поэтому обе раскладки доступны сразу после включения IME и не зависят от отдельно активированных Android-subtype.

## Границы пакетов

- `ime/model` — типизированные действия, состояние, контекст редактора, reducer и команды;
- `ime/layout` — EN/RU/symbol/numeric спецификации клавиш;
- `ime/ui` — доступные View-клавиши, long press и Backspace repeat;
- `ime/editor` — единственная точка записи через `InputConnection`;
- `settings` — launcher-экран для системного enable/select flow.

Платформенные `android.inputmethodservice.Keyboard` и `KeyboardView` не используются: они deprecated с API 29. View-подход выбран вместо Canvas, чтобы каждая клавиша сразу имела корректную focus/click/long-click семантику TalkBack без отдельного виртуального accessibility tree.

## Приватность и безопасность

- manifest не объявляет разрешения пользователя и не содержит `INTERNET`;
- service экспортирован только с signature permission `android.permission.BIND_INPUT_METHOD`;
- backup и cleartext traffic отключены;
- используются только числовые границы selection из `EditorInfo`/`onUpdateSelection` и вычисленный
  из них факт наличия выделения; содержимое selection и surrounding text не читается и не логируется;
- Backspace опирается на этот факт и `deleteSurroundingTextInCodePoints`, не извлекая текст редактора;
- выбранный язык хранится как единственная несекретная preference; история ввода не сохраняется;
- история, composing buffer, clipboard, аналитика и crash SDK отсутствуют.

Direct Boot в MVP выключен: его нельзя честно включить без device-protected preferences и отдельной lockscreen-проверки после перезагрузки.

## Производительность

- один процесс и один модуль;
- нет runtime-зависимостей кроме Kotlin stdlib, встроенной AGP;
- нет I/O на пути нажатия клавиши;
- один основной `InputConnection` вызов на действие;
- повтор удаления отменяется на `UP`, `CANCEL`, уходе пальца и detach View;
- R8 и resource shrinking включены для release.
