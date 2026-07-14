# Guía de deploy — TCG Trade en Railway

## 1. GitHub

En la carpeta del proyecto:

```bash
git init
git add .
git commit -m "TCG Trade: FastAPI + SQLite listo para Railway"
```

Creá un repo vacío en GitHub (sin README) y:

```bash
git remote add origin https://github.com/TU_USUARIO/tcg-trade.git
git branch -M main
git push -u origin main
```

Si ya tenés el repo conectado (como este), simplemente `git push`.

## 2. Railway

1. Entrá a https://railway.app y creá cuenta (podés con GitHub).
2. **New Project** → **Deploy from GitHub repo** → elegí el repo.
3. Railway detecta Python automáticamente (Nixpacks) e instala `requirements.txt` solo.
4. En la pestaña **Settings** del servicio, en **Deploy**:
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. En **Variables** (opcional):
   - `SECRET_KEY` = cualquier string largo aleatorio
   - `GEMINI_API_KEY` = solo si querés IA real en el escaneo (gratis, sin tarjeta, en [Google AI Studio](https://aistudio.google.com/apikey))
6. Railway asigna una URL pública en **Settings → Networking → Generate Domain** (tipo `https://tcg-trade-production-xxxx.up.railway.app`).
7. Cada `git push` a la rama conectada dispara un redeploy automático.

## 3. Persistencia de la base (opcional)

Por defecto el filesystem de Railway es efímero como en cualquier PaaS: `data/tcg_trade.db` se recrea en cada redeploy (el seed vuelve a cargar cartas, usuarios demo, torneo y publicaciones). Si querés que la base sobreviva a los redeploys:

1. En el servicio → **Settings → Volumes** → **Add Volume**.
2. Mount path: `/app/data` (o la ruta donde corra el proyecto dentro del contenedor).
3. Redeployá — a partir de ahí `data/tcg_trade.db` persiste entre despliegues.

## 4. Verificación

- Home carga la app.
- `/api/health` responde `{"status":"ok"}`.
- Login con `usuario` / `usuario123` (premium), `tienda` / `tienda123` (tienda) u `otrousuario` / `otrousuario123`.
- Escaneo → Guardar → Publicar → Ofertar.
- Catálogo lista cartas reales de One Piece TCG (trae el set más reciente al primer arranque).
- Mercado muestra el torneo pre-cargado por `tienda`.

## Notas del plan gratuito

- Railway da un crédito mensual gratis (plan Trial/Hobby); revisá los límites vigentes en tu dashboard, ya que pueden cambiar.
- Sin un Volume (paso 3), el SQLite se resetea en cada redeploy; el seed recrea cartas, usuarios y datos demo automáticamente.
- A diferencia de Render free, Railway no duerme la instancia por inactividad en los planes pagos/Hobby — confirmá el comportamiento del plan que tengas activo.
