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

## Cuentas de prueba

| Usuario | Contraseña | Tipo |
|---|---|---|
| `usuario` | `usuario123` | Usuario premium |
| `otrousuario` | `otrousuario123` | Usuario normal |
| `tienda` | `tienda123` | Tienda (puede crear torneos) |

## Funcionalidades

| Área | Detalle |
|---|---|
| **Escanear** | Sin registro. Subí/sacá una foto o escaneá sin foto. Devuelve carta, precio ARS, tendencia y gráfico. |
| **Colección** | Requiere login. Guardar cartas y ver valor total. |
| **Mercado** | Publicar (venta / intercambio / negociable / combo), reservar y ofertar. |
| **Perfil** | Stats reales + banner premium (maqueta). |
| **Torneos** | Las cuentas tipo tienda pueden crear torneos. Cualquier usuario puede ver los torneos activos. |

### Escaneo híbrido (IA)

- Por defecto: identificación **simulada** contra la base SQLite.
- Si configurás `GEMINI_API_KEY` (gratis en [Google AI Studio](https://aistudio.google.com/apikey), sin tarjeta), el backend intenta visión con Gemini y cae a simulación si falla.
- También soporta `OPENAI_API_KEY` como alternativa/fallback si preferís OpenAI.
- Para probar el escaneo real sin tener una carta física a mano, usá la foto de ejemplo incluida en el repo: [`carta_image.jpeg`](carta_image.jpeg) (subila desde la pantalla Escanear).

## Estructura

```
app/           # FastAPI, modelos, seed, routers
static/        # Frontend (HTML/CSS/JS)
data/          # SQLite local (se crea al arrancar)
requirements.txt
render.yaml
```

## Deploy

La app está desplegada en **Railway**: [https://tcg-trade.up.railway.app/](https://tcg-trade.up.railway.app/)

### Variables de entorno

- `SECRET_KEY` (recomendado)
- `GEMINI_API_KEY` (solo si querés escaneo con IA real, gratis en Google AI Studio)

### Limitaciones del plan free de Railway

- El disco es **efímero**: SQLite se recrea en cada deploy/reinicio. El `seed` vuelve a cargar cartas y usuarios de prueba automáticamente.

## API principal

- `GET /api/health`
- `GET /api/cards` · `GET /api/cards/{id}`
- `POST /api/scan` (multipart opcional `file`)
- `POST /api/users/register` · `POST /api/users/login`
- `GET /api/collection` · `POST /api/collection/{card_id}`
- `GET /api/market/listings` · `POST /api/market/listings`
- `POST /api/market/listings/{id}/reserve`
- `POST /api/market/listings/{id}/offers`
- `GET /api/tournaments` · `POST /api/tournaments` (requiere cuenta tienda)
- `GET /api/tournaments/mine`

## Notas

Los archivos `index.html`, `app.js` y `styles.css` de la raíz son la versión estática original. La app en producción usa `static/` servida por FastAPI.
