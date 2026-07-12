# TCG Trade — Registro de desarrollo

**Fecha:** 15 de junio de 2026  
**Estado:** Aplicación funcional (versión estática / prototipo)  
**Ubicación del proyecto:** `proyecto/`

---

## Contexto

Se revisó la carpeta `proyecto` existente y se detectó que no correspondía con los materiales de referencia del curso:

- `diagrama_logica.png` — flujo funcional y modelo de monetización
- `wireframe_pantallas_1_2.png` y `wireframe_pantallas_3.png` — diseño de interfaz móvil
- `TCG_Trade_ScanValue_Actividad4.docx` — especificación de la app Scan & Value

El código anterior era un landing web genérico (header, hero, galería con imágenes de placeholder) que no implementaba pantallas, flujos ni el diseño visual definido en los wireframes.

---

## Qué se hizo

### 1. Reconstrucción desde cero

Se eliminó el enfoque anterior y se creó una **SPA móvil** alineada con los wireframes y el diagrama de lógica.

**Archivos principales:**

| Archivo | Rol |
|---|---|
| `index.html` | Shell de la aplicación |
| `styles.css` | Design system (navy `#1A1A2E`, rojo `#E94560`, layout móvil) |
| `app.js` | Pantallas, navegación, datos mock y flujo de escaneo |
| `start.bat` | Servidor local con Python (`http.server` puerto 8000) |
| `README.md` | Instrucciones de ejecución |

### 2. Pantallas implementadas

- **Inicio** — Logo TCGTrade, tagline, botón principal “Escanear carta”, accesos a colección y mercado, listado de últimos escaneos.
- **Escanear** — Viewfinder simulado, animación de identificación y pantalla de resultado con precio, tendencia y gráfico de 30 días.
- **Mercado** — Listados de ejemplo (venta e intercambio).
- **Perfil** — Estadísticas, banner premium y menú de funciones secundarias (alertas, mazo, torneos, historial).
- **Colección** — Accesible desde el inicio; muestra cartas guardadas y valor estimado.

### 3. Flujo principal (según wireframe)

```
Inicio → Escanear carta → Simular escaneo → Resultado (precio + gráfico)
                                              ↓
                                    Guardar / Publicar / Nueva
```

### 4. Datos mock

Se usaron las cartas del wireframe como referencia:

- **Monkey D. Luffy** — One Piece OP-01 — $4.200 ARS — tendencia ↑ +12%
- **Zoro Promo** — One Piece OP-02 — $8.500 ARS — tendencia ↓ -5%

### 5. Script de arranque

Se creó `start.bat` para levantar la app con:

```bat
python -m http.server 8000
```

El script verifica que Python esté instalado, inicia el servidor y abre el navegador en `http://localhost:8000`.

---

## Decisiones técnicas

- **HTML + CSS + JavaScript puro** — sin frameworks ni dependencias, según el plan original (Opción A: sitio estático).
- **Mobile-first** — contenedor máximo 430px, navegación inferior fija.
- **Dark mode fijo** — coherente con la estética definida en la actividad (no modo claro).
- **Escaneo simulado** — no hay cámara real ni IA de visión; el botón “Simular escaneo” reproduce el flujo del wireframe.

---

## Alcance actual (qué NO está implementado)

| Funcionalidad | Estado |
|---|---|
| Cámara / IA de visión real | No implementado |
| Backend / API de precios | No implementado |
| Registro de usuarios | No implementado |
| Marketplace funcional (reservas, ofertas) | Solo UI mock |
| Análisis de mazo | Solo enlace / toast |
| Torneos y notificaciones | Solo enlace / toast |
| Monetización (premium, destacados) | Solo banner informativo |

---

## Cómo ejecutar

1. Ir a la carpeta `proyecto/`.
2. Ejecutar `start.bat` (doble clic).
3. Abrir `http://localhost:8000` si no se abre automáticamente.

---

## Próximos pasos sugeridos (futuro)

1. Integrar acceso a cámara del dispositivo (`getUserMedia`).
2. Conectar con API mock o backend para precios reales.
3. Persistir colección en `localStorage`.
4. Completar pantalla de publicación (venta / intercambio / mixto).
5. Implementar pantalla de análisis de mazo según diagrama de lógica.

---

## Referencias del curso

- `../diagrama_logica.png`
- `../wireframe_pantallas_1_2.png`
- `../wireframe_pantallas_3.png`
- `../TCG_Trade_ScanValue_Actividad4.docx`
- `../documentacion/plan.md`

---

*Documento generado el 15/06/2026 como registro del trabajo realizado en la sesión de desarrollo.*
