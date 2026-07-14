"""
Tests unitarios para las funciones de autenticación (app/auth.py).

No usan base de datos ni HTTP — son tests puramente unitarios de las
funciones de hash, verificación y generación de tokens JWT.
"""
import time

import pytest
from jose import jwt

from app.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
)


# ── hash_password ─────────────────────────────────────────────────────────────

class TestHashPassword:
    def test_resultado_no_es_texto_plano(self):
        hashed = hash_password("micontraseña")
        assert hashed != "micontraseña"

    def test_hash_es_string_no_vacio(self):
        hashed = hash_password("abc123")
        assert isinstance(hashed, str)
        assert len(hashed) > 10

    def test_misma_password_genera_hashes_distintos(self):
        """bcrypt usa salt aleatorio: dos hashes de la misma password difieren."""
        h1 = hash_password("igual")
        h2 = hash_password("igual")
        assert h1 != h2

    def test_password_vacia_se_hashea(self):
        hashed = hash_password("")
        assert isinstance(hashed, str)


# ── verify_password ───────────────────────────────────────────────────────────

class TestVerifyPassword:
    def test_password_correcta_verifica(self):
        hashed = hash_password("secreto")
        assert verify_password("secreto", hashed) is True

    def test_password_incorrecta_falla(self):
        hashed = hash_password("secreto")
        assert verify_password("equivocado", hashed) is False

    def test_password_vacia_vs_hash_de_vacia(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_password_con_caracteres_especiales(self):
        pwd = "P@$$w0rd!#áéü"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_no_verifica_con_hash_diferente(self):
        h1 = hash_password("abc")
        assert verify_password("abc", hash_password("xyz")) is False


# ── create_access_token ───────────────────────────────────────────────────────

class TestCreateAccessToken:
    def test_token_contiene_user_id(self):
        token = create_access_token(42, "alice")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "42"

    def test_token_contiene_username(self):
        token = create_access_token(1, "bob")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["username"] == "bob"

    def test_token_tiene_expiracion(self):
        token = create_access_token(1, "carol")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_token_expira_en_72_horas(self):
        token = create_access_token(1, "dave")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # La expiración debe ser ~72 horas desde ahora (tolerancia ±60s)
        expected = time.time() + 72 * 3600
        assert abs(payload["exp"] - expected) < 60

    def test_tokens_distintos_para_usuarios_distintos(self):
        t1 = create_access_token(1, "user1")
        t2 = create_access_token(2, "user2")
        assert t1 != t2

    def test_token_firmado_con_secret_correcto(self):
        token = create_access_token(5, "eve")
        # Debe decodificarse sin errores
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload is not None

    def test_token_invalido_con_secret_incorrecto(self):
        from jose import JWTError
        token = create_access_token(5, "eve")
        with pytest.raises(JWTError):
            jwt.decode(token, "clave-incorrecta", algorithms=[ALGORITHM])
