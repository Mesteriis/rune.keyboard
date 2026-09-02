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
          ├──────────────► TypingSessionController → composing / RAM context
          │                                      │
          ├──────────────► EditorCommandExecutor → InputConnection
          │
          ▼
KeyboardLayoutProvider ── immutable KeySpec rows (+ LayoutOptions)
          │
          ▼
RuneKeyboardView ──────── accessible View keys, popups, touch/repeat handling
```

`RuneInputMethodService` остаётся оркестратором Android lifecycle. Переходы Shift/language/symbols, mapping Enter, арбитраж жестов пробела, typing-owned правило двойного пробела и политика ускорения Backspace вынесены в чистый Kotlin и покрываются обычными JVM-тестами. Android-boundary сценарии проходят через debug-only `ImeQaActivity` в отдельном процессе `:qa_editor`, поэтому instrumentation проверяет настоящий Binder `InputConnection`, а не повторяет reducer-тесты. Рендер не пересобирается на каждом обычном символе: только при изменении состояния или контекста редактора.

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
- `smarttyping/session` — отдельный владелец composing, session/revision и ограниченного контекста; не хранит визуальное состояние;
- `settings` — снапшот настроек, их хранение и экраны onboarding/настроек.
- `intelligence/model` — descriptor/snapshot/operation types и строгий manifest schema;
- `intelligence/delivery` — DownloadManager adapter, AtomicFile journal, private candidate install и SAF transfer.
- `intelligence/runtime` — self-test orchestration, атомарный active pointer и единственный rollback slot;
- `intelligence/storage` — read-only active-model resolver, pointer codec и общий межпроцессный operation lock;
- `intelligence/ipc` — bounded request и числовой reply, oneway AIDL;
- `intelligence/client` — main-thread binding lifecycle, session/revision/request guards и cancellation;
- `intelligence/inference` — private scoring service, один worker и узкий native adapter;
- `:runtime-llama` — pinned llama.cpp, opaque JNI handle и CPU-only `load/selfTest/scoreCandidates/cancel/unload`.

Подсистема модели не зависит от `ime/**`. Статический gate разрешает IME только scoring client interface и bounded value contracts; delivery, activation, storage, JNI и network недоступны транзитивно. Runtime предоставляет `load/selfTest/cancel/unload` и bounded `scoreCandidates`; IME ещё не вызывает модель. Общего `generate()` нет.

Scoring получает 1–8 продолжений с уникальными числовыми IDs. Kotlin и JNI
независимо проверяют строгий UTF-8 и byte limits; tokenizer дополнительно
проверяет 192/64 standalone tokens и 256 tokens полной строки с допустимым BOS.
Оценка строится по полной строке `prefix + continuation`, общему token prefix
и divergent span. Последовательный teacher forcing очищает KV между вариантами;
возвращаются только IDs, суммы log probability, counts, timing и stable error.
Нулевой divergent span отклоняет весь набор. EOS не добавляется.

CMake архивирует чистый pinned llama.cpp в build directory и применяет туда
проверенный patch; gitlink не меняется. Новый совместимый tokenizer API имеет
callback/user-data на вызов и проверяет отмену внутри Unicode preparation,
QWEN2 pre-split и BPE loops. Runtime отклоняет неподдерживаемые tokenizer types.
Отдельный request cancellation predicate проверяется после сброса native flag
при допуске load/score на worker: отмена до постановки в очередь не теряется.
После допуска `cancelCurrentOperation` непосредственно выставляет atomic flag.
Периодического polling для этой гарантии нет.

Платформенные `android.inputmethodservice.Keyboard` и `KeyboardView` не используются: они deprecated с API 29. View-подход выбран вместо Canvas, чтобы каждая клавиша сразу имела корректную focus/click/long-click семантику TalkBack без отдельного виртуального accessibility tree.

## Приватный inference process

`ModelInferenceService` работает в `:model_runtime`: `exported=false`, без
intent-filter, foreground service и отдельного permission. Оба направления
AIDL — oneway. Request содержит bounded prefix/continuations и session,
revision, request, candidate IDs; callback содержит только эти IDs, числовые
scores/counts, duration и код. Parcel проверяет длины до выделения массивов.

Один serial worker держит максимум один active и один заменяющий pending request.
Отмена сначала отмечает request token, затем вызывает native cancellation;
Binder не ставит cancel в очередь scoring. Idle unload происходит через 60 секунд
без работы; critical memory pressure, unbind и invalidation отменяют работу и
запрашивают unload. Закрытие service не ждёт native teardown на main thread.

Resolver читает active pointer и manifest под общим operation lock с install
worker. Load удерживает read lock; scoring его освобождает. После scoring
identity проверяется снова под lock. Это точка проверки версии, а не обещание
атомарности с будущей установкой между проверкой и доставкой callback.
Обычная отмена запроса отбрасывает ответ, сохраняя полностью загруженную модель,
если эта проверка подтвердила ту же identity. Смена/удаление модели, ошибка
проверки и неполная загрузка требуют cleanup. Явная worker invalidation
всегда запрашивает отдельный serial unload, даже при неизменных метаданных.
Три FileObserver следят за root, versions и активной версией; регистрация
подтверждается read-only OPEN handshake. Отсутствующая регистрация запрещает load.
Каждая регистрация имеет отдельную identity; close сначала делает её неактивной,
затем останавливает native watches. Проверка identity и доставка invalidation
синхронизированы, поэтому поздний callback закрытой регистрации не отменяет новую.
Ожидание OPEN handshake выполняется вне этой блокировки. Неизвестные события
текущей регистрации по-прежнему вызывают invalidation.
Resolver не выполняет AtomicFile recovery, не создаёт storage и не зависит от
delivery; mutable activation остаётся у install worker.

Client принимает только актуальный session/revision/request/candidate набор и
текущую revision composition. Каждый callback дополнительно привязан к generation
подключения. Повторный attach той же session/demand ничего не отменяет и не
переподключает; OFF/ON и временный null detach сохраняют request watermark
последней положительной session. Разные реальные сессии получают разные IDs.

После смерти Binder transport становится unavailable. В одной непрерывной demand
эпохе разрешены initial bind и максимум две попытки rebind через 1 и 2 секунды;
успешное подключение, revision и повторный attach не пополняют число попыток.
Существует не более одного retry timer; старые timers/connections не изменяют
новую generation. Старый payload не воспроизводится. Завершение/смена session
снимает retry и binding. Close окончателен и идемпотентен. Availability callback
сообщает только переходы транспортного состояния, а не готовность/загрузку модели.

Чистый `ModelDemand` объединяет cached readiness, активность/видимость допустимой
NORMAL text session и наличие включённого реализованного модельного потребителя.
Без READY или такого потребителя спрос отсутствует. Словарные подсказки,
видимость полоски, механика и double-space сами по себе не являются модельным
спросом; spelling/contextual потребители независимы. В текущем срезе IME ещё
не создаёт client: readiness monitor, consumer scheduling, process-CPU budget и
model-assisted ranking остаются последующей интеграцией. Конечное число bind
попыток не доказывает ограничение inference CPU или экономию батареи.

`imeIntelligenceBoundary` проверяет также client, IPC, storage и inference с
транзитивными зависимостями. Отрицательные fixtures подтверждают обнаружение
network, delivery, JNI, logging, filesystem/payload persistence и обходов
через helper. Native разрешён только adapter; URI разрешён только pure manifest
parser. Это source-level gate, дополняющий dependency и manifest проверки.

## Настройки и session state

Persistent (`SharedPreferences`, файл `keyboard_preferences`): включённые языки и их порядок, стартовый язык, высота по профилям экрана, отступы, цифровой ряд, тема, haptic, звук, preview, двойной пробел и независимые предпочтения Smart Typing. `SettingsCodec` читает их в immutable снапшот `KeyboardSettings`. Схема 3 добавляет `autocorrectionMode` (default `HIGH_CONFIDENCE`), `mechanicalPunctuation` (true), `contextualPunctuationMode` (`SUGGESTIONS`) и `candidateStrip` (true). Сохранённое предпочтение не зависит от готовности модели и само по себе не разрешает автозамену до прохождения quality gates. Экран настроек показывает независимые переключатели и режимы, сохраняя выбранное предпочтение отдельно от доступности. В текущей версии `SUGGESTIONS` и `HIGH_CONFIDENCE` дают только ручные словарные подсказки; UI явно сообщает о недоступности автоматической замены и контекстной пунктуации.

Отсутствующие поля старой схемы 1/2 или нового хранилища получают defaults; отсутствующие поля схемы 3 и повреждённые отдельные значения получают `OFF`/false. Это относится и к некорректному `doubleSpacePeriod`. Независимые корректные настройки сохраняются. Неизвестная или повреждённая версия схемы отключает эффективные Smart Typing preferences; обычные визуальные настройки сохраняют прежние defaults. Чтение ничего не записывает. Любой существующий writer мигрирует поддерживаемое хранилище одним `SharedPreferences.Editor` вместе с явным изменением, сериализуя snapshot и запись между владельцами одного `SharedPreferences`. Более новая числовая версия и остальные её исходные поля не понижаются и не нормализуются: writer сохраняет только явно выбранный ключ, а Smart Typing остаётся выключенным до совместимого reader. Текст редактора в preferences не попадает.

`AutocorrectionMode.OFF` отменяет словарные запросы и оставляет только Original при включённой строке. Скрытая строка не запрашивает словарные кандидаты, поскольку сейчас их единственный потребитель — явный выбор пользователем. Изменение режима или видимости инвалидирует pending requests и IDs, сохраняя composition и Undo механической пунктуации. Поздний ответ и отпускание ранее нажатой подсказки повторно проверяют текущую policy. Включение настройки, готовность словаря или перерисовка не запускают поиск без следующего явного изменения слова. Механика, double-space и сохранённое предпочтение контекстной пунктуации независимы; настройки сами по себе не вызывают model binding.

Session (только в памяти): активный редактор, язык, Shift, слой, состояние жеста; отдельно — composing word с leading boundary и текст, введённый через Rune в текущей сессии. Контекст ограничен 2048 UTF-16 units и 1024 code points с обрезкой по ICU grapheme boundaries. Он не заполняется из чтений редактора.

Снапшот читается один раз на старте сессии и обновляется через `OnSharedPreferenceChangeListener`, поэтому на пути нажатия клавиши нет I/O. Изменения темы, геометрии и preview пересоздают input view; изменение списка или порядка языков перерисовывает клавиши. Остальные настройки обновляют cached policy и полоску кандидатов, сохраняя экземпляры клавиш и активное касание. Для них не вызывается `renderKeyboard`: этот путь перестраивает клавиши, в том числе отложенно после отпускания пальца.

Профили размеров выбираются по `smallestScreenWidthDp` (граница 600dp совпадает с ресурсным квалификатором `sw600dp`), отдельно для внешнего и внутреннего экрана Fold и для каждой ориентации. Вендорные Fold API не используются.

Тема переопределяется через `createConfigurationContext` с форсированным `uiMode`: палитра живёт в квалификаторах `values`/`values-night`, и только конфигурационный контекст переразрешает её корректно.

## Fold и сессия редактора

Складывание и раскладывание — обычная смена конфигурации: фреймворк пересоздаёт input view и повторно вызывает `onStartInput(restarting = true)` для того же редактора. `KeyboardSessionPolicy` в этом случае сохраняет предыдущее состояние, поэтому Shift, Caps Lock, слой и язык не теряются. Единственная точка сброса — `onStartInput(restarting = false)`; `onFinishInput` состояние не сбрасывает, потому что некоторые прошивки перемешивают его с restarting-стартом во время fold-перехода.

Визуальное состояние и typing-сессия имеют разные lifecycle. При завершении input/view Rune завершает принадлежащий ей span и уничтожает контекст. Restart начинает новую typing-сессию; предыдущий буфер не отправляется повторно. Буквы обновляют текущий composing span. Пробел завершает слово и создаёт видимую pending boundary, которую следующая буква расширяет до `" <word>"`. Enter, язык, слой и начало cursor mode завершают composition. После операции с неизвестной позицией курсора composing ждёт selection callback; plain ввод остаётся доступным.

Подтверждения ожидаемых selection/span имеют ограниченную числовую очередь. Внешняя selection очищает контекст; потерянный или отвергнутый composing span отключает Smart Typing до следующей editor session. Rune не читает текст для проверки ownership и не восстанавливает потерянный буфер. Одна typing-owned Undo-транзакция хранит предыдущий собственный suffix; первый Backspace восстанавливает его как composition, следующее текстовое действие закрывает транзакцию. В KeyboardState отдельного double-space Undo нет. Редакторы, молча отбрасывающие span без callback, остаются явной границей совместимости.

Механическая пунктуация использует только принятый Rune suffix (до 256 code points)
и текущий собственный composing span. После завершённого слова ASCII-пробелы и
`, . ? ! : ;` остаются pending boundary. Planner предлагает одну замену этого
span до записи очередного символа: исправление пробелов, допустимого повтора
знака и первой заглавной буквы объединяется в одну immediate Undo-транзакцию.
Undo возвращает исходный результат текущего ввода; double-space сохраняет
своё правило восстановления первого пробела. Отказ composing не вызывает
повторной отправки текста. Неоднозначные hostname/code формы и многоточия
сохраняются; две точки исправляются только после собственного пробела и начала
обычного слова, если обе точки ещё входят в живой span.

Механика и double-space имеют независимые cached settings. Явное выключение
Shift подавляет автоматическую капитализацию следующего текстового действия;
это состояние принадлежит KeyboardState. Обычный NORMAL-only caps lookup
сохранён, дополнительных чтений текста редактора нет. Удержание запятой
открывает `? ! : ;` без смены слоя и потери typing context.

## Полоса кандидатов

`RuneKeyboardView` содержит постоянные `CandidateStripView` и контейнер клавиш.
Обновление кандидатов меняет только три постоянные ячейки полосы, сохраняя
экземпляры клавиш, активное касание, popup и Shift. Пустая включённая полоса
сохраняет высоту; скрытая очищает текст, accessibility descriptions и selection.
Каждый непустой набор содержит Original, а выбранный элемент передаёт selected
state и подписанное TalkBack action. Если данные ячейки изменились между Down
и Up, старое касание отменяется.

Продукт показывает Original и доступные локальные словарные варианты текущего
composing word. Их IDs привязаны к session/revision/request; устаревший tap
отклоняется. Явный выбор варианта заменяет только текущий собственный span;
Original восстанавливает введённое слово после ручного выбора альтернативы.
Словари открываются вне main thread, результаты проходят проверку актуальности.
Автозамена и contextual punctuation ещё не включены. В sensitive/raw input,
на других слоях и после потери composing ownership полоса скрыта.

## Приватность и безопасность

- manifest объявляет ровно `android.permission.INTERNET`; сеть используется только после явного скачивания модели через системный DownloadManager;
- введённый текст не передаётся в delivery/activation; bounded scoring contract допускает эфемерную передачу Rune-owned контекста в приватный процесс того же приложения, без сети, логов или сохранения; IME consumer ещё не подключён;
- `privacyGateRelease` проверяет точный permission set, отключённые backup/cleartext и отсутствие логирования;
- IME service экспортирован только с signature permission `android.permission.BIND_INPUT_METHOD`; interactive inference service приватный и отдельно проверяет UID caller;
- backup и cleartext traffic отключены;
- вибрация реализована через `View.performHapticFeedback`, поэтому Rune не просит `android.permission.VIBRATE`; интенсивности выражены платформенными haptic-константами, а не амплитудами;
- `EditorContext.inputPolicy` (`NORMAL`/`SENSITIVE`) — единая точка, которую обязаны спрашивать компоненты, работающие с текстом. `SENSITIVE` включается для password-полей и `IME_FLAG_NO_PERSONALIZED_LEARNING`; он, в частности, выключает popup preview. Значение `INCOGNITO` появится вместе с первой обучающейся подсистемой — пустую заглушку заранее не вводим;
- история ввода на диске, clipboard, аналитика и crash SDK отсутствуют; composing и текущий Rune-owned контекст существуют только в RAM;
- sensitive/raw редакторы не создают composing/context; automatic Caps и double-space также требуют `InputPolicy.NORMAL`.

### Осознанное расширение инварианта чтения текста

До введения правила двойного пробела и Unicode-safe Backspace клавиатура читала из редактора только `getCursorCapsMode` и числовые границы selection. Правило двойного пробела (SPACE-002) и атомарное удаление logical character требуют минимального surrounding-text контекста. Rune разрешает ограниченное эфемерное чтение для удаления вне собственной composition:

- double-space и его Undo используют собственный pending span и Rune-owned RAM-контекст, без чтений редактора;
- `getTextBeforeCursor(64, 0)` — только непосредственно во время Backspace в non-sensitive поле. Android ICU и ограниченный compatibility scan находят предыдущий grapheme cluster, после чего удаление передаётся редактору числом code points;
- selection удаляется целиком через `commitText("", 1)` без чтения выделенного или surrounding text;
- password и `IME_FLAG_NO_PERSONALIZED_LEARNING` никогда не читаются: там Backspace удаляет один code point; `TYPE_NULL` получает `KEYCODE_DEL`;
- прочитанное существует только в стеке одной команды, не сохраняется, не логируется, не попадает в trace и не передаётся другим компонентам.

Compatibility scan покрывает ZWJ, emoji modifiers, regional-indicator flags, keycaps, variation selectors и combining marks в пределах тех же 64 UTF-16 units. Патологический cluster длиннее границы чтения остаётся документированным ограничением: Rune не расширяет наблюдаемое окно и использует безопасный fallback редактора. Внутри Rune-owned composition Backspace удаляет последний grapheme из собственного буфера без чтения редактора. Fold-gate должен дополнительно проверять сохранность отображённого текста без повторного применения старой composition.

Direct Boot в 0.2 выключен: его нельзя честно включить без device-protected preferences и отдельной lockscreen-проверки после перезагрузки.

## Доставка, self-test и активация

External app-specific каталог — только недоверенный staging системного `DownloadManager`. Worker в процессе `:model_worker` открывает результат через `openDownloadedFile()`, одним ограниченным проходом копирует его в private `.installing`, считает SHA-256, делает `fsync` и только затем проверяет GGUF v3, `qwen3` и `file_type=15`. Кандидат публикуется атомарным rename в `noBackupFilesDir`; старый active при этом не скрывается.

Pinned JNI runtime загружает candidate с отключённым logger, выполняет warm-up и не более четырёх greedy tokens при `n_ctx=256`/`n_batch=64`, проверяет непустой UTF-8 и не возвращает output. После успеха candidate атомарно становится versioned active, прежний active — единственным rollback. Opaque handle владеет model через RAII; глобальные model/context pointers отсутствуют. Отмена соединена с load-progress и decode-abort callbacks.

Единый APK и `:runtime-llama` собираются только для `arm64-v8a` и `x86_64`; 32-разрядные ABI не поддерживаются.

## Производительность

- IME остаётся в основном процессе; install/self-test выполняются в `:model_worker`, interactive scoring — в отдельном `:model_runtime`;
- нет runtime-зависимостей кроме Kotlin stdlib, встроенной AGP;
- нет I/O на пути нажатия клавиши;
- обновление слова — один `setComposingText`; граница слова и удаление последнего composing grapheme дополнительно завершают span (двойной пробел и его Undo — замена собственного span);
- popup-окна создаются один раз и переиспользуются, на `ACTION_DOWN` ничего не инфлейтится;
- повтор удаления отменяется на `UP`, `CANCEL`, уходе пальца и detach View; жестовое состояние возвращается в `Idle` через общий `cancelActiveTouches`;
- R8 и resource shrinking включены для release.

Build type `profile` повторяет release minification/shrinking, подписывается debug-ключом, имеет отдельный application ID suffix, остаётся `debuggable=false` и разрешает shell profiling через `<profileable>`. Perfetto-секции имеют только константные content-free имена `Rune#…`; текст редактора в них не попадает. Аллокации снимаются отдельно на debuggable debug build.
