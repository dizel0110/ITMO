import os
import sys

import json
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.api.app import app

client = TestClient(app)


def test_integration():
    pass