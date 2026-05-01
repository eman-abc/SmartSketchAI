# SmartSketch API – Frontend Integration Spec

**For:** Frontend developer / integration  
**Backend base URL (local dev):** `http://127.0.0.1:8000/api`  
**Auth:** JWT (Bearer token). Send header: `Authorization: Bearer <access_token>` on all protected endpoints.

---

## 1. Authentication

### Login (get tokens)
- **POST** `/api/token/`
- **Body (JSON):** `{ "username": "...", "password": "..." }`
- **Response 200:** `{ "access": "<jwt_access_token>", "refresh": "<jwt_refresh_token>" }`
- **No** `Authorization` header for this request.

### Refresh token
- **POST** `/api/token/refresh/`
- **Body (JSON):** `{ "refresh": "<refresh_token>" }`
- **Response 200:** `{ "access": "<new_access_token>" }`

### Register
- **POST** `/api/register/`
- **Body (JSON):** `{ "username": "...", "email": "...", "password": "...", "role": "general" }`
- **Roles:** `admin` | `forensic` | `editor` | `general`
- **No** auth required.

---

## 2. Generate forensic sketch (main flow)

- **POST** `/api/forensic/generate/`
- **Headers:** `Authorization: Bearer <access>`, `Content-Type: application/json`
- **Body (JSON):**
  ```json
  {
    "prompt": "required text",
    "case_type": "criminal",
    "age": 25
  }
  ```
  - `prompt`: required.
  - `case_type`: optional, default `"criminal"`.
  - `age`: optional number or `null`.

- **Success 200:**
  ```json
  {
    "id": 1,
    "image_url": "http://127.0.0.1:8000/media/generated/xxx.png",
    "scores": { "clip_score": 0.87, "identity_score": 0.72, "combined_score": 0.8 },
    "metadata": { "seed": 12345, "model_version": "..." },
    "generation_id": "..."
  }
  ```

- **Errors:**
  - **400** – `prompt` missing or invalid, or ML error: `{ "error": "..." }`
  - **403** – Not allowed (only role `forensic` or admin)
  - **500** – `{ "error": "Remote ML service URL is not configured on the server" }`
  - **502** – ML service unreachable or bad response: `{ "error": "..." }`

---

## 3. Edit forensic sketch

- **POST** `/api/forensic/edit/`
- **Headers:** `Authorization: Bearer <access>`, `Content-Type: application/json`
- **Body (JSON):**
  ```json
  {
    "original_image_id": 123,
    "edit_prompt": "add round glasses",
    "strength": 0.6
  }
  ```
  - `original_image_id`: required. ID of a GeneratedImage owned by the user.
  - `edit_prompt`: required. What to change (e.g., "add beard", "make older").
  - `strength`: optional, 0.0-1.0, default 0.6. Higher = more change.

- **Success 200:**
  ```json
  {
    "id": 1,
    "original_image_id": 123,
    "original_image_url": "http://127.0.0.1:8000/media/generated/xxx.png",
    "edited_image_url": "http://127.0.0.1:8000/media/edited/yyy.png",
    "edit_prompt": "add round glasses",
    "identity_score": 0.87,
    "identity_preserved": true,
    "scores": { "clip_score": 0.69, "combined_score": 69.1 },
    "metadata": { ... },
    "edit_id": "edit_..."
  }
  ```

- **Errors:**
  - **400** – Missing fields or ML error: `{ "error": "..." }`
  - **403** – Not allowed (only role `forensic` or admin)
  - **404** – Original image not found or not owned by user
  - **502** – ML service unreachable or bad response

---

## 4. Other useful endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/profile/` | Yes | Current user info |
| GET | `/api/my-images/` | Yes | List user’s generated images |
| GET | `/api/audit-logs/` | Yes | List audit logs (filtered by role) |
| POST | `/api/forensic-requests/` | Yes | Create forensic request |
| POST | `/api/forensic-requests/<id>/approve/` | Admin | Approve request |

---

## 5. CORS

Backend allows all origins in dev (`CORS_ALLOW_ALL_ORIGINS = True`). No extra CORS setup needed for local frontend (e.g. Vite on `http://localhost:5173`).

---

## 6. Frontend config

- Set **API base URL** to `http://127.0.0.1:8000/api` for local development (env var recommended, e.g. `VITE_API_BASE_URL`).
- Store `access` in memory or secure storage; send as `Authorization: Bearer <access>` on every protected request.
- On **401**, use refresh token; if refresh fails, redirect to login.
