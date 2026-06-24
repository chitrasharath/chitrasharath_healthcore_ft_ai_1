from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domains.procurement.suppliers import store as supplier_store
from app.main import app
from tests.auth_helpers import auth_headers
from app.seed import run_seed

VALID_SUPPLIER = {
    "name": "Test Supplier Co",
    "country": "USA",
    "categories": ["medical_supplies"],
    "monthly_rate": 1500.0,
    "currency": "USD",
    "status": "active",
}


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path) -> None:
    db_path = tmp_path / "suppliers_test.json"
    supplier_store.reset_db(db_path)
    supplier_store.clear_all()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def bearer(client: TestClient) -> dict[str, str]:
    return auth_headers(client)


def test_seed_inserts_fifteen_on_first_run() -> None:
    inserted, skipped = run_seed()
    assert inserted == 15
    assert skipped == 0


def test_seed_is_idempotent() -> None:
    run_seed()
    inserted, skipped = run_seed()
    assert inserted == 0
    assert skipped == 15


def test_post_valid_supplier(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] >= 1
    assert data["name"] == VALID_SUPPLIER["name"]
    assert data["rate_updated_at"] is not None


def test_post_missing_country(client: TestClient, bearer: dict[str, str]) -> None:
    payload = {**VALID_SUPPLIER}
    del payload["country"]
    response = client.post("/api/v1/suppliers", json=payload, headers=bearer)
    assert response.status_code == 422


def test_post_usa_gbp_mismatch(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "currency": "GBP"},
        headers=bearer,
    )
    assert response.status_code == 422


def test_post_zero_rate(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "monthly_rate": 0},
        headers=bearer,
    )
    assert response.status_code == 422


def test_post_negative_rate(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "monthly_rate": -50},
        headers=bearer,
    )
    assert response.status_code == 422


def test_post_invalid_status(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "status": "deleted"},
        headers=bearer,
    )
    assert response.status_code == 422


def test_post_empty_categories(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "categories": []},
        headers=bearer,
    )
    assert response.status_code == 422


def test_post_unknown_category(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/suppliers",
        json={**VALID_SUPPLIER, "categories": ["unknown_thing"]},
        headers=bearer,
    )
    assert response.status_code == 422


def test_post_duplicate_name(client: TestClient, bearer: dict[str, str]) -> None:
    client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer)
    response = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer)
    assert response.status_code == 422
    assert "already exists" in response.json()["detail"]


def test_get_all_after_seed(client: TestClient, bearer: dict[str, str]) -> None:
    run_seed()
    response = client.get("/api/v1/suppliers", headers=bearer)
    assert response.status_code == 200
    assert len(response.json()) == 15


def test_get_filter_country_usa(client: TestClient, bearer: dict[str, str]) -> None:
    run_seed()
    response = client.get("/api/v1/suppliers", params={"country": "USA"}, headers=bearer)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 9
    assert all(item["country"] == "USA" for item in data)


def test_get_filter_category_clinical_software(client: TestClient, bearer: dict[str, str]) -> None:
    run_seed()
    response = client.get("/api/v1/suppliers", params={"category": "clinical_software"}, headers=bearer)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {item["name"] for item in data}
    assert names == {"Epic Systems", "EMIS Health"}


def test_get_supplier_by_id(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    response = client.get(f"/api/v1/suppliers/{created['id']}", headers=bearer)
    assert response.status_code == 200
    assert response.json()["name"] == VALID_SUPPLIER["name"]


def test_get_supplier_not_found(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.get("/api/v1/suppliers/9999", headers=bearer)
    assert response.status_code == 404


def test_patch_rate_valid(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    original_updated = created["rate_updated_at"]
    response = client.patch(
        f"/api/v1/suppliers/{created['id']}/rate",
        json={"monthly_rate": 5000},
        headers=bearer,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["monthly_rate"] == 5000
    assert data["rate_updated_at"] != original_updated


def test_patch_rate_zero(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    response = client.patch(
        f"/api/v1/suppliers/{created['id']}/rate",
        json={"monthly_rate": 0},
        headers=bearer,
    )
    assert response.status_code == 422


def test_patch_rate_negative(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    response = client.patch(
        f"/api/v1/suppliers/{created['id']}/rate",
        json={"monthly_rate": -100},
        headers=bearer,
    )
    assert response.status_code == 422


def test_patch_status_suspended(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    response = client.patch(
        f"/api/v1/suppliers/{created['id']}/status",
        json={"status": "suspended"},
        headers=bearer,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


def test_patch_status_invalid(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    response = client.patch(
        f"/api/v1/suppliers/{created['id']}/status",
        json={"status": "archived"},
        headers=bearer,
    )
    assert response.status_code == 422


def test_patch_details_updates_optional_fields(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    response = client.patch(
        f"/api/v1/suppliers/{created['id']}/details",
        json={
            "compliance_agreement": "BAA",
            "contract_renewal_date": "2026-12-31",
            "contact_email": "ops@example.com",
            "notes": "Added via detail update",
        },
        headers=bearer,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["compliance_agreement"] == "BAA"
    assert data["contract_renewal_date"] == "2026-12-31"
    assert data["contact_email"] == "ops@example.com"
    assert data["notes"] == "Added via detail update"


def test_patch_details_invalid_date(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    response = client.patch(
        f"/api/v1/suppliers/{created['id']}/details",
        json={"contract_renewal_date": "31-12-2026"},
        headers=bearer,
    )
    assert response.status_code == 422


def test_delete_soft_suspends(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/suppliers", json=VALID_SUPPLIER, headers=bearer).json()
    supplier_id = created["id"]
    response = client.delete(f"/api/v1/suppliers/{supplier_id}", headers=bearer)
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"
    still_there = client.get(f"/api/v1/suppliers/{supplier_id}", headers=bearer)
    assert still_there.status_code == 200


def test_delete_not_found(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.delete("/api/v1/suppliers/9999", headers=bearer)
    assert response.status_code == 404


def test_seeded_records_have_rate_updated_at(client: TestClient, bearer: dict[str, str]) -> None:
    run_seed()
    response = client.get("/api/v1/suppliers", headers=bearer)
    for supplier in response.json():
        assert supplier["rate_updated_at"] is not None


def test_invalid_country_query(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.get("/api/v1/suppliers", params={"country": "CA"}, headers=bearer)
    assert response.status_code == 422


def test_invalid_category_query(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.get("/api/v1/suppliers", params={"category": "unknown_thing"}, headers=bearer)
    assert response.status_code == 422


def test_list_suppliers_without_token_returns_401(client: TestClient) -> None:
    response = client.get('/api/v1/suppliers')
    assert response.status_code == 401


def test_create_supplier_missing_required_fields_returns_422(
    client: TestClient,
    bearer: dict[str, str],
) -> None:
    response = client.post("/api/v1/suppliers", json={}, headers=bearer)
    assert response.status_code == 422


def test_patch_supplier_details_not_found_returns_404(
    client: TestClient,
    bearer: dict[str, str],
) -> None:
    response = client.patch(
        "/api/v1/suppliers/99999/details",
        json={"notes": "missing supplier"},
        headers=bearer,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Supplier not found"


@pytest.mark.parametrize(
    "override",
    [
        {"monthly_rate": 0},
        {"country": ""},
        {"categories": ["not_a_real_category"]},
    ],
)
def test_supplier_schema_validation_edge_cases(
    client: TestClient,
    bearer: dict[str, str],
    override: dict,
) -> None:
    payload = {**VALID_SUPPLIER, **override}
    response = client.post("/api/v1/suppliers", json=payload, headers=bearer)
    assert response.status_code == 422
