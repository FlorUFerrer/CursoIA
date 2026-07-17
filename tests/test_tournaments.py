"""
Tests de integración para los endpoints de torneos (app/routers/tournaments.py).

Cubre: listado público, creación (solo tiendas), restricciones de roles.
"""


class TestListTournaments:
    def test_lista_vacia_sin_torneos(self, client):
        resp = client.get("/api/tournaments")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lista_torneos_activos(self, client, store_headers, store_user):
        client.post(
            "/api/tournaments",
            json={"title": "Torneo OP Julio"},
            headers=store_headers,
        )
        resp = client.get("/api/tournaments")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_torneo_incluye_campos_obligatorios(self, client, store_headers, store_user):
        client.post(
            "/api/tournaments",
            json={"title": "Gran Torneo", "event_date": "2026-07-26", "location": "CABA"},
            headers=store_headers,
        )
        torneo = client.get("/api/tournaments").json()[0]
        for field in ("id", "title", "organizer_username", "status", "created_at"):
            assert field in torneo, f"Falta el campo '{field}'"

    def test_lista_es_publica_sin_auth(self, client):
        resp = client.get("/api/tournaments")
        assert resp.status_code == 200

    def test_torneos_ordenados_por_fecha_descendente(self, client, store_headers, store_user):
        client.post("/api/tournaments", json={"title": "Torneo A"}, headers=store_headers)
        client.post("/api/tournaments", json={"title": "Torneo B"}, headers=store_headers)
        torneos = client.get("/api/tournaments").json()
        assert len(torneos) == 2
        # El más reciente primero
        assert torneos[0]["title"] == "Torneo B"


