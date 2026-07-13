# Guía de exploración demo — TCG Trade

Esta guía permite recorrer todas las funcionalidades de la aplicación usando cuentas pre-configuradas. Cada cuenta representa un tipo de usuario distinto.

---

## Inicio rápido

```bash
start.bat          # Windows: inicia el servidor y abre el navegador
# o bien:
uvicorn app.main:app --reload
```

> Los usuarios demo se crean/actualizan en **cada arranque** (no hace falta borrar la base para tenerlos). Lo que sí requiere una base vacía es el catálogo de cartas, las 4 publicaciones demo y el torneo pre-cargado: si ya arrancaste el server antes, eliminá `data/tcg_trade.db` para que se vuelvan a sembrar.

---

## Cuentas demo

| Usuario | Contraseña | Tipo | Descripción |
|---|---|---|---|
| `usuario` | `usuario123` | Comprador **Premium** | Ve alertas y análisis sin bloqueo; puede ofertar cartas |
| `otrousuario` | `otrousuario123` | Comprador estándar | Sin premium; ve las mismas cartas y torneos pero con funciones bloqueadas |
| `tienda` | `tienda123` | **Tienda** | Puede publicar torneos y cartas; representa un comercio asociado |

---

## Escenario 1 — Usuario anónimo (sin login)

**Qué explorar:** funciones disponibles sin registrarse.

1. Abrí la app. Estás en la pantalla **Inicio**.
2. Navegá a **Escanear** y presioná "Escanear carta" (sin subir imagen — usa simulación determinística).
3. Observá el resultado: nombre, precio en ARS, tendencia y gráfico de historial.
4. Intentá guardar la carta → la app pide login (comportamiento esperado).
5. Navegá a **Catálogo** → buscá por nombre o rareza sin necesidad de cuenta.
6. Navegá a **Mercado** → ves las publicaciones activas y el torneo pre-cargado de `tienda`. No podés reservar ni ofertar sin login.

---

## Escenario 2 — Login como `tienda` (cuenta tienda)

**Qué explorar:** publicar una carta y publicar un torneo.

### Publicar una carta

**Opción A — por escaneo:**
1. Iniciá sesión con `tienda` / `tienda123`.
2. Navegá a **Escanear** → presioná "Escanear carta".
3. En el resultado: presioná **Publicar**.
4. Elegí el tipo (`sale`, `trade`, `negotiable` o `combo`).
5. Para `trade` o `combo` ingresá qué cartas buscás a cambio.
6. La carta queda publicada en el Mercado.

**Opción B — desde el Catálogo:**
1. Navegá a **Catálogo** → seleccioná un set → hacé clic en cualquier carta.
2. En el detalle de la carta: presioná **Publicar**.
3. Seguí los mismos pasos que en la opción A.

### Publicar un torneo

1. (Con sesión de `tienda` activa) Navegá a **Perfil**.
2. En el menú aparece **Publicar Torneo** (solo visible para cuentas tienda).
3. Completá los prompts: nombre, descripción, fecha (YYYY-MM-DD), lugar.
4. Confirmá → aparece el mensaje "¡Torneo publicado!".
5. Navegá a **Mercado** → el torneo aparece en la sección "🏆 Torneos activos".

---

## Escenario 3 — Login como `usuario` (premium)

**Qué explorar:** ver la oferta de `tienda`, hacer una oferta, y explorar funciones premium.

1. Cerrá sesión de `tienda` → iniciá sesión con `usuario` / `usuario123`.
2. En **Perfil** observás:
   - Subtítulo `@usuario · ⭐ Premium`
   - Banner verde "Premium activo" (sin botón de compra)
   - Opciones de menú "Alertas de precio" y "Análisis de mazo" **sin el candado** 🔒
3. Navegá a **Mercado**:
   - El torneo publicado por `tienda` aparece en la sección de torneos.
   - La carta publicada por `tienda` aparece en las publicaciones.
