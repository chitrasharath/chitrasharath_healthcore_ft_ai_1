from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.db import get_supabase_db
from app.domains.inventory import models as inventory_models  # noqa: F401
from app.main import app
from tests.auth_helpers import auth_headers

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="inventory_session")
def inventory_session_fixture():
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(inventory_session):
    def override():
        with Session(inventory_session) as session:
            yield session

    app.dependency_overrides[get_supabase_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def bearer(client: TestClient) -> dict[str, str]:
    return auth_headers(client)


VALID_PRODUCT = {
    "name": "Test Syringe",
    "sku": "HCR-TEST-001",
    "category": "consumables",
    "unit": "unit",
    "country": "US",
}


def _create_product(client: TestClient, bearer: dict[str, str]) -> dict:
    response = client.post("/api/v1/inventory/products", json=VALID_PRODUCT, headers=bearer)
    assert response.status_code == 201
    return response.json()


def test_post_product_creates_with_zero_stock(client: TestClient, bearer: dict[str, str]) -> None:
    data = _create_product(client, bearer)
    assert data["current_stock"] == 0
    assert data["sku"] == VALID_PRODUCT["sku"]


def test_post_product_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/inventory/products", json=VALID_PRODUCT)
    assert response.status_code == 401


def test_get_products_computes_stock(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    client.post(
        "/api/v1/inventory/orders/inbound",
        json={
            "supply_id": product["id"],
            "quantity": 50,
            "vendor_name": "Test Vendor",
            "clinic_id": 1,
        },
        headers=bearer,
    )
    client.post(
        "/api/v1/inventory/orders/outbound",
        json={
            "supply_id": product["id"],
            "quantity": 10,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
        headers=bearer,
    )
    response = client.get("/api/v1/inventory/products")
    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()}
    assert items[product["id"]]["current_stock"] == 40


def test_get_product_by_id(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    response = client.get(f"/api/v1/inventory/products/{product['id']}")
    assert response.status_code == 200
    assert response.json()["current_stock"] == 0


def test_get_product_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/inventory/products/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_post_inbound_increases_stock(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    response = client.post(
        "/api/v1/inventory/orders/inbound",
        json={
            "supply_id": product["id"],
            "quantity": 25,
            "vendor_name": "MedLine Industries",
            "clinic_id": 2,
        },
        headers=bearer,
    )
    assert response.status_code == 201
    stock_response = client.get(f"/api/v1/inventory/products/{product['id']}")
    assert stock_response.json()["current_stock"] == 25


def test_post_outbound_decreases_stock(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    client.post(
        "/api/v1/inventory/orders/inbound",
        json={
            "supply_id": product["id"],
            "quantity": 30,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
        },
        headers=bearer,
    )
    response = client.post(
        "/api/v1/inventory/orders/outbound",
        json={
            "supply_id": product["id"],
            "quantity": 12,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
        headers=bearer,
    )
    assert response.status_code == 201
    stock_response = client.get(f"/api/v1/inventory/products/{product['id']}")
    assert stock_response.json()["current_stock"] == 18


def test_outbound_rejects_insufficient_stock(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    client.post(
        "/api/v1/inventory/orders/inbound",
        json={
            "supply_id": product["id"],
            "quantity": 5,
            "vendor_name": "MedLine Industries",
            "clinic_id": 1,
        },
        headers=bearer,
    )
    response = client.post(
        "/api/v1/inventory/orders/outbound",
        json={
            "supply_id": product["id"],
            "quantity": 10,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
        headers=bearer,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Insufficient stock for supply '{VALID_PRODUCT['name']}'. Available: 5, requested: 10."
    )


def test_invalid_consumption_type(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    response = client.post(
        "/api/v1/inventory/orders/outbound",
        json={
            "supply_id": product["id"],
            "quantity": 1,
            "consumption_type": "stolen",
            "clinic_id": 1,
        },
        headers=bearer,
    )
    assert response.status_code == 422


def test_get_orders_combined(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    client.post(
        "/api/v1/inventory/orders/inbound",
        json={
            "supply_id": product["id"],
            "quantity": 20,
            "vendor_name": "Bound Tree Medical",
            "clinic_id": 3,
        },
        headers=bearer,
    )
    client.post(
        "/api/v1/inventory/orders/outbound",
        json={
            "supply_id": product["id"],
            "quantity": 5,
            "consumption_type": "expiry_waste",
            "clinic_id": 3,
        },
        headers=bearer,
    )
    response = client.get("/api/v1/inventory/orders")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 2
    types = {order["order_type"] for order in orders}
    assert types == {"inbound", "outbound"}
    for order in orders:
        assert order["supply_name"] == VALID_PRODUCT["name"]
        assert order["supply_id"] == product["id"]


def test_inbound_requires_auth(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    response = client.post(
        "/api/v1/inventory/orders/inbound",
        json={
            "supply_id": product["id"],
            "quantity": 10,
            "vendor_name": "Vendor",
            "clinic_id": 1,
        },
    )
    assert response.status_code == 401


def test_stock_net_after_multiple_orders(client: TestClient, bearer: dict[str, str]) -> None:
    product = _create_product(client, bearer)
    for qty in (100, 50):
        client.post(
            "/api/v1/inventory/orders/inbound",
            json={
                "supply_id": product["id"],
                "quantity": qty,
                "vendor_name": "MedLine Industries",
                "clinic_id": 1,
            },
            headers=bearer,
        )
    for qty in (20, 5):
        client.post(
            "/api/v1/inventory/orders/outbound",
            json={
                "supply_id": product["id"],
                "quantity": qty,
                "consumption_type": "clinical_use",
                "clinic_id": 1,
            },
            headers=bearer,
        )
    response = client.get(f"/api/v1/inventory/products/{product['id']}")
    assert response.json()["current_stock"] == 125
