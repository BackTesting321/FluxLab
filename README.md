# FluxLab

Локальный инструмент для генерации и обучения LoRA для Flux: Django API + UI
(позже).

## Быстрый старт (backend)

```bash
cd server
python -m venv ../.venv
source ../.venv/Scripts/activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

GET /api/health
GET /api/training/diagnostics
GET /api/datasets/
GET /api/promptgen/models/
POST /api/enhance/preview

## /api/enhance/preview

`POST /api/enhance/preview` принимает путь к изображению и описание пайплайна
улучшения.

Пример запроса с автоматическим подбором цепочки:

```json
{
  "image_path": "sample.jpg",
  "auto_policy": "BASIC",
  "return": "metadata"
}
```

Пример запроса с явным указанием шагов:

```json
{
  "image_path": "sample.jpg",
  "auto_policy": "OFF",
  "pipeline": [
    {"type": "denoise", "params": {"level": "light"}},
    {"type": "face_restore", "params": {"level": "light"}},
    {"type": "upscale", "params": {"scale": 1.5}}
  ]
}
```

В ответе возвращаются поля `applied_pipeline`, `estimated_time_ms`,
`quality_before`, `quality_after` и `logs`.