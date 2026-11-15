import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def app_client():
    """One TestClient (one event loop) for the whole run: the Mongo client is bound to it."""
    from fastapi.testclient import TestClient
    import server
    with TestClient(server.app) as c:
        yield c