class TestCreateTournament:
    def test_tienda_puede_crear_torneo(self, client, store_headers, store_user):
        resp = client.post(
            "/api/tournaments",
            json={
                "title": "Gran Torneo One Piece",
                "description": "Torneo abierto a todos",
                "event_date": "2026-07-26",
                "location": "Buenos Aires",
            },
            headers=store_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Gran Torneo One Piece"
        assert data["organizer_username"] == "teststore"
        assert data["status"] == "active"
        assert data["event_date"] == "2026-07-26"
        assert data["location"] == "Buenos Aires"

    def test_usuario_regular_no_puede_crear_torneo(self, client, auth_headers, user):
        resp = client.post(
            "/api/tournaments",
            json={"title": "Torneo no autorizado"},
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert "tienda" in resp.json()["detail"].lower()

    def test_requiere_autenticacion(self, client):
        resp = client.post(
            "/api/tournaments",
            json={"title": "Torneo sin auth"},
        )
        assert resp.status_code == 401

    def test_torneo_sin_fecha_ni_lugar(self, client, store_headers, store_user):
        resp = client.post(
            "/api/tournaments",
            json={"title": "Torneo mínimo"},
            headers=store_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_date"] is None
        assert data["location"] is None

    def test_titulo_muy_corto_devuelve_422(self, client, store_headers, store_user):
        resp = client.post(
            "/api/tournaments",
            json={"title": "ab"},
            headers=store_headers,
        )
        assert resp.status_code == 422

    def test_torneo_creado_aparece_en_lista(self, client, store_headers, store_user):
        client.post("/api/tournaments", json={"title": "Torneo visible"}, headers=store_headers)
        torneos = client.get("/api/tournaments").json()
        titulos = [t["title"] for t in torneos]
        assert "Torneo visible" in titulos

    def test_tienda_puede_crear_multiples_torneos(self, client, store_headers, store_user):
        client.post("/api/tournaments", json={"title": "Torneo 1"}, headers=store_headers)
        client.post("/api/tournaments", json={"title": "Torneo 2"}, headers=store_headers)
        resp = client.get("/api/tournaments")
        assert len(resp.json()) == 2


class TestEditTournament:
    def test_organizador_puede_editar(self, client, store_headers, store_user, tournament):
        resp = client.patch(
            f"/api/tournaments/{tournament.id}",
            json={"title": "Torneo Editado", "location": "Rosario"},
            headers=store_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Torneo Editado"
        assert data["location"] == "Rosario"

    def test_otro_usuario_no_puede_editar(self, client, auth_headers, user, tournament):
        resp = client.patch(
            f"/api/tournaments/{tournament.id}",
            json={"title": "Hack"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_requiere_autenticacion(self, client, tournament):
        resp = client.patch(f"/api/tournaments/{tournament.id}", json={"title": "X"})
        assert resp.status_code == 401

    def test_torneo_inexistente_devuelve_404(self, client, store_headers, store_user):
        resp = client.patch("/api/tournaments/99999", json={"location": "Rosario"}, headers=store_headers)
        assert resp.status_code == 404

    def test_edicion_parcial_no_borra_campos(self, client, store_headers, store_user, tournament):
        resp = client.patch(
            f"/api/tournaments/{tournament.id}",
            json={"location": "Córdoba"},
            headers=store_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Torneo Test OP"  # sin cambios
        assert data["location"] == "Córdoba"


class TestCancelTournament:
    def test_organizador_puede_cancelar(self, client, store_headers, store_user, tournament):
        resp = client.post(
            f"/api/tournaments/{tournament.id}/cancel",
            json={"reason": "Falta de inscriptos suficientes"},
            headers=store_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["cancellation_reason"] == "Falta de inscriptos suficientes"

    def test_otro_usuario_no_puede_cancelar(self, client, auth_headers, user, tournament):
        resp = client.post(
            f"/api/tournaments/{tournament.id}/cancel",
            json={"reason": "No autorizado"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_cancelar_torneo_ya_cancelado_falla(self, client, store_headers, store_user, tournament):
        client.post(
            f"/api/tournaments/{tournament.id}/cancel",
            json={"reason": "Primera cancelación"},
            headers=store_headers,
        )
        resp = client.post(
            f"/api/tournaments/{tournament.id}/cancel",
            json={"reason": "Segunda cancelación"},
            headers=store_headers,
        )
        assert resp.status_code == 400

    def test_motivo_muy_corto_devuelve_422(self, client, store_headers, store_user, tournament):
        resp = client.post(
            f"/api/tournaments/{tournament.id}/cancel",
            json={"reason": "abc"},
            headers=store_headers,
        )
        assert resp.status_code == 422

    def test_torneo_cancelado_no_aparece_en_lista_publica(self, client, store_headers, store_user, tournament):
        client.post(
            f"/api/tournaments/{tournament.id}/cancel",
            json={"reason": "Cancelado por fuerza mayor"},
            headers=store_headers,
        )
        torneos = client.get("/api/tournaments").json()
        assert all(t["status"] != "cancelled" for t in torneos)


class TestRegisterTournament:
    def test_usuario_puede_inscribirse(self, client, auth_headers, user, tournament):
        resp = client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tournament_id"] == tournament.id
        assert data["username"] == "testuser"
        assert data["dni_used"] == "12345678"

    def test_organizador_no_puede_inscribirse(self, client, store_headers, store_user, tournament):
        resp = client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "99999999"},
            headers=store_headers,
        )
        assert resp.status_code == 400

    def test_inscripcion_duplicada_falla(self, client, auth_headers, user, tournament):
        client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        resp = client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_cupo_lleno_rechaza_inscripcion(self, client, db, auth_headers, user, store_user, tournament):
        from app.models import TournamentRegistration, User as UserModel
        # Llenar el cupo con usuarios ficticios
        for i in range(tournament.max_participants):
            extra = UserModel(username=f"extra{i}", password_hash="x")
            db.add(extra)
            db.flush()
            db.add(TournamentRegistration(tournament_id=tournament.id, user_id=extra.id, dni_used="00000000"))
        db.commit()
        resp = client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_torneo_cancelado_rechaza_inscripcion(self, client, auth_headers, user, store_headers, store_user, tournament):
        client.post(
            f"/api/tournaments/{tournament.id}/cancel",
            json={"reason": "Cancelado por fuerza mayor"},
            headers=store_headers,
        )
        resp = client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_requiere_autenticacion(self, client, tournament):
        resp = client.post(f"/api/tournaments/{tournament.id}/register", json={"dni": "12345678"})
        assert resp.status_code == 401


class TestUnregisterTournament:
    def test_desanotarse_exitoso(self, client, auth_headers, user, tournament):
        client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        resp = client.delete(f"/api/tournaments/{tournament.id}/register", headers=auth_headers)
        assert resp.status_code == 204

    def test_desanotarse_sin_inscripcion_falla(self, client, auth_headers, user, tournament):
        resp = client.delete(f"/api/tournaments/{tournament.id}/register", headers=auth_headers)
        assert resp.status_code == 404

    def test_requiere_autenticacion(self, client, tournament):
        resp = client.delete(f"/api/tournaments/{tournament.id}/register")
        assert resp.status_code == 401


class TestTournamentRegistrations:
    def test_organizador_ve_inscriptos(self, client, auth_headers, user, store_headers, store_user, tournament):
        client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        resp = client.get(f"/api/tournaments/{tournament.id}/registrations", headers=store_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["username"] == "testuser"
        assert data[0]["dni_used"] == "12345678"

    def test_no_organizador_no_puede_ver_inscriptos(self, client, auth_headers, user, tournament):
        resp = client.get(f"/api/tournaments/{tournament.id}/registrations", headers=auth_headers)
        assert resp.status_code == 403

    def test_requiere_autenticacion(self, client, tournament):
        resp = client.get(f"/api/tournaments/{tournament.id}/registrations")
        assert resp.status_code == 401


class TestMyRegisteredTournaments:
    def test_sin_inscripciones_devuelve_lista_vacia(self, client, auth_headers, user):
        resp = client.get("/api/tournaments/mine-registered", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_devuelve_torneos_donde_esta_inscripto(self, client, auth_headers, user, store_headers, store_user, tournament):
        client.post(
            f"/api/tournaments/{tournament.id}/register",
            json={"dni": "12345678"},
            headers=auth_headers,
        )
        resp = client.get("/api/tournaments/mine-registered", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == tournament.id

    def test_requiere_autenticacion(self, client):
        resp = client.get("/api/tournaments/mine-registered")
        assert resp.status_code == 401
