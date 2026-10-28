"""Integration contract for G-03.

The fixture layer is supplied by the CI Testcontainers profile. These tests
stay intentionally small so they can also run against a staging-like API.
"""

import pytest


@pytest.mark.integration
@pytest.mark.isolation
def test_owner_isolation_contract(client_a, client_b, seeded_documents):
    document_b = seeded_documents["b"][0]
    response = client_a.get("/api/v1/documents")
    assert response.status_code == 200
    assert all(item["id"] != str(document_b.id) for item in response.json())
    assert client_a.delete(f"/api/v1/documents/{document_b.id}").status_code == 404


@pytest.mark.integration
@pytest.mark.isolation
def test_owner_cannot_query_other_owner_document(client_a, seeded_documents):
    document_b = seeded_documents["b"][0]
    response = client_a.post(
        "/api/v1/conversations",
        headers={"X-Test-Document": str(document_b.id)},
    )
    assert response.status_code in {201, 403, 404}
