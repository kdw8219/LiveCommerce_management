import pytest
from fastapi.testclient import TestClient
from app.main import app

#scope : function < class < module < package < session
@pytest.fixture(scope="function")
def client():
    return TestClient(app)
