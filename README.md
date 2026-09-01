# Rune Keyboard

Rune Keyboard — компактная приватная Android-клавиатура на Kotlin. Проект реализован как независимый IME и не использует код или package identity Iris.

## Возможности MVP

- русская и английская QWERTY/ЙЦУКЕН-раскладки;
- одноразовый Shift и Caps Lock по двойному нажатию;
- цифры, основные символы и отдельные раскладки для number/phone/date-time полей;
- адаптация нижнего ряда для email и URL;
- Unicode-safe Backspace с повтором при удержании;
- корректные `DONE`, `GO`, `NEXT`, `PREVIOUS`, `SEARCH`, `SEND` и многострочный Enter;
- системный экран включения/выбора клавиатуры;
- светлая и тёмная темы, доступные Android View-клавиши;
- без `INTERNET`, телеметрии, рекламы, истории ввода и доступа к clipboard.

Подсказки, автокоррекция, словарь и свайп-ввод намеренно не входят в MVP.

## Требования

- JDK 17;
- Android SDK Platform 37 и Build Tools 36.0.0;
- Android 8.0 (API 26) или новее.

При настроенных стандартных `JAVA_HOME` и `ANDROID_HOME` сборка запускается так:

```bash
./gradlew --no-daemon :app:assembleDebug :app:lintDebug :app:testDebugUnitTest
```

Release-проверка:

```bash
./gradlew --no-daemon :app:assembleRelease
```

## Как включить

1. Установите `app/build/outputs/apk/debug/app-debug.apk`.
2. Откройте Rune Keyboard.
3. Нажмите «Открыть настройки клавиатур» и включите Rune.
4. Вернитесь в приложение, нажмите «Выбрать клавиатуру» и выберите Rune.

Долгое нажатие `RU`/`EN` открывает следующую клавиатуру или системный picker. `Ё` доступна долгим нажатием `Е`.

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
