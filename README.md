# FluxLab

Локальный инструмент для генерации и обучения LoRA для Flux: Django API + UI (позже).

## Быстрый старт (backend)

```bash
cd server
python -m venv ../.venv
source ../.venv/Scripts/activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

GET /api/health
GET /api/training/diagnostics
GET /api/datasets/
GET /api/promptgen/models/
POST /api/enhance/preview
