"""
Tests de integración para los endpoints de colección (app/routers/collection.py).

Cubre: GET/POST/DELETE /api/collection y reglas de negocio (duplicados, no encontrado).
"""


class TestGetCollection:
    def test_requiere_autenticacion(self, client):
        resp = client.get("/api/collection")
        assert resp.status_code == 401

    def test_coleccion_inicial_vacia(self, client, auth_headers, user):
        resp = client.get("/api/collection", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["items"] == []
        assert data["total_value"] == 0

    def test_coleccion_incluye_campos_obligatorios(self, client, auth_headers, user):
        resp = client.get("/api/collection", headers=auth_headers)
        assert resp.status_code == 200
        for field in ("count", "items", "total_value"):
            assert field in resp.json()


class TestAddToCollection:
    def test_agrega_carta_exitosamente(self, client, auth_headers, card, user):
        resp = client.post(f"/api/collection/{card.id}", headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["card"]["id"] == card.id

    def test_requiere_autenticacion(self, client, card):
        resp = client.post(f"/api/collection/{card.id}")
        assert resp.status_code == 401

    def test_carta_inexistente_devuelve_404(self, client, auth_headers, user):
        resp = client.post("/api/collection/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_carta_duplicada_devuelve_400(self, client, auth_headers, card, user):
        client.post(f"/api/collection/{card.id}", headers=auth_headers)
        resp = client.post(f"/api/collection/{card.id}", headers=auth_headers)
        assert resp.status_code == 400
        assert "ya está" in resp.json()["detail"].lower()

    def test_contador_aumenta_tras_agregar(self, client, auth_headers, card, user):
        client.post(f"/api/collection/{card.id}", headers=auth_headers)
        resp = client.get("/api/collection", headers=auth_headers)
        assert resp.json()["count"] == 1

    def test_valor_total_aumenta_con_precio_de_carta(self, client, auth_headers, card, user):
        client.post(f"/api/collection/{card.id}", headers=auth_headers)
        resp = client.get("/api/collection", headers=auth_headers)
        assert resp.json()["total_value"] == card.price

    def test_coleccion_de_un_usuario_no_afecta_a_otro(self, client, auth_headers, store_headers, card, user, store_user):
        client.post(f"/api/collection/{card.id}", headers=auth_headers)
        resp = client.get("/api/collection", headers=store_headers)
        assert resp.json()["count"] == 0


class TestRemoveFromCollection:
    def test_elimina_carta_correctamente(self, client, auth_headers, card, user):
        client.post(f"/api/collection/{card.id}", headers=auth_headers)
        resp = client.delete(f"/api/collection/{card.id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_eliminar_reduce_contador(self, client, auth_headers, card, user):
        client.post(f"/api/collection/{card.id}", headers=auth_headers)
        client.delete(f"/api/collection/{card.id}", headers=auth_headers)
        resp = client.get("/api/collection", headers=auth_headers)
        assert resp.json()["count"] == 0

    def test_requiere_autenticacion(self, client, card):
        resp = client.delete(f"/api/collection/{card.id}")
        assert resp.status_code == 401

    def test_carta_no_en_coleccion_devuelve_404(self, client, auth_headers, card, user):
        resp = client.delete(f"/api/collection/{card.id}", headers=auth_headers)
        assert resp.status_code == 404
