import pytest
import uuid
import chromadb
from shared.brain import MatrixBrain


@pytest.fixture
def brain():
    """Fresh ephemeral brain for each test."""
    # Create a unique collection name for each test to ensure isolation
    unique_name = f"matrix_brain_test_{uuid.uuid4().hex[:8]}"
    client = chromadb.EphemeralClient()
    brain = MatrixBrain(mode="ephemeral")
    brain._client = client
    brain._collection = client.get_or_create_collection(
        name=unique_name,
        metadata={"description": "Matrix Agent Team shared memory test"},
    )
    return brain
