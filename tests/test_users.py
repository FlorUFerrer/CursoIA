"""
Tests de integración para los endpoints de usuarios (app/routers/users.py).

Cubre: registro, login, /me, /me/stats y campos de roles (is_premium, is_store).
"""


class TestRegister:
    def test_registro_exitoso(self, client):
        resp = client.post(
            "/api/users/register",
            json={"username": "nuevousuario", "password": "pass1234"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["username"] == "nuevousuario"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_registro_devuelve_is_premium_false_por_defecto(self, client):
        resp = client.post(
            "/api/users/register",
            json={"username": "newbie", "password": "pass1234"},
        )
        assert resp.status_code == 201
        assert resp.json()["user"]["is_premium"] is False

    def test_registro_devuelve_is_store_false_por_defecto(self, client):
        resp = client.post(
            "/api/users/register",
            json={"username": "newcomer", "password": "pass1234"},
        )
        assert resp.status_code == 201
        assert resp.json()["user"]["is_store"] is False

    def test_registro_usuario_duplicado_falla(self, client, user):
        resp = client.post(
            "/api/users/register",
            json={"username": "testuser", "password": "cualquierpass"},
        )
        assert resp.status_code == 400
        assert "ya existe" in resp.json()["detail"].lower()

    def test_registro_username_muy_corto_falla(self, client):
        resp = client.post(
            "/api/users/register",
            json={"username": "ab", "password": "pass1234"},
        )
        assert resp.status_code == 422

    def test_registro_password_muy_corta_falla(self, client):
        resp = client.post(
            "/api/users/register",
            json={"username": "validuser", "password": "abc"},
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_exitoso(self, client, user):
        resp = client.post(
            "/api/users/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == "testuser"

    def test_login_devuelve_campos_de_rol(self, client, store_user):
        resp = client.post(
            "/api/users/login",
            json={"username": "teststore", "password": "storepass123"},
        )
        assert resp.status_code == 200
        u = resp.json()["user"]
        assert u["is_store"] is True
        assert u["is_premium"] is False

    def test_login_usuario_premium(self, client, premium_user):
        resp = client.post(
            "/api/users/login",
            json={"username": "premiumuser", "password": "premiumpass123"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["is_premium"] is True

    def test_login_password_incorrecta(self, client, user):
        resp = client.post(
            "/api/users/login",
            json={"username": "testuser", "password": "mal"},
        )
        assert resp.status_code == 401

    def test_login_usuario_inexistente(self, client):
        resp = client.post(
            "/api/users/login",
            json={"username": "noexiste", "password": "pass1234"},
        )
        assert resp.status_code == 401


class TestMe:
    def test_me_devuelve_usuario_actual(self, client, auth_headers, user):
        resp = client.get("/api/users/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_me_sin_token_devuelve_401(self, client):
        resp = client.get("/api/users/me")
        assert resp.status_code == 401

    def test_me_token_invalido_devuelve_401(self, client):
        resp = client.get("/api/users/me", headers={"Authorization": "Bearer token_falso"})
        assert resp.status_code == 401

    def test_me_stats_devuelve_campos_correctos(self, client, auth_headers, user):
        resp = client.get("/api/users/me/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "scans_count" in data
        assert "collection_count" in data
        assert "collection_value" in data
        assert data["username"] == "testuser"

    def test_me_stats_iniciales_en_cero(self, client, auth_headers, user):
        resp = client.get("/api/users/me/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["scans_count"] == 0
        assert data["collection_count"] == 0
        assert data["collection_value"] == 0
