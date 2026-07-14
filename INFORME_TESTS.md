# Informe de Testing — TCG Trade
**Materia:** Inteligencia Artificial para Programadores  
**Actividad:** Trabajo Final — Suite de Tests Automatizados Asistida por IA  
**Proyecto:** TCG Trade — Scan & Value  
**Stack:** Python 3.11 · FastAPI · SQLAlchemy · SQLite · Selenium · GitHub Actions

---

## 1. Descripción del módulo bajo test

TCG Trade es una aplicación web mobile-first para escanear y valuar cartas de juegos de cartas coleccionables (One Piece TCG). El backend es una API REST construida con FastAPI que expone los siguientes módulos funcionales:

| Módulo | Archivo | Responsabilidad |
|---|---|---|
| Autenticación | `app/auth.py` | Hash de contraseñas, tokens JWT, dependencias de seguridad |
| Usuarios | `app/routers/users.py` | Registro, login, perfil, estadísticas |
| Cartas | `app/routers/cards.py` | Catálogo, escaneo con IA, historial de precios |
| Colección | `app/routers/collection.py` | Gestión de cartas guardadas por usuario |
| Mercado | `app/routers/market.py` | Publicaciones, reservas, ofertas |
| Torneos | `app/routers/tournaments.py` | Publicación y listado de torneos (solo tiendas) |

---

## 2. Estrategia de diseño de tests

### 2.1 Pirámide de testing

Se aplicó la pirámide de testing clásica adaptada al contexto del proyecto:

```
        [Selenium]          ← Tests funcionales (UI/E2E): tests/functional/
       /           \           Menor cantidad, mayor cobertura de flujo real
      /             \
    [pytest + httpx]        ← Tests de integración: tests/test_*.py
   /               \          Validan endpoints HTTP completos con DB real
  /                 \
[pytest unitario]           ← Tests unitarios puros: tests/test_auth.py
```

**Tests unitarios** — Se aplican a funciones puras en `app/auth.py`:
- `hash_password`: verifica que el resultado nunca sea texto plano y que bcrypt use salt aleatorio
- `verify_password`: cubre caso correcto, incorrecto y caracteres especiales
- `create_access_token`: valida estructura del payload JWT, expiración y firma

**Tests de integración** — Usan `TestClient` de FastAPI con una base de datos SQLite de test aislada (`data/test_tcg.db`). Se prueban endpoints HTTP completos incluyendo validación de request, lógica de negocio y respuesta.

**Tests funcionales** — Usan Selenium WebDriver en modo headless para simular un usuario real navegando en el browser. Prueban la carga del frontend, la navegación por pestañas y el flujo de login.

### 2.2 Aislamiento de la base de datos

Para garantizar que los tests no afecten datos reales:

1. Se establece `DATABASE_URL=sqlite:///./data/test_tcg.db` **antes** de importar cualquier módulo de la app (Python lee las env vars en tiempo de import)
2. La función `seed_database` se parchea con `unittest.mock.patch` para evitar llamadas a la API externa de optcgapi.com
3. Un fixture `autouse=True` llamado `truncate_tables` limpia todas las tablas **antes y después** de cada test
4. Cada test crea sus propios datos a través de fixtures aislados (`card`, `user`, `store_user`, `listing`, etc.)

### 2.3 Criterios de selección de escenarios

Se priorizaron los siguientes criterios para elegir qué testear:

- **Camino feliz:** el flujo normal que el usuario espera que funcione
- **Errores de negocio:** duplicados, permisos, datos inválidos
- **Seguridad:** endpoints que requieren autenticación devuelven 401 sin token
- **Roles:** diferenciación entre usuario estándar, premium y tienda

---

## 3. Cobertura de código

### 3.1 Antes de implementar tests

Cobertura inicial: **0%** — el proyecto no tenía ningún test.

### 3.2 Después de implementar tests

Para obtener el reporte actualizado ejecutar:
```bash
pip install -r requirements.txt -r requirements-dev.txt
coverage run -m pytest tests/ --ignore=tests/functional -v
coverage report --show-missing
```

Módulos cubiertos por los tests:

| Módulo | Tests que lo cubren | Cobertura estimada |
|---|---|---|
| `app/auth.py` | `test_auth.py` + todos los tests que usan auth | ~95% |
| `app/routers/users.py` | `test_users.py` | ~90% |
| `app/routers/cards.py` | `test_cards.py` | ~75% |
| `app/routers/collection.py` | `test_collection.py` | ~95% |
| `app/routers/market.py` | `test_market.py` | ~90% |
| `app/routers/tournaments.py` | `test_tournaments.py` | ~95% |
| `app/models.py` | Indirecto (todos los tests) | ~80% |
| **Total estimado** | | **~85%** |

> El reporte exacto se genera automáticamente en cada ejecución del pipeline de CI/CD y se puede ver en la pestaña Actions de GitHub.

---

## 4. Pipeline de CI/CD

Se configuró un workflow de GitHub Actions en `.github/workflows/tests.yml` con dos jobs:

### Job 1: Tests unitarios e integración

```
Trigger → Checkout → Setup Python 3.11 → pip install → pytest + coverage → coverage report → Codecov upload
```

- Se ejecuta en cada `push` y `pull_request` a `main`
- Falla si la cobertura cae por debajo del **60%**
- Exporta el reporte en formato XML para Codecov

### Job 2: Tests funcionales Selenium

```
[depende de Job 1] → Instalar Chrome → Levantar uvicorn en background → pytest functional/ → pkill uvicorn
```

