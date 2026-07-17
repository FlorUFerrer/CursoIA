# Pendientes de desarrollo — TCG Trade

Estado al 16/07/2026. Referencia: consigna del Trabajo Final (IA para Programadores).

---

## ✅ Funcionalidades completadas

| Feature | Detalle |
|---------|---------|
| 1.1 Editar torneo | PATCH /api/tournaments/{id}, solo organizador |
| 1.2 Inscripción de usuarios | POST/DELETE /api/tournaments/{id}/register, modal con DNI |
| 1.3 Cupos máximos | max_participants opcional, validación al inscribirse |
| 1.4 Mis inscripciones | GET /api/tournaments/mine-registered, tab en frontend |
| 1.5 Buscador de torneos | Filtro client-side por nombre, tienda, lugar |
| 1.6 ID visible y buscable | Badge #ID en cada tarjeta, buscable con #123 |
| Bug escanear vs galería | Cámara (getUserMedia) separada de Subir imagen |
| Buscador en Mercado | Filtro por carta, vendedor, set, tipo |
| Chat comprador-vendedor | WebSocket por publicación, historial REST, pantalla de chat |
| Mis chats | GET /api/messages/mine, tab en Mercado, preview último mensaje |
| Notificaciones en tiempo real | WS /ws/notify por usuario, badge en campanita + nav Mercado |
| Badge por chat | No-leídos por listing_id, abrir directo si hay 1 solo |
| Ordenar no-leídos primero | Mis chats ordena unread al tope |

---

## ❌ Pendiente para aprobar el TP

### A. Tests de endpoints nuevos (crítico — afecta cobertura)

Los siguientes módulos **no tienen tests** y bajan el porcentaje de cobertura.
El CI exige mínimo 60% (`--fail-under=60`).

#### `tests/test_messages.py` — crear desde cero
- GET /api/messages/mine → lista chats del usuario
- GET /api/messages/{listing_id} → historial de mensajes
- Requiere auth en ambos
- Historial vacío para listing sin mensajes

#### `tests/test_tournaments.py` — ampliar el existente
- PATCH /api/tournaments/{id} → editar (organizador puede, otro no)
- POST /api/tournaments/{id}/cancel → cancelar con motivo
- GET /api/tournaments/mine → solo la tienda ve sus torneos
- POST /api/tournaments/{id}/register → inscribirse (con DNI, cupo, duplicado)
- DELETE /api/tournaments/{id}/register → desanotarse
- GET /api/tournaments/{id}/registrations → solo el organizador puede ver inscriptos
- GET /api/tournaments/mine-registered → el usuario ve sus inscripciones

#### `tests/test_users.py` — ampliar el existente
- PATCH /api/users/me → actualizar nombre, apellido, DNI

---

### B. Informe escrito (entregable obligatorio del TP)

Documento (PDF o MD) que incluya:

1. **Justificación de diseño de pruebas** — por qué se eligió pytest + Selenium + GitHub Actions
2. **Análisis de cobertura antes y después** — porcentaje inicial vs final, qué módulos cubren más/menos
3. **Capturas de pantalla del CI** — ejecución exitosa en GitHub Actions (jobs: unit-tests + functional-tests)
4. **Reflexión crítica** — qué encontró la IA (Claude Code / Copilot), qué falló, qué mejoró

---

### C. Verificar que el CI pasa en GitHub

El workflow `.github/workflows/tests.yml` ya existe y es correcto, pero:
- Hacer **push a origin** para que corra en GitHub Actions
- Verificar que los dos jobs (unit-tests y functional-tests) aparecen en verde
- Tomar captura de pantalla para el informe

---

## Criterios de evaluación y estado actual

| Criterio | Peso | Estado |
|----------|------|--------|
| Cobertura total alcanzada | 20% | ⚠️ Falta agregar tests de mensajes y torneos nuevos |
| Uso correcto de herramientas de IA | 20% | ✅ Claude Code usado a lo largo de todo el proyecto |
| Calidad de pruebas (unitarias + funcionales) | 20% | ⚠️ Faltan tests de endpoints nuevos |
| Funcionamiento de CI/CD | 15% | ✅ GitHub Actions configurado, falta push y captura |
| Documentación clara y reflexiva | 15% | ❌ Informe escrito no redactado |
| Presentación y entrega ordenada | 10% | ✅ Repo ordenado, commits descriptivos |

**Prioridad recomendada:** A → C → B
