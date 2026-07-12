# Guía de deploy — TCG Trade en Render

## 1. GitHub

En la carpeta del proyecto:

```bash
git init
git add .
git commit -m "TCG Trade: FastAPI + SQLite listo para Render"
```

Creá un repo vacío en GitHub (sin README) y:

```bash
git remote add origin https://github.com/TU_USUARIO/tcg-trade.git
git branch -M main
git push -u origin main
```

## 2. Render

1. Entrá a https://dashboard.render.com y creá cuenta (podés con GitHub).
2. **New** → **Web Service** → conectá el repo `tcg-trade`.
3. Settings:
   - **Name**: `tcg-trade`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type**: Free
4. Environment (opcional):
   - `SECRET_KEY` = cualquier string largo aleatorio
   - `OPENAI_API_KEY` = solo si querés IA real en el escaneo
5. **Create Web Service** y esperá el deploy (~2–5 min).
6. Abrí la URL tipo `https://tcg-trade-xxxx.onrender.com`

Alternativa: **New** → **Blueprint** y usá el `render.yaml` del repo.

## 3. Verificación

- Home carga la app.
- `/api/health` responde `{"status":"ok"}`.
- Login con `demo` / `demo123`.
- Escaneo → Guardar → Publicar → Ofertar.

## Notas free tier

- Cold start: la primera visita tras dormir puede tardar 30–60 s.
- SQLite se resetea en redeploy; el seed recrea cartas y usuarios demo.
