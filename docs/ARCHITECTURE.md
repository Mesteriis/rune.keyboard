# Архитектура Rune Keyboard

## Цели

Rune оптимизируется под низкую задержку, предсказуемый lifecycle и минимальную поверхность риска. IME остаётся без сетевого и model-runtime кода. Отдельная подсистема локальной модели использует только системный `DownloadManager`, неперсистентный `JobScheduler` и приватный worker process; Compose, DI, WorkManager, coroutines, HTTP-клиентов, аналитики и базы данных нет.

## Поток ввода

```text
Android editor / EditorInfo
          │
          ▼
RuneInputMethodService ── lifecycle, InputConnection, settings snapshot, feedback
          │
          ├──── SpaceGestureDetector ── touches → tap / double tap / swipe / cursor
          │
          ▼
KeyboardReducer ───────── (state, action, editor context) → state + command
          │
          ├──────────────► EditorCommandExecutor → InputConnection
          │
          ▼
KeyboardLayoutProvider ── immutable KeySpec rows (+ LayoutOptions)
          │
          ▼
RuneKeyboardView ──────── accessible View keys, popups, touch/repeat handling
```

`RuneInputMethodService` остаётся оркестратором Android lifecycle. Переходы Shift/language/symbols, mapping Enter, арбитраж жестов пробела, правило двойного пробела и политика ускорения Backspace вынесены в чистый Kotlin и покрываются обычными JVM-тестами. Android-boundary сценарии проходят через debug-only `ImeQaActivity` в отдельном процессе `:qa_editor`, поэтому instrumentation проверяет настоящий Binder `InputConnection`, а не повторяет reducer-тесты. Рендер не пересобирается на каждом обычном символе: только при изменении состояния или контекста редактора.

Rune регистрирует один системный subtype на три языка. Переключение EN/RU/ES происходит внутри reducer по пользовательскому порядку из настроек, поэтому все раскладки доступны сразу после включения IME и не зависят от отдельно активированных Android-subtype.

## Жесты

Жесты живут только на управляющих клавишах. Пробел — отдельный `SpaceKeyView`, буквенные клавиши (`KeyboardKeyView`) физически не содержат жестового кода, поэтому glide typing невозможен не по настройке, а по устройству кода.

`SpaceGestureDetector` — одна state machine (`Idle`, `TapCandidate`, `Pressed`, `DoubleTapCandidate`, `LanguageSwipe`, `CursorMode`, `Cancelled`), которая арбитрирует тап, двойной тап, горизонтальный свайп смены языка и удержание для перемещения курсора. Она не читает время и не планирует таймеры: события и таймауты приходят снаружи, поэтому весь жестовый контракт тестируется на JVM.

Курсор двигается DPAD-событиями: редактор сам шагает по grapheme-кластерам, работает в `TYPE_NULL`-полях, и Rune при этом не читает текст.

## Границы пакетов

- `ime/model` — типизированные действия, состояние, контекст редактора, session policy, reducer и команды;
- `ime/gesture` — чистые правила жестов и расписание повтора Backspace;
- `ime/layout` — EN/RU/ES, две страницы символов, numeric/phone спецификации клавиш и таблицы long-press;
- `ime/ui` — доступные View-клавиши, popup preview и alternates, геометрия попапов;
- `ime/feedback` — политика haptic/звука и её исполнитель;
- `ime/editor` — единственная точка записи через `InputConnection`;
- `settings` — снапшот настроек, их хранение и экраны onboarding/настроек.
- `intelligence/model` — descriptor/snapshot/operation types и строгий manifest schema;
- `intelligence/delivery` — DownloadManager adapter, AtomicFile journal, private candidate install и SAF transfer.
- `intelligence/runtime` — self-test orchestration, атомарный active pointer и единственный rollback slot;
- `:runtime-llama` — pinned llama.cpp, opaque JNI handle и CPU-only `load/selfTest/cancel/unload`.

Подсистема модели не зависит от `ime/**`, а статический gate запрещает обратную зависимость. В 0.2 runtime предоставляет только `load/selfTest/cancel/unload`; typing API и общий `generate()` отсутствуют.

Платформенные `android.inputmethodservice.Keyboard` и `KeyboardView` не используются: они deprecated с API 29. View-подход выбран вместо Canvas, чтобы каждая клавиша сразу имела корректную focus/click/long-click семантику TalkBack без отдельного виртуального accessibility tree.

## Настройки и session state

Persistent (`SharedPreferences`, файл `keyboard_preferences`): включённые языки и их порядок, стартовый язык, высота по профилям экрана, отступы, цифровой ряд, тема, haptic, звук, preview, двойной пробел. Читаются кодеком `SettingsCodec` в immutable снапшот `KeyboardSettings`; любое некорректное значение честно падает в default, поэтому испорченный файл настроек не мешает клавиатуре запуститься.

Session (только в памяти): активный редактор, язык, Shift, слой, состояние жеста.

Снапшот читается один раз на старте сессии и обновляется через `OnSharedPreferenceChangeListener`, поэтому на пути нажатия клавиши нет I/O. Изменения, влияющие на внешний вид, пересоздают input view; остальные просто подменяют снапшот.

Профили размеров выбираются по `smallestScreenWidthDp` (граница 600dp совпадает с ресурсным квалификатором `sw600dp`), отдельно для внешнего и внутреннего экрана Fold и для каждой ориентации. Вендорные Fold API не используются.

