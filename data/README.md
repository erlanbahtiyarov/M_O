# Данные проекта

Основной экспериментальный корпус содержит 86 размеченных русскоязычных
аудиозаписей команд управления компьютером.

Файл разметки:

```text
data/dataset_curated/recovery_dataset_86.jsonl
```

Каждая строка JSONL содержит:

- `audio_path` — относительный путь к аудиофайлу;
- `text` — результат распознавания речи;
- `intent` — класс команды;
- `canonical_text` — правильная формулировка команды;
- `split` — часть выборки: `train`, `val` или `test`.

Аудиофайлы размещаются в `data/dataset_curated/audio/`.

Проверка датасета:

```powershell
python scripts\validate_voice_command_dataset.py `
  --dataset data\dataset_curated\recovery_dataset_86.jsonl `
  --expected-count 86
```
