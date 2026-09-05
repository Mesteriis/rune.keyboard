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

Первый подходящий ввод Rune с cached Ready и qualified runtime подключает
service ещё до готовности словаря/паузы scoring. Worker готовит только веса:
`ScoringEngine.prepare` не получает текст, candidates или request. Отмена/замена
слова освобождает pending payload, но не прерывает эту загрузку. Закрытие сессии,
смена модели, memory pressure и watchdog отменяют подготовку и выгружают runtime.
Успешная подготовка без scoring также выгружается после 60 секунд простоя;
контекст llama по-прежнему создаётся лениво при первом score. Валидное слово не
создаёт scoring demand и не разрывает уже подходящий binding. Render/Ready
callbacks сами прогрев не запускают.

`ProcessModelDuty` хранит числовой бюджет на время жизни процесса, отдельно от
Service. Единственная lease остаётся у worker до завершения serial cleanup;
новый Service не может параллельно войти в native runtime. Пересоздание Service
и смена session не сбрасывают расход. Учитывается CPU всего процесса через
`Process.getElapsedCpuTime`, включая загрузку, ошибки и обязательный cleanup.
Некорректные часы запрещают модельную работу до перезапуска процесса.

Экспериментальный профиль: ёмкость 8000 CPU-ms, пополнение 8000 CPU-ms за 60 s,
вход при остатке не менее 7500 CPU-ms, возраст очереди и активный deadline по
3000 ms. Проверки идут только во время работы/cleanup, с паузой 50 ms после
предыдущей проверки (`scheduleWithFixedDelay`), без догоняющих вызовов после
заморозки процесса. Отказ немедленно возвращает UNAVAILABLE без retry;
он не продлевает idle unload. Cleanup выполняется даже при отрицательном
бюджете. Это sampled cancellation policy: cooperative native cancellation
может превысить бюджет, и этот расход остаётся долгом. Числа пока не являются
измеренным батарейным бюджетом или release qualification.

Подготовка весов и первый score делят один admission и исходный deadline
3000 ms. Числовой reservation не содержит payload, не возвращает потраченный CPU
и не продлевает deadline; после первого score либо истечения окна снова нужен
обычный порог 7500 CPU-ms. Неудачная подготовка возвращает ожидающему запросу
исходный числовой код и не перезапускает загрузку для того же слова. Пока между
прогревом и score нет работы, watchdog timer не работает. Этот механизм не
открывает `ModelRuntimeQualification` без физических измерений.

После измерений 2026-09-05 qualified runtime для текущего Rune Text включён:
release p95 четырёх вариантов EN75/RU260/ES173 ms; настоящий service из 120
запросов за минуту выполнил 13 и отклонил 107, потратив 7,85 CPU-seconds.
После idle unload освобождены страницы модели. Это квалификация runtime под
существующим ограничителем, а не полная release/battery acceptance. Доказательства
и оставшиеся границы: `docs/acceptance/2026-09-05-smart-typing-0.3-fold-qualified.md`.

Critical/background/low-memory сначала блокируют новые admissions, затем
отменяют работу и запрашивают выгрузку. Только последующий настоящий
unbind/bind снимает блокировку, сохраняя долг; revision, submit и invalidation
её не снимают. Проверки таймера отсутствуют в idle/unloaded состоянии.
`onUnbind` возвращает true: если Service остаётся жив, Android вызывает
`onRebind`, который восстанавливает worker binding. Повторный `onBind` для
уже выданного Binder не предполагается; сервис остаётся только bound.

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

Client принимает только последний session/revision/request/candidate набор,
который typing owner подтверждает как актуальный. Обычно это текущая revision
composition. Для обычного пробела в квалифицированном режиме AutoReplace owner
может сохранить один уже запущенный spelling-запрос; ещё не сработавшая пауза
отправляет его один раз без ожидания результата. Пробел коммитится сразу. В течение
250 мс после него разрешена замена только прежнего полного Rune-owned слова и
его пробела при неизменных caret, suffix, session, новой revision и настройках.
Исходные IDs запроса не меняются. Следующее текстовое действие, Original, cursor,
смена поля/настроек или истечение окна отменяют владение. Deadline проверяется и
при получении callback, даже если main-thread timer задержался. Успешная замена
использует guarded editor batch и единую Undo-транзакцию; нет нового editor
readback, повторной отправки запроса или дополнительного CPU allowance. Это окно
реакции интерфейса, а не квалификация скорости/энергии модели. Enter/SEND и
пунктуация используют прежнее правило: только уже готовый результат на границе.
Каждый callback дополнительно привязан к generation
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
спросом; spelling/contextual потребители независимы. IME создаёт потребителя через единственную Android-фабрику
`AndroidModelCandidates`: main Handler управляет паузой, `BoundModelScoringClient`
передаёт bounded request приватному процессу. Конечное число bind попыток
не доказывает ограничение inference CPU или экономию батареи.

