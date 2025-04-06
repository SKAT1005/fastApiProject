import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import Base, get_db, app, TronAddressInfo

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(test_db):
    return TestClient(app)


def test_create_address_info(client: TestClient):
    """Юнит-тест для записи в БД."""

    address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    response = client.post(f"/address_info/?address={address}")
    assert response.status_code == 200
    data = response.json()
    assert "address" in data
    assert data["address"] == address

def test_get_address_info_list(client: TestClient, test_db):
    """Интеграционный тест для эндпоинта получения списка."""

    # Add some data to the database
    db = TestingSessionLocal()
    address1 = "TPL6W6Z4R7fKxe8f5zaog9kYk1L5qiuxgQ"
    address2 = "TBWagnyV6FwR5mcjvZx24dF3B2KBkYYonv"

    info1 = TronAddressInfo(address=address1, bandwidth=100, energy=50, balance=1000)
    info2 = TronAddressInfo(address=address2, bandwidth=200, energy=75, balance=2000)

    db.add(info1)
    db.add(info2)
    db.commit()
    db.close()


    response = client.get("/address_info/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    address_in_response = [item['address'] for item in data]
    assert address1 in address_in_response
    assert address2 in address_in_response