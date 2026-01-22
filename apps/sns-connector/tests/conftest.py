import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("KAKAO_BUFFER_ENABLED", "0")

from app.main import app


@pytest.fixture(scope="function")
def client():
    return TestClient(app)
