# voice_control_pc

Модуль дипломного проекта для локального голосового управления ПК на Windows 11.

В этой итерации реализовано практическое ядро:
- пакет `voice_control_pc`
- YAML-конфигурация
- rule-based NLU
- локальный neural recovery слой для битых ASR-команд
- безопасный executor по allowlist
- CLI для обработки текстовой команды
- заготовки для ASR, устройств и GUI
- базовые unit-тесты

## Структура

- `configs/default.yaml` — основные настройки приложения
- `configs/commands.yaml` — список intents и примеры фраз
- `configs/apps.yaml` — allowlist приложений и папок
- `src/voice_control_pc` — исходный код
- `tests` — тесты

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
voice-pc command "открой браузер" --dry-run
```

## CLI

```bash
voice-pc devices
voice-pc transcribe path.wav
voice-pc command "открой папку загрузки" --dry-run
voice-pc listen --dry-run --duration 5
voice-pc gui
```

## Neural Recovery

Если ASR распознает команду не полностью, например:

- распознано: `крой папку загрузки`
- нужно: `открой папку загрузки`

можно обучить локальную нейросеть восстановления команд.

### Вариант 1. Базовый корпус из 97 записей

1. Положить ровно `97` голосовых записей в `data/audio_commands/`.

2. Создать JSONL из этих записей:

```bash
python scripts/prepare_voice_command_dataset.py
```

3. Разметить `intent` и `canonical_text` в `data/voice_commands_97.jsonl`.

4. Проверить датасет:

```bash
python scripts/validate_voice_command_dataset.py --dataset data/voice_commands_97.jsonl --expected-count 97
```

### Вариант 2. Приобретённый корпус из 86 записей

1. Подготовить нормализованный черновик recovery-датасета из `data/dataset_curated/dataset_manifest.jsonl`:

```bash
python scripts/prepare_curated_recovery_dataset.py
```

2. Если ASR уже заполнил транскрипты, но нужно только проверить структуру черновика:

```bash
python scripts/validate_voice_command_dataset.py --allow-draft
```

3. После ревью и корректировки `text`, `intent` и `canonical_text` проверить финальный датасет:

```bash
python scripts/validate_voice_command_dataset.py --expected-count 86
```

### Обучение

```bash
pip install -e .[dev,ml]
python scripts/train_command_recovery.py --expected-count 86
```

После этого модель будет загружаться из `models/command_recovery.pt`
и автоматически использоваться перед rule-based NLU.

## Ограничения текущей итерации

- `listen` и полноценный захват микрофона пока не доведены до production-состояния
- GUI пока минимальный
- основная рабочая часть сейчас — конфиги, NLU и безопасное исполнение команд