Тема переопределяется через `createConfigurationContext` с форсированным `uiMode`: палитра живёт в квалификаторах `values`/`values-night`, и только конфигурационный контекст переразрешает её корректно.

## Fold и сессия редактора

Складывание и раскладывание — обычная смена конфигурации: фреймворк пересоздаёт input view и повторно вызывает `onStartInput(restarting = true)` для того же редактора. `KeyboardSessionPolicy` в этом случае сохраняет предыдущее состояние, поэтому Shift, Caps Lock, слой и язык не теряются. Единственная точка сброса — `onStartInput(restarting = false)`; `onFinishInput` состояние не сбрасывает, потому что некоторые прошивки перемешивают его с restarting-стартом во время fold-перехода.

## Приватность и безопасность

- manifest объявляет ровно `android.permission.INTERNET`; сеть используется только после явного скачивания модели через системный DownloadManager;
- введённый текст не передаётся в delivery/runtime, не отправляется и не логируется;
- `privacyGateRelease` проверяет точный permission set, отключённые backup/cleartext и отсутствие логирования;
- service экспортирован только с signature permission `android.permission.BIND_INPUT_METHOD`;
- backup и cleartext traffic отключены;
- вибрация реализована через `View.performHapticFeedback`, поэтому Rune не просит `android.permission.VIBRATE`; интенсивности выражены платформенными haptic-константами, а не амплитудами;
- `EditorContext.inputPolicy` (`NORMAL`/`SENSITIVE`) — единая точка, которую обязаны спрашивать компоненты, работающие с текстом. `SENSITIVE` включается для password-полей и `IME_FLAG_NO_PERSONALIZED_LEARNING`; он, в частности, выключает popup preview. Значение `INCOGNITO` появится вместе с первой обучающейся подсистемой — пустую заглушку заранее не вводим;
- история, composing buffer, clipboard, аналитика и crash SDK отсутствуют.

### Осознанное расширение инварианта чтения текста

До Rune 0.1 клавиатура читала из редактора только `getCursorCapsMode` и числовые границы selection. Правило двойного пробела (SPACE-002) и атомарное удаление logical character требуют минимального surrounding-text контекста. Rune разрешает два строго ограниченных вида эфемерного чтения:

- `getTextBeforeCursor(2, 0)` — только в момент второго тапа по пробелу и при последующем Backspace-откате, только в plain-text полях;
- `getTextBeforeCursor(64, 0)` — только непосредственно во время Backspace в non-sensitive поле. Android ICU и ограниченный compatibility scan находят предыдущий grapheme cluster, после чего удаление передаётся редактору числом code points;
- selection удаляется целиком через `commitText("", 1)` без чтения выделенного или surrounding text;
- password и `IME_FLAG_NO_PERSONALIZED_LEARNING` никогда не читаются: там Backspace удаляет один code point; `TYPE_NULL` получает `KEYCODE_DEL`;
- прочитанное существует только в стеке одной команды, не сохраняется, не логируется, не попадает в trace и не передаётся другим компонентам.

Compatibility scan покрывает ZWJ, emoji modifiers, regional-indicator flags, keycaps, variation selectors и combining marks в пределах тех же 64 UTF-16 units. Патологический cluster длиннее границы чтения остаётся документированным ограничением: Rune не расширяет наблюдаемое окно и использует безопасный fallback редактора. Rune-owned composing state отсутствует, поэтому Fold-gate проверяет committed text, cursor/selection, язык, слой и Shift/Caps без phantom composition.

Direct Boot в 0.1 выключен: его нельзя честно включить без device-protected preferences и отдельной lockscreen-проверки после перезагрузки.

## Доставка, self-test и активация

External app-specific каталог — только недоверенный staging системного `DownloadManager`. Worker в процессе `:model_worker` открывает результат через `openDownloadedFile()`, одним ограниченным проходом копирует его в private `.installing`, считает SHA-256, делает `fsync` и только затем проверяет GGUF v3, `qwen3` и `file_type=15`. Кандидат публикуется атомарным rename в `noBackupFilesDir`; старый active при этом не скрывается.

Pinned JNI runtime загружает candidate с отключённым logger, выполняет warm-up и не более четырёх greedy tokens при `n_ctx=256`/`n_batch=64`, проверяет непустой UTF-8 и не возвращает output. После успеха candidate атомарно становится versioned active, прежний active — единственным rollback. Opaque handle владеет model через RAII; глобальные model/context pointers отсутствуют. Отмена соединена с load-progress и decode-abort callbacks.

## Производительность

- IME остаётся в основном процессе; install/self-test выполняются worker service в `:model_worker`;
- нет runtime-зависимостей кроме Kotlin stdlib, встроенной AGP;
- нет I/O на пути нажатия клавиши;
- один основной `InputConnection` вызов на действие (двойной пробел — один batch edit);
- popup-окна создаются один раз и переиспользуются, на `ACTION_DOWN` ничего не инфлейтится;
- повтор удаления отменяется на `UP`, `CANCEL`, уходе пальца и detach View; жестовое состояние возвращается в `Idle` через общий `cancelActiveTouches`;
- R8 и resource shrinking включены для release.

Build type `profile` повторяет release minification/shrinking, подписывается debug-ключом, имеет отдельный application ID suffix, остаётся `debuggable=false` и разрешает shell profiling через `<profileable>`. Perfetto-секции имеют только константные content-free имена `Rune#…`; текст редактора в них не попадает. Аллокации снимаются отдельно на debuggable debug build.