`ActiveModelReadiness` читает только metadata через `DiskModelReadinessProbe`
на отдельном serial worker. Один заменяющий numeric epoch ограничивает очередь;
смена активности и close отбрасывают старый результат без ожидания worker.
Путь не создаёт model store, не открывает/хеширует GGUF и не получает текст.
Общий operation lock берётся неблокирующим read-only способом: занятый lock
даёт UNKNOWN. Повтор UNKNOWN допускается при следующем явном candidate action;
READY/MISSING/BROKEN не опрашиваются таймером. Переход inactive → active обновляет
metadata. READY означает доступность descriptor/file stat, а не загрузку,
проверенный digest или пройденную quality qualification. Сам ответ Ready
не инициирует binding/scoring. Актуальные NO_MODEL/LOAD_FAILED отменяют спрос
и сбрасывают hint; устаревшие ошибки не затрагивают новый запрос.

`imeIntelligenceBoundary` проверяет также client, IPC, readiness, storage и inference с
транзитивными зависимостями. Отрицательные fixtures подтверждают обнаружение
network, delivery, JNI, logging, filesystem/payload persistence и обходов
через helper. Только точная Android-фабрика допускает вход из IME в реализации
client/readiness; pure contracts и все транзитивные зависимости продолжают проверяться.
Native разрешён только adapter; URI разрешён только pure manifest
parser. Это source-level gate, дополняющий dependency и manifest проверки.

## Настройки и session state

Persistent (`SharedPreferences`, файл `keyboard_preferences`): включённые языки и их порядок, стартовый язык, высота по профилям экрана, отступы, цифровой ряд, тема, haptic, звук, preview, двойной пробел и независимые предпочтения Smart Typing. `SettingsCodec` читает их в immutable снапшот `KeyboardSettings`. Схема 3 добавляет `autocorrectionMode` (default `HIGH_CONFIDENCE`, в UI «Автозамена (95%)»), `mechanicalPunctuation` (true), `contextualPunctuationMode` (`SUGGESTIONS`) и `candidateStrip` (true). Сохранённое предпочтение не зависит от готовности модели. `SUGGESTIONS` оставляет ручной выбор; `HIGH_CONFIDENCE` автоматически применяет прошедшее зафиксированный 95% профиль model-assisted решение, когда локальная модель Ready. Без модели обычная орфография остаётся подсказкой; точное исправление регистра имени собственного работает локально. Контекстная пунктуация по-прежнему применяется только по явному нажатию.

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

`CandidateGenerator` выполняет общие protection, normalization и routed exact
membership проверки, затем использует точный глобальный top-seven selection для
packed словарей. `CandidateLexicon.scan` остаётся полным перечислением для
общих readers; отдельный `selectTop` требует сертификат семи вариантов в полном
порядке или исчерпания всей допустимой области поиска. Оба пути используют один
бюджет 8192 состояний и 64 проверенных terminals, включая exact lookup и оба языка.
Порядок определяется weighted distance, prior, частотой и Unicode scalar identity;
case/display дедупликация предшествует квоте fallback. Положительный результат
сертифицирует набор предложений, а не confidence или право на AutoReplace.

