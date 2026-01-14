import pytest
from app.main import app

#scope : function < class < module < package < session
@pytest.fixture(scope="session")
def test_router():
    pass