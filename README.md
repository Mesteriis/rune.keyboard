# Rune Keyboard

Rune Keyboard — компактная приватная Android-клавиатура на Kotlin. Проект реализован как независимый IME и не использует код или package identity Iris.

## Возможности 0.2

- русская, английская и испанская раскладки (ЙЦУКЕН, QWERTY, QWERTY с `ñ`);
- жесты пробела: свайп влево/вправо меняет язык циклично, удержание перемещает курсор, двойной тап ставит `. `;
- компактный индикатор языка на пробеле;
- одноразовый Shift, Caps Lock по двойному нажатию, автокапитализация;
- долгое нажатие с попапом альтернатив: `á é í ó ú ü`, `ё`, `ъ`, `« »`, `– —`, `¿ ¡`, валюты;
- popup preview нажатой клавиши, отключаемый и никогда не показываемый в полях пароля;
- две страницы символов, опциональный цифровой ряд, отдельные раскладки number/phone/date-time;
- адаптация нижнего ряда для email и URL;
- Unicode-safe Backspace с ускоряющимся повтором при удержании;
- корректные `DONE`, `GO`, `NEXT`, `PREVIOUS`, `SEARCH`, `SEND` и многострочный Enter;
- onboarding с выбором языков и тестовыми полями, полноценный экран настроек;
- профили размеров под внешний и внутренний экран Fold, обе ориентации, пресеты высоты и отступов;
- темы `Как в системе / Светлая / Тёмная`, пять режимов вибрации, четыре режима звука;
- необязательная локальная Rune Text 0.1: явное скачивание/импорт, проверка и локальный runtime self-test; модель пока не подключена к вводу;
- ровно одно разрешение `android.permission.INTERNET`, используемое только для явно запущенного скачивания модели; без телеметрии, рекламы, истории ввода и доступа к clipboard.

Автокоррекция, автоматическая пунктуация, composing, inference из IME и общий `generate()` намеренно не входят в 0.2. Скользящий ввод, подсказки, словарь, Emoji-панель, one-handed и split-режимы, свайп по Backspace и голосовой ввод отложены на следующие версии.

## Требования

- JDK 17;
- Android SDK Platform 37 и Build Tools 36.0.0;
- Android NDK `29.0.14206865` и CMake `3.31.6`;
- Android 8.0 (API 26) или новее.

После клонирования нужен pinned submodule runtime:

```bash
git submodule update --init --recursive
```

При настроенных стандартных `JAVA_HOME` и `ANDROID_HOME` полная проверка запускается так:

```bash
./gradlew testDebugUnitTest lint assembleDebug assembleRelease assembleProfile \
  privacyGateRelease privacyGateProfile imeIntelligenceBoundary \
  forbiddenRuntimeDependencies :runtime-llama:nativeSymbolGate
```

`privacyGateRelease` проверяет ровно одно разрешение `INTERNET`, отключённые cleartext/backup и отсутствие логирования. `imeIntelligenceBoundary` запрещает сети, доставке модели и native runtime попадать в `ime/**`; native gate проверяет ABI, зависимости и отсутствие JNI/log/network symbols.

Подпись release-сборки описана в [docs/RELEASE.md](docs/RELEASE.md); без keystore release собирается неподписанным.

## Как включить

1. Установите `app/build/outputs/apk/debug/app-debug.apk`.
2. Откройте Rune Keyboard.
3. Нажмите «Открыть настройки клавиатур» и включите Rune.
4. Вернитесь в приложение, нажмите «Выбрать клавиатуру» и выберите Rune.
5. Выберите языки и проверьте ввод в тестовых полях на том же экране.

Язык переключается свайпом по пробелу. Rune не дублирует системную кнопку скрытия клавиатуры. `Ё` доступна долгим нажатием `Е`.

## Иконка

Исходный RGBA-мастер хранится в `artwork/rune-keyboard-icon-source.png`. Adaptive foreground
генерируется детерминированно с настоящим alpha-каналом и безопасными полями:

```bash
ffmpeg -i artwork/rune-keyboard-icon-source.png \
  -vf 'scale=600:-1:flags=lanczos,pad=1024:1024:(ow-iw)/2:(oh-ih)/2:color=0x00000000' \
  -frames:v 1 -pix_fmt rgba \
  app/src/main/res/drawable-nodpi/ic_launcher_foreground_art.png
```

Полноцветный foreground используется Android adaptive icon, а прежний простой Rune-вектор —
как monochrome-слой для системных themed icons.

Архитектура описана в [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), реальная IME-приёмка — в [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).
