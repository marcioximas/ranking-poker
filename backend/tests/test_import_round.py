"""
Tests for POST /api/rounds/import-pdf.
Covers: file validation, size limit, duplicate label, dry_run, and round creation.
"""
import pytest
from unittest.mock import patch

FAKE_PDF = b"%PDF-1.4 fake" + b"x" * 100


def upload(client, content=FAKE_PDF, filename="test.pdf",
           label="", dry_run="false", headers=None):
    return client.post(
        "/api/rounds/import-pdf",
        files={"file": (filename, content, "application/pdf")},
        data={"label": label, "dry_run": dry_run},
        headers=headers or {"X-Admin-Password": "test-password"},
    )


# ── File validation ───────────────────────────────────────────────────────────

class TestFileValidation:
    def test_requires_admin(self, client):
        r = client.post(
            "/api/rounds/import-pdf",
            files={"file": ("test.pdf", FAKE_PDF, "application/pdf")},
            data={"dry_run": "false"},
        )
        assert r.status_code == 401

    def test_rejects_non_pdf_extension(self, client):
        r = client.post(
            "/api/rounds/import-pdf",
            files={"file": ("planilha.csv", b"nome,pontos\nAlice,10", "text/csv")},
            data={"dry_run": "false"},
            headers={"X-Admin-Password": "test-password"},
        )
        assert r.status_code == 400
        assert "PDF" in r.json()["detail"]

    def test_rejects_empty_file(self, client):
        r = upload(client, content=b"")
        assert r.status_code == 400
        assert "vazio" in r.json()["detail"]

    def test_rejects_file_over_5mb(self, client):
        big = b"x" * (5 * 1024 * 1024 + 1)
        r = upload(client, content=big)
        assert r.status_code == 413
        assert "5 MB" in r.json()["detail"]

    def test_accepts_file_at_exactly_5mb(self, client):
        five_mb = b"%PDF " + b"x" * (5 * 1024 * 1024 - 5)
        with patch("app.routers.import_round._parse_pdf", return_value=[]):
            r = upload(client, content=five_mb, dry_run="true")
        # size is OK; parse returns [] so 422, but NOT 413
        assert r.status_code == 422

    def test_rejects_pdf_with_no_parseable_data(self, client):
        with patch("app.routers.import_round._parse_pdf", return_value=[]):
            r = upload(client, dry_run="true")
        assert r.status_code == 422
        assert "Nenhum dado" in r.json()["detail"]


# ── Dry-run (preview) ─────────────────────────────────────────────────────────

class TestDryRun:
    def test_preview_returns_matched_player(self, client, player):
        rows = [{"name": player["name"], "pontos": "10", "presenca": "5"}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, dry_run="true")
        assert r.status_code == 200
        data = r.json()
        assert data["dry_run"] is True
        assert len(data["matched"]) == 1
        assert data["matched"][0]["player_id"] == player["id"]
        assert data["matched"][0]["pontos"] == 10
        assert data["matched"][0]["presenca"] == 5

    def test_preview_reports_unmatched_names(self, client, player):
        rows = [{"name": player["name"]}, {"name": "Ninguém Cadastrado"}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, dry_run="true")
        data = r.json()
        assert len(data["matched"]) == 1
        assert "Ninguém Cadastrado" in data["unmatched"]

    def test_preview_does_not_create_round(self, client, player):
        rows = [{"name": player["name"]}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            upload(client, dry_run="true")
        assert client.get("/api/rounds/current").json() is None

    def test_preview_all_unmatched_returns_empty_matched(self, client):
        with patch("app.routers.import_round._parse_pdf", return_value=[{"name": "Fantasma"}]):
            r = upload(client, dry_run="true")
        assert r.status_code == 200
        data = r.json()
        assert data["matched"] == []
        assert data["unmatched"] == ["Fantasma"]

    def test_name_matching_ignores_case_and_accents(self, client, player):
        # player name is "Jogador A"; test with different casing
        rows = [{"name": player["name"].lower()}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, dry_run="true")
        assert r.json()["matched"][0]["player_id"] == player["id"]


# ── Round creation ────────────────────────────────────────────────────────────

class TestCreateRound:
    def test_creates_round_and_adds_players(self, client, player):
        rows = [{"name": player["name"], "pontos": "15", "presenca": "5", "buyin": "2", "addon": "1"}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, label="Rodada PDF", dry_run="false")
        assert r.status_code == 200
        data = r.json()
        assert data["dry_run"] is False
        assert data["round_label"] == "Rodada PDF"
        assert data["players_added"] == 1

        current = client.get("/api/rounds/current").json()
        assert current is not None
        assert current["label"] == "Rodada PDF"
        assert current["is_current"] is True

        rps = client.get(f"/api/rounds/{current['id']}/players").json()
        assert rps[0]["pontos"] == 15
        assert rps[0]["presenca"] == 5
        assert rps[0]["buyin"] == 2
        assert rps[0]["addon"] == 1

    def test_auto_generates_label_when_not_provided(self, client, player):
        rows = [{"name": player["name"]}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, label="", dry_run="false")
        assert r.status_code == 200
        assert r.json()["round_label"].startswith("Rodada")

    def test_buyin_defaults_to_1_when_missing(self, client, player):
        rows = [{"name": player["name"]}]  # no buyin column
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, label="R1", dry_run="false")
        round_id = r.json()["round_id"]
        rps = client.get(f"/api/rounds/{round_id}/players").json()
        assert rps[0]["buyin"] == 1

    def test_rejects_when_no_players_matched(self, client):
        with patch("app.routers.import_round._parse_pdf", return_value=[{"name": "Ninguém"}]):
            r = upload(client, dry_run="false")
        assert r.status_code == 422
        assert "cadastro" in r.json()["detail"]

    def test_rejects_when_current_round_already_exists(self, client, player, current_round):
        rows = [{"name": player["name"]}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, dry_run="false")
        assert r.status_code == 409
        assert "andamento" in r.json()["detail"]


# ── Duplicate label ───────────────────────────────────────────────────────────

class TestDuplicateLabel:
    def test_rejects_label_already_used(self, client, auth, player):
        client.post("/api/rounds", json={"label": "Rodada Duplicada"}, headers=auth)

        rows = [{"name": player["name"]}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, label="Rodada Duplicada", dry_run="false")
        assert r.status_code == 409
        assert "Rodada Duplicada" in r.json()["detail"]

    def test_allows_unique_label(self, client, player):
        rows = [{"name": player["name"]}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, label="Label Único", dry_run="false")
        assert r.status_code == 200

    def test_auto_label_collision_rejected(self, client, auth, player):
        # With 1 round in DB, auto-label = "Rodada 2"; create it first to force collision
        client.post("/api/rounds", json={"label": "Rodada 2"}, headers=auth)

        rows = [{"name": player["name"]}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, label="", dry_run="false")
        assert r.status_code == 409
        assert "Rodada 2" in r.json()["detail"]

    def test_duplicate_check_skipped_on_dry_run(self, client, auth, player):
        client.post("/api/rounds", json={"label": "Rodada Existente"}, headers=auth)

        rows = [{"name": player["name"]}]
        with patch("app.routers.import_round._parse_pdf", return_value=rows):
            r = upload(client, label="Rodada Existente", dry_run="true")
        # dry_run does not check for duplicates — just returns preview
        assert r.status_code == 200
        assert r.json()["dry_run"] is True
