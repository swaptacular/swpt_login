import pytest


@pytest.fixture(scope="function")
def client(app, db_session):
    return app.test_client()


def test_404_error(client):
    r = client.get("/login/invalid-path")
    assert r.status_code == 404
