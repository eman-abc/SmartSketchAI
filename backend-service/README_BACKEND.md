# SmartSketch AI – Backend

Django REST API with JWT auth and forensic sketch generation.

## Requirements

- Python 3.10+
- pip

## Run locally

1. **Create virtualenv and install dependencies**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. **Environment**
   - Copy `.env.example` to `.env` and set `COLAB_ML_URL` if you use the generate endpoint (Colab ML service URL).
   - Without `COLAB_ML_URL`, other endpoints (register, login, profile, etc.) still work; `/api/forensic/generate/` will need this URL.

3. **Database**
   ```bash
   python manage.py migrate
   ```

4. **Run server**
   ```bash
   python manage.py runserver
   ```
   API base: `http://127.0.0.1:8000/api`

## Main endpoints

- `POST /api/register/` – register
- `POST /api/token/` – login (get JWT)
- `POST /api/token/refresh/` – refresh JWT
- `POST /api/forensic/generate/` – generate sketch (requires `COLAB_ML_URL` in `.env`)
- See `API_INTEGRATION_SPEC.md` for full list and request/response shapes.