`PackedTopSeven` хранит глобальные heap/arena и unrestricted prefix DP в фиксированных
массивах на candidate worker. Он восстанавливает только уже прочитанные prefix
records, проверяет отмену между строками DP и очищает scratch в finally.
При переходе между ветвями DP сохраняет только общий scalar prefix для того же
запроса и языка; другая часть пути пересчитывается с полной историей unrestricted
transpositions. Смена языка сбрасывает глубину переиспользования, завершение
поиска очищает всю историю. Порядок frontier и бюджеты от этого не меняются.
Незавершённое расширение списка children не может выдать сертификат. Исчерпание
лимита оставляет только проверенные partial suggestions с veto автоматической
замены. Lazy bridge публикует immutable mappings; сам поиск не загружает файлы и
не сохраняет запросы. Дополнительные примитивные массивы занимают 286876 байт
на используемый engine, помимо существующих generator/reader arrays; это размер
ёмкости массивов, не измеренный RSS. Подробный proof и воспроизводимые controls:
`tools/lexicon/smart-typing-0.3/top-seven/README.md`.

Typing-контроллер сохраняет Original и до семи полных `GeneratedCandidate`,
включая deterministic features, а показывает только Original и два варианта.
Позиция на полоске не является identity: correction ID содержит исходный
индекс кандидата и не меняет смысл при перестановке. Невидимый ID не допускается
к выбору, даже если этот вариант остаётся в полном наборе.

`ModelCandidateCoordinator` подключён к вводу и выходу local coordinator.
Он использует cached eligibility/Ready для ранней подготовки весов без payload,
ждёт паузу 400 ms после принятого
словарного результата и отправляет полный набор только через `ModelScoringClient`.
Таймер хранит числовую identity и policy, а не текст. Snapshot собирается в момент
отправки из Rune-owned context; prefix исключает текущее typedWord, но включает
его leading boundary. Ввод/tap отменяет запрос, lifecycle/settings/privacy
дополнительно снимают binding. Reconnect/Ready/render не воспроизводят старый
payload. 400 ms — development debounce, не измеренный performance budget.

Числовой ответ принимается только для точного token, исходного candidate set,
текущей composition и неизменной owner policy. Нормализация — sum/tokenCount;
при равенстве сохраняется исходный порядок, Original имеет первый ID.
Результат меняет только порядок и выделение подсказок, никогда editor text.
Это ещё не калиброванный combined ranker или AutoReplace. Production IME
создаёт coordinator через Android-фабрику с read-only metadata Ready bridge.
Без актуального результата сохраняется немедленный словарный путь.

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
Автозамена ещё не включена. Contextual punctuation для допустимого текущего
слова ранжирует только bounded allowlist из пробела, запятой, двоеточия,
точки с запятой, точки, вопросительного и восклицательного знаков. На одно
слово допускается один запрос после паузы: typo отдаёт его spelling ranker,
valid word — contextual ranker. Непробельный победитель показывается как
suggestion и меняет только Rune-owned composing span после явного tap.
В sensitive/raw input,
на других слоях и после потери composing ownership полоса скрыта.

## Приватность и безопасность

- manifest объявляет ровно `android.permission.INTERNET`; сеть используется только после явного скачивания модели через системный DownloadManager;
- введённый текст не передаётся в delivery/activation; bounded scoring contract допускает эфемерную передачу Rune-owned контекста в приватный процесс того же приложения, без сети, логов или сохранения; IME consumer использует этот путь только для актуальных допустимых подсказок;
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

Встроенный model manifest принимает два вида источников: asset неизменяемого GitHub Release Rune
или файл публичного Hugging Face model repository, закреплённый полным 40-символьным commit SHA.
Ветки, теги, query/fragment, сокращённый `hf.co` и косвенные download-hosts отклоняются до постановки
загрузки. Имя файла в URL обязано совпадать с manifest; размер и SHA-256 проверяются независимо после
загрузки. Это позволяет доставлять квалифицированный GGUF через HF без moving target.

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

Build type `profile` повторяет release minification/shrinking, подписывается debug-ключом, имеет отдельный application ID suffix, остаётся `debuggable=false` и разрешает shell profiling через `<profileable>`. Perfetto-секции используют закрытый константный словарь: `Rune#composeUpdate`, `Rune#candidateGenerate`, `Rune#candidateRank`, `Rune#modelRequest`, `Rune#modelResult`, `Rune#candidateRender`, `Rune#correctionCommit`, `Rune#correctionUndo` и `Rune#punctuationRule`. Имена не получают текст, IDs, язык, editor package или путь модели. Аллокации снимаются отдельно на debuggable debug build.
