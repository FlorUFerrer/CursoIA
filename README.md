# TCG Trade — Scan & Value

App web móvil para escanear cartas TCG, ver precio de mercado, tendencia y gráfico histórico. Backend **FastAPI + SQLite**, frontend SPA, deploy listo para **Render** (plan gratuito).

## Requisitos locales

- Python 3.10+ (probado con 3.14)
- Navegador moderno

## Cómo levantarlo

### Opción rápida — `start.bat`

1. Doble clic en `start.bat`
2. Abrí `http://localhost:8085`

### Manual

```bash
cd proyecto
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8085
```

Abrí `http://localhost:8085`. Documentación interactiva de la API: `http://localhost:8085/docs`.

## Cuenta demo

- Usuario: `demo`
- Contraseña: `demo123`

También existen vendedores seed: `ColeccionAR` / `TCG_BA` (misma contraseña).

## Funcionalidades

| Área | Detalle |
|---|---|
| **Escanear** | Sin registro. Subí/sacá una foto o escaneá sin foto. Devuelve carta, precio ARS, tendencia y gráfico. |
| **Colección** | Requiere login. Guardar cartas y ver valor total. |
| **Mercado** | Publicar (venta / intercambio / negociable / combo), reservar y ofertar. |
| **Perfil** | Stats reales + banner premium (maqueta). |

### Escaneo híbrido (IA)

- Por defecto: identificación **simulada** contra la base SQLite.
- Si configurás `GEMINI_API_KEY` (gratis en [Google AI Studio](https://aistudio.google.com/apikey), sin tarjeta), el backend intenta visión con Gemini y cae a simulación si falla.
- También soporta `OPENAI_API_KEY` como alternativa/fallback si preferís OpenAI.

## Estructura

```
app/           # FastAPI, modelos, seed, routers
static/        # Frontend (HTML/CSS/JS)
data/          # SQLite local (se crea al arrancar)
requirements.txt
render.yaml
```

## Deploy en Render (gratis)

1. Subí el proyecto a un repositorio de **GitHub**.
2. En [Render](https://render.com) → **New** → **Web Service** → conectá el repo.
3. Configuración:
   - **Runtime**: Python
   - **Build**: `pip install -r requirements.txt`
   - **Start**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Variables opcionales:
   - `SECRET_KEY` (recomendado; o usá el `render.yaml` que la genera)
   - `GEMINI_API_KEY` (solo si querés escaneo con IA real, gratis en Google AI Studio)

También podés usar **Blueprint** con el archivo `render.yaml` incluido.

### Limitaciones del plan free de Render

- La instancia se **duerme** tras ~15 min sin tráfico (la primera carga puede tardar).
- El disco es **efímero**: SQLite se recrea en cada deploy/reinicio. El `seed` vuelve a cargar cartas y usuarios demo automáticamente.

## API principal

- `GET /api/health`
- `GET /api/cards` · `GET /api/cards/{id}`
- `POST /api/scan` (multipart opcional `file`)
- `POST /api/users/register` · `POST /api/users/login`
- `GET /api/collection` · `POST /api/collection/{card_id}`
- `GET /api/market/listings` · `POST /api/market/listings`
- `POST /api/market/listings/{id}/reserve`
- `POST /api/market/listings/{id}/offers`

## Notas

Los archivos `index.html`, `app.js` y `styles.css` de la raíz son la versión estática original. La app en producción usa `static/` servida por FastAPI.