4. Hacé clic en **Ofertar** sobre la carta de `tienda`:
   - Ingresá un monto en ARS (ej. `15000`).
   - Opcionalmente mencioná cartas a ofrecer.
   - Confirmá → "Oferta enviada".
5. Hacé clic en **Reservar** sobre otra publicación → "Reserva creada".

---

## Escenario 4 — Login como `otrousuario` (estándar sin premium)

**Qué explorar:** mismas publicaciones y torneos visibles, pero funciones premium bloqueadas.

1. Cerrá sesión → iniciá sesión con `otrousuario` / `otrousuario123`.
2. En **Perfil** observás:
   - Banner "⭐ Premium" (mismo diseño que ve un anónimo) con botón "Conocer planes"
   - Opciones "Alertas de precio 🔒" y "Análisis de mazo 🔒" con candado
3. Navegá a **Mercado** → el torneo y las publicaciones son **los mismos** que ve `usuario`.
4. Podés reservar y ofertar (estas acciones no son premium).
5. Hacé clic en "Alertas de precio" → toast informando que es función premium.

---

## Escenario 5 — Ver oferta recibida (como `tienda`)

1. Volvé a iniciar sesión como `tienda` / `tienda123`.
2. Las ofertas recibidas se consultan vía API (solo disponible por endpoint por ahora):
   ```
   GET /api/market/listings/{id}/offers
   Authorization: Bearer <token>
   ```
   Podés probar desde `/docs` (Swagger UI incluido en FastAPI).
3. En `/docs` → `GET /api/market/listings` → copiá el `id` de la publicación de `tienda`.
4. `GET /api/market/listings/{id}/offers` → aparece la oferta de `usuario`.

---

## Escenario 6 — API interactiva (Swagger)

FastAPI incluye documentación interactiva en:

```
http://localhost:8085/docs
```

Endpoints principales para explorar:

| Endpoint | Descripción |
|---|---|
| `POST /api/users/login` | Obtener token JWT |
| `GET /api/catalog/sets` | Sets de cartas disponibles |
| `GET /api/cards?set_id=OP-01` | Cartas de un set |
| `POST /api/scan` | Simular escaneo (sin imagen) |
| `GET /api/market/listings` | Ver publicaciones activas |
| `POST /api/market/listings` | Publicar carta (requiere auth) |
| `POST /api/market/listings/{id}/offers` | Hacer oferta |
| `GET /api/tournaments` | Ver torneos activos |
| `POST /api/tournaments` | Publicar torneo (solo tiendas) |

---

## Mapa de pantallas

```
Inicio         → dashboard con escaneos recientes y acceso rápido a colección
Escanear       → escáner con cámara/foto + resultado con precio, tendencia, historial
Catálogo       → navegación por sets, búsqueda por nombre/rareza, detalle de carta
Mercado        → publicaciones activas + torneos; reservar y ofertar requiere login
Perfil         → estadísticas del usuario, banner premium, menú de funciones
```

---

## Notas técnicas

- **Base de datos:** SQLite en `data/tcg_trade.db`. Los usuarios demo se sincronizan en cada arranque; catálogo, publicaciones y torneo demo solo se siembran si la base está vacía (ver nota al principio).
- **Precios:** USD × 1500 ARS (tasa hardcodeada en `app/pricing.py`).
- **Escaneo real:** requiere variable de entorno `OPENAI_API_KEY`. Sin ella, el escaneo es determinístico (simula basado en hash de imagen).
- **Datos de cartas:** el catálogo se trae de `optcgapi.com` bajo demanda, cacheado en la base. Al primer arranque se siembra automáticamente **el set más reciente** (hoy OP-16); los otros 20 sets se piden a la API recién la primera vez que alguien los elige en el selector del Catálogo (`GET /api/cards?set_id=...`), y quedan guardados para las próximas veces. Si no hay red al arrancar, cae de respaldo al snapshot local `data/optcg_op01_raw.json` (set OP-01).
