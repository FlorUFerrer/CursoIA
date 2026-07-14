"""
Tests de integración para los endpoints de cartas y escaneo (app/routers/cards.py).

Cubre: /cards, /cards/{id}, /scan, /scans/recent, /catalog/sets.
"""


class TestListCards:
    def test_lista_vacia_sin_cartas(self, client):
        resp = client.get("/api/cards")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lista_con_una_carta(self, client, card):
        resp = client.get("/api/cards")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Monkey D. Luffy"
        assert data[0]["code"] == "OP01-001"
        assert data[0]["price"] == 15000

    def test_lista_varias_cartas(self, client, card, second_card):
        resp = client.get("/api/cards")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_filtra_por_set_id(self, client, card):
        resp = client.get("/api/cards?set_id=OP-01")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["set_name"] == "OP-01"

    def test_respuesta_incluye_historial(self, client, card):
        resp = client.get("/api/cards")
        assert resp.status_code == 200
        carta = resp.json()[0]
        assert "history" in carta
        assert len(carta["history"]) == 4  # conftest agrega 4 puntos

    def test_respuesta_incluye_trend(self, client, card):
        resp = client.get("/api/cards")
        assert resp.status_code == 200
        carta = resp.json()[0]
        assert carta["trend"] == 5.2
        assert carta["trend_dir"] == "up"


class TestGetCard:
    def test_obtiene_carta_por_id(self, client, card):
        resp = client.get(f"/api/cards/{card.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == card.id
        assert data["name"] == "Monkey D. Luffy"

    def test_carta_no_encontrada_devuelve_404(self, client):
        resp = client.get("/api/cards/99999")
        assert resp.status_code == 404

    def test_carta_incluye_campos_obligatorios(self, client, card):
        resp = client.get(f"/api/cards/{card.id}")
        data = resp.json()
        for field in ("id", "name", "game", "set_name", "code", "rarity", "price", "trend", "trend_dir", "history"):
            assert field in data, f"Falta el campo '{field}' en la respuesta"


class TestScan:
    def test_escaneo_sin_imagen_devuelve_carta(self, client, card):
        resp = client.post("/api/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert "card" in data
        assert "scan_id" in data
        assert data["method"] == "simulated"

    def test_escaneo_sin_cartas_devuelve_404(self, client):
        # Sin fixture `card`, no hay cartas en la DB
        resp = client.post("/api/scan")
        assert resp.status_code == 404

    def test_escaneo_anonimo_no_requiere_auth(self, client, card):
        resp = client.post("/api/scan")
        assert resp.status_code == 200

    def test_escaneo_autenticado_registra_scan(self, client, auth_headers, card, user, db):
        from app.models import Scan
        resp = client.post("/api/scan", headers=auth_headers)
        assert resp.status_code == 200
        scan_count = db.query(Scan).filter(Scan.user_id == user.id).count()
        assert scan_count == 1

    def test_escaneo_anonimo_registra_scan_sin_usuario(self, client, card, db):
        from app.models import Scan
        resp = client.post("/api/scan")
        assert resp.status_code == 200
        # El scan existe pero sin user_id
        scan = db.query(Scan).first()
        assert scan is not None
        assert scan.user_id is None


class TestRecentScans:
    def test_escaneos_recientes_lista_vacia_por_defecto(self, client):
        resp = client.get("/api/scans/recent")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_escaneos_recientes_devuelve_carta_escaneada(self, client, card):
        client.post("/api/scan")
        resp = client.get("/api/scans/recent")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_escaneos_recientes_respeta_limite(self, client, card, second_card):
        for _ in range(3):
            client.post("/api/scan")
        resp = client.get("/api/scans/recent?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


class TestCatalogSets:
    def test_catalog_sets_devuelve_estructura(self, client):
        resp = client.get("/api/catalog/sets")
        assert resp.status_code == 200
        data = resp.json()
        assert "sets" in data
        assert "default_set_id" in data
        assert isinstance(data["sets"], list)