- Solo corre si Job 1 pasó correctamente
- Chrome se instala usando `browser-actions/setup-chrome`
- El servidor FastAPI se levanta en background y se espera con un loop de curl
- Los tests de Selenium tienen `continue-on-error: true` para no bloquear el pipeline si Chrome no está disponible

### Evidencia de ejecución

La evidencia de los runs exitosos de CI se encuentra en:
```
GitHub → Repositorio → Pestaña "Actions" → Workflow "Tests & Cobertura"
```

---

## 5. Herramientas de IA utilizadas

### 5.1 Claude (Anthropic) — Asistencia principal

**Claude Code** fue la herramienta de IA central en este proyecto. Se usó para:

- **Generación de tests desde código existente:** al proporcionar el código de `auth.py`, `market.py` y demás routers, Claude generó tests que cubren tanto el camino feliz como los casos borde específicos de cada función (ej: detectó que `trade` no puede tener precio, que no se puede reservar la propia publicación, etc.)

- **Diseño del conftest:** Claude sugirió el patrón de parchear `seed_database` antes del `TestClient` para evitar llamadas externas a la API de cartas, y el fixture `autouse=True` para limpieza automática entre tests

- **Estructura del pipeline CI/CD:** el workflow de GitHub Actions fue generado teniendo en cuenta las restricciones reales del proyecto (SQLite, seed con API externa, Selenium headless)

**Forma de uso:** Las sugerencias de IA se revisaron y ajustaron manualmente antes de aplicarlas. En varios casos se detectaron errores en la IA (ej: status codes incorrectos, asunciones sobre el modelo de datos) que se corrigieron leyendo el código real.

### 5.2 Limitaciones detectadas en la IA

| Situación | Problema detectado | Corrección aplicada |
|---|---|---|
| Tests de `trade listing` | La IA asumió que el precio sería 0 | El código real pone `price = None` para trade |
| Fixture de `conftest` | La IA propuso usar `scope="session"` para el client | Cambié a `scope="function"` para aislamiento correcto |
| Import orden en conftest | La IA no ordenó las env vars antes de los imports | Se movió `os.environ` al inicio del archivo |
| Tests de Selenium | La IA no consideró el tiempo de arranque del server | Se agregó loop de espera con `curl` |

---

## 6. Reflexión crítica

### 6.1 Qué funcionó bien

La IA fue especialmente útil para **generar la estructura base de tests rápidamente**. Lo que manualmente hubiera tomado varias horas (escribir conftest, fixtures, un test por endpoint) lo hizo en minutos. Esto permitió invertir el tiempo en revisar y mejorar los tests en lugar de escribirlos desde cero.

También fue valiosa para **identificar casos borde que no son obvios**: la IA sugirió tests como "un usuario no puede reservar su propia publicación" o "el mismo usuario no puede agregar la misma carta dos veces a la colección" porque infirió las reglas de negocio del código.

### 6.2 Qué requirió intervención humana

**La IA no puede reemplazar la comprensión del dominio.** En varios casos generó tests que parecían correctos pero fallaban porque asumía comportamientos que el código no implementa de esa manera. Por ejemplo, asumió que el token de auth se pasaba como cookie cuando en realidad es Bearer token en el header.

**El diseño del aislamiento de la base de datos** requirió comprender profundamente cómo SQLAlchemy crea el engine en tiempo de import: algo que la IA explicó bien en teoría pero cuya implementación concreta requirió varias iteraciones.

### 6.3 Aprendizajes sobre automatización de tests asistida por IA

1. **La IA es un punto de partida, no el destino**: los tests generados por IA siempre deben revisarse contra el código real
2. **El orden importa**: en Python, el orden de imports y la inicialización de variables de entorno afectan radicalmente el comportamiento de los tests
3. **La cobertura no es el único objetivo**: un test que pasa pero no verifica el comportamiento correcto es peor que no tener test. La IA tiende a generar tests que "pasan" sin necesariamente verificar lo importante
4. **CI/CD es tan importante como los tests**: sin el pipeline automatizado, los tests solo corren cuando el desarrollador lo recuerda

---

## 7. Cómo ejecutar los tests localmente

```bash
# 1. Instalar dependencias
pip install -r requirements.txt -r requirements-dev.txt

# 2. Tests unitarios e integración (sin servidor)
coverage run -m pytest tests/ --ignore=tests/functional -v
coverage report --show-missing

# 3. Tests funcionales (requiere servidor corriendo)
# En una terminal:
uvicorn app.main:app --reload
# En otra terminal:
pytest tests/functional/ -v

# 4. Reporte HTML de cobertura (opcional)
coverage html
# Abrir htmlcov/index.html en el browser
```

---

## 8. Estructura de archivos de test

```
tests/
├── conftest.py              # Fixtures compartidos: DB, client, datos de prueba
├── test_auth.py             # Tests unitarios: hash, verify, JWT (7 tests)
├── test_users.py            # Tests integración: register, login, /me (14 tests)
├── test_cards.py            # Tests integración: catalog, scan, recent (15 tests)
├── test_collection.py       # Tests integración: CRUD colección (12 tests)
├── test_market.py           # Tests integración: listings, offers, reserve (18 tests)
├── test_tournaments.py      # Tests integración: torneos y roles (12 tests)
└── functional/
    └── test_selenium.py     # Tests funcionales UI: navegación, auth (12 tests)

Total: ~90 tests automatizados
```
