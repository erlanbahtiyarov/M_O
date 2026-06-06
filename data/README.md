# Training Data

Для этого проекта основной тренировочный корпус должен состоять ровно из `97`
голосовых записей команд на русском языке.

Есть два режима:
- `real` — твои реальные записи
- `synthetic` — локально сгенерированные TTS-записи

## Быстро создать синтетический аудиокорпус

Если нужен готовый аудиодатасет, можно локально сгенерировать `97` русских
команд через установленный Windows TTS:

```bash
python scripts/generate_synthetic_audio_dataset.py
```

После этого будут созданы:
- `data/audio_commands/001.wav ... 097.wav`
- `data/voice_commands_97.jsonl`

Важно:
- это **синтетические** записи, а не реальные человеческие голоса
- для финального обучения/оценки ВКР лучше смешивать их с реальными записями

## Структура

- `data/audio_commands/` — сюда положить `97` аудиофайлов команд
- `data/voice_commands_97.jsonl` — итоговый размеченный JSONL для обучения

## Шаг 1. Подготовка корпуса из 97 записей

Положи ровно `97` файлов в `data/audio_commands/`.

Поддерживаемые форматы:
- `.wav`
- `.mp3`
- `.m4a`
- `.flac`

## Шаг 2. Создание черновика JSONL

Если хочешь автоматически получить первичные транскрипции через Faster-Whisper:

```bash
python scripts/prepare_voice_command_dataset.py
```

Если хочешь сначала только собрать шаблон без ASR:

```bash
python scripts/prepare_voice_command_dataset.py --skip-asr
```

Скрипт проверяет, что в папке лежит ровно `97` записей.

## Шаг 3. Ручная разметка

После этого открой `data/voice_commands_97.jsonl` и для каждой строки заполни:
- `intent`
- `canonical_text`

Пример строки:

```json
{"audio_path":"G:/Copiya/VKR_Module_Project/data/audio_commands/001.wav","text":"крой папку загрузки","intent":"open_folder","canonical_text":"открой папку загрузки","language":"ru"}
```

Поля:
- `audio_path` — путь к записи
- `text` — то, что реально распознал ASR
- `intent` — правильный intent
- `canonical_text` — правильная эталонная команда
- `language` — язык корпуса

## Шаг 4. Валидация

Перед обучением проверь датасет:

```bash
python scripts/validate_voice_command_dataset.py
```

Скрипт проверяет:
- что строк ровно `97`
- что в каждой записи есть `audio_path`, `text`, `intent`, `canonical_text`

## Шаг 5. Обучение

```bash
python scripts/train_command_recovery.py
```

Скрипт тоже требует ровно `97` записей и не запустится на другом количестве.
