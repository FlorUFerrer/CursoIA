"""
Tests de integración para los endpoints de mensajes (app/routers/messages.py).

Cubre: historial de mensajes y listado de chats propios.
"""
from app.models import Message


class TestGetMessages:
    def test_historial_vacio(self, client, auth_headers, user, listing):
        resp = client.get(f"/api/messages/{listing.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requiere_autenticacion(self, client, listing):
        resp = client.get(f"/api/messages/{listing.id}")
        assert resp.status_code == 401

    def test_devuelve_mensajes_guardados(self, client, db, auth_headers, user, listing):
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Hola, sigue disponible?"))
        db.commit()
        resp = client.get(f"/api/messages/{listing.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["content"] == "Hola, sigue disponible?"
        assert data[0]["sender_username"] == "testuser"

    def test_mensajes_ordenados_por_fecha_asc(self, client, db, auth_headers, user, listing):
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Primero"))
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Segundo"))
        db.commit()
        resp = client.get(f"/api/messages/{listing.id}", headers=auth_headers)
        msgs = resp.json()
        assert msgs[0]["content"] == "Primero"
        assert msgs[1]["content"] == "Segundo"

    def test_mensaje_incluye_campos_requeridos(self, client, db, auth_headers, user, listing):
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Test"))
        db.commit()
        msg = client.get(f"/api/messages/{listing.id}", headers=auth_headers).json()[0]
        for field in ("id", "listing_id", "sender_id", "sender_username", "content", "created_at"):
            assert field in msg


class TestGetMyChats:
    def test_sin_mensajes_devuelve_lista_vacia(self, client, auth_headers, user):
        resp = client.get("/api/messages/mine", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requiere_autenticacion(self, client):
        resp = client.get("/api/messages/mine")
        assert resp.status_code == 401

    def test_aparece_chat_donde_el_usuario_envio_mensaje(self, client, db, auth_headers, user, listing):
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Hola"))
        db.commit()
        resp = client.get("/api/messages/mine", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["listing_id"] == listing.id

    def test_aparece_chat_donde_el_usuario_es_vendedor(self, client, db, store_headers, store_user, user, listing):
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Disponible?"))
        db.commit()
        resp = client.get("/api/messages/mine", headers=store_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["listing_id"] == listing.id

    def test_chat_summary_incluye_campos_requeridos(self, client, db, auth_headers, user, listing):
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Test"))
        db.commit()
        chat = client.get("/api/messages/mine", headers=auth_headers).json()[0]
        for field in ("listing_id", "card_name", "seller_username", "listing_type", "last_content", "last_at", "last_sender"):
            assert field in chat

    def test_last_content_es_el_ultimo_mensaje(self, client, db, auth_headers, user, listing):
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Primero"))
        db.add(Message(listing_id=listing.id, sender_id=user.id, content="Ultimo"))
        db.commit()
        chat = client.get("/api/messages/mine", headers=auth_headers).json()[0]
        assert chat["last_content"] == "Ultimo"
