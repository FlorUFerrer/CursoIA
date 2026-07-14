"""
Tests de integración para los endpoints del mercado (app/routers/market.py).

Cubre: listado de publicaciones, creación, tipos de listing, reservas y ofertas.
"""


class TestListListings:
    def test_lista_vacia_sin_publicaciones(self, client):
        resp = client.get("/api/market/listings")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lista_publicaciones_activas(self, client, listing):
        resp = client.get("/api/market/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["listing_type"] == "sale"
        assert data[0]["status"] == "active"

    def test_publicacion_incluye_datos_de_carta(self, client, listing):
        resp = client.get("/api/market/listings")
        pub = resp.json()[0]
        assert "card" in pub
        assert pub["card"]["name"] == "Monkey D. Luffy"

    def test_publicacion_incluye_datos_de_vendedor(self, client, listing):
        resp = client.get("/api/market/listings")
        pub = resp.json()[0]
        assert pub["seller_username"] == "teststore"


class TestCreateListing:
    def test_requiere_autenticacion(self, client, card):
        resp = client.post(
            "/api/market/listings",
            json={"card_id": card.id, "listing_type": "sale", "price": 5000},
        )
        assert resp.status_code == 401

    def test_crea_publicacion_venta(self, client, auth_headers, card, user):
        resp = client.post(
            "/api/market/listings",
            json={"card_id": card.id, "listing_type": "sale", "price": 12000},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["listing_type"] == "sale"
        assert data["price"] == 12000

    def test_crea_publicacion_intercambio(self, client, auth_headers, card, user):
        resp = client.post(
            "/api/market/listings",
            json={"card_id": card.id, "listing_type": "trade", "wants": "Busco Zoro"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["listing_type"] == "trade"
        assert data["price"] is None  # trade no tiene precio

    def test_crea_publicacion_negociable(self, client, auth_headers, card, user):
        resp = client.post(
            "/api/market/listings",
            json={"card_id": card.id, "listing_type": "negotiable"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_crea_publicacion_combo(self, client, auth_headers, card, user):
        resp = client.post(
            "/api/market/listings",
            json={"card_id": card.id, "listing_type": "combo", "wants": "Carta + efectivo"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_tipo_invalido_devuelve_400(self, client, auth_headers, card, user):
        resp = client.post(
            "/api/market/listings",
            json={"card_id": card.id, "listing_type": "subasta"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_carta_inexistente_devuelve_404(self, client, auth_headers, user):
        resp = client.post(
            "/api/market/listings",
            json={"card_id": 99999, "listing_type": "sale"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestReserveListing:
    def test_reserva_exitosa(self, client, auth_headers, user, listing):
        resp = client.post(f"/api/market/listings/{listing.id}/reserve", headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["listing_id"] == listing.id
        assert data["status"] == "active"

    def test_requiere_autenticacion(self, client, listing):
        resp = client.post(f"/api/market/listings/{listing.id}/reserve")
        assert resp.status_code == 401

    def test_no_puede_reservar_propia_publicacion(self, client, store_headers, store_user, listing):
        resp = client.post(f"/api/market/listings/{listing.id}/reserve", headers=store_headers)
        assert resp.status_code == 400

    def test_reserva_duplicada_falla(self, client, auth_headers, user, listing):
        client.post(f"/api/market/listings/{listing.id}/reserve", headers=auth_headers)
        resp = client.post(f"/api/market/listings/{listing.id}/reserve", headers=auth_headers)
        assert resp.status_code == 400

    def test_publicacion_inexistente_devuelve_404(self, client, auth_headers, user):
        resp = client.post("/api/market/listings/99999/reserve", headers=auth_headers)
        assert resp.status_code == 404


class TestCreateOffer:
    def test_oferta_en_dinero_exitosa(self, client, auth_headers, user, listing):
        resp = client.post(
            f"/api/market/listings/{listing.id}/offers",
            json={"money_offer": 10000},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["money_offer"] == 10000
        assert data["status"] == "pending"

    def test_oferta_en_cartas_exitosa(self, client, auth_headers, user, listing):
        resp = client.post(
            f"/api/market/listings/{listing.id}/offers",
            json={"cards_offer": "Zoro OP01-002"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_oferta_mixta_dinero_y_cartas(self, client, auth_headers, user, listing):
        resp = client.post(
            f"/api/market/listings/{listing.id}/offers",
            json={"money_offer": 5000, "cards_offer": "Nami OP01-016"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_oferta_vacia_devuelve_400(self, client, auth_headers, user, listing):
        resp = client.post(
            f"/api/market/listings/{listing.id}/offers",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_no_puede_ofertar_en_propia_publicacion(self, client, store_headers, store_user, listing):
        resp = client.post(
            f"/api/market/listings/{listing.id}/offers",
            json={"money_offer": 5000},
            headers=store_headers,
        )
        assert resp.status_code == 400

    def test_requiere_autenticacion(self, client, listing):
        resp = client.post(
            f"/api/market/listings/{listing.id}/offers",
            json={"money_offer": 5000},
        )
        assert resp.status_code == 401


class TestListOffers:
    def test_vendedor_puede_ver_ofertas(self, client, auth_headers, store_headers, user, store_user, listing):
        # Comprador hace oferta
        client.post(
            f"/api/market/listings/{listing.id}/offers",
            json={"money_offer": 8000},
            headers=auth_headers,
        )
        # Vendedor consulta
        resp = client.get(f"/api/market/listings/{listing.id}/offers", headers=store_headers)
        assert resp.status_code == 200
        ofertas = resp.json()
        assert len(ofertas) == 1
        assert ofertas[0]["money_offer"] == 8000
        assert ofertas[0]["buyer_username"] == "testuser"

    def test_no_vendedor_no_puede_ver_ofertas(self, client, auth_headers, listing):
        resp = client.get(f"/api/market/listings/{listing.id}/offers", headers=auth_headers)
        assert resp.status_code == 403

    def test_requiere_autenticacion(self, client, listing):
        resp = client.get(f"/api/market/listings/{listing.id}/offers")
        assert resp.status_code == 401
