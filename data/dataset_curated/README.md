# Curated Dataset

Эта папка содержит нормализованную версию исходного корпуса из `G:\Copiya\dataset`.

Структура:
- `audio/` — уникальные аудиофайлы с нормализованными именами `cmd_0001.mp3`, ...
- `duplicates/` — вынесенные дубликаты
- `dataset_manifest.jsonl` — основной манифест для разметки и обучения
- `dataset_manifest.csv` — тот же манифест в табличном виде
- `duplicates_manifest.jsonl` — список дублей
- `summary.json` — краткая сводка по корпусу

Поля манифеста:
- `id`
- `split`
- `audio_path`
- `original_name`
- `source`
- `voice`
- `language`
- `transcript_asr`
- `text`
- `intent`
- `canonical_text`
- `hash`
- `duration`

Следующий шаг:
- заполнить `transcript_asr` или `text`
- затем разметить `intent` и `canonical_text`
