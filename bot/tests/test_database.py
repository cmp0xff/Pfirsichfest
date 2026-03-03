# ruff: noqa: PLR2004
"""Tests for the database abstraction layer."""

from bot.database import InMemoryDatabaseClient, create_database_client


class TestInMemoryDatabaseClient:
    """Tests for InMemoryDatabaseClient."""

    def test_set_and_get_document(self):
        """Documents stored with set() can be retrieved via where().stream()."""
        db = InMemoryDatabaseClient()
        db.collection("downloads").document("doc1").set(
            {"chat_id": 123, "status": "provisioning_vm", "magnet": "magnet:?xt=..."}
        )
        results = list(
            db.collection("downloads").where("status", "==", "provisioning_vm").stream()
        )
        assert len(results) == 1
        assert results[0].id == "doc1"
        data = results[0].to_dict()
        assert data is not None
        assert data["chat_id"] == 123
        assert data["status"] == "provisioning_vm"

    def test_update_document(self):
        """update() merges fields into an existing document."""
        db = InMemoryDatabaseClient()
        db.collection("downloads").document("doc1").set(
            {"status": "provisioning_vm", "magnet": "magnet:?xt=..."}
        )
        db.collection("downloads").document("doc1").update({"status": "downloading"})

        results = list(
            db.collection("downloads").where("status", "==", "downloading").stream()
        )
        assert len(results) == 1
        data = results[0].to_dict()
        assert data is not None
        assert data["magnet"] == "magnet:?xt=..."

    def test_update_nonexistent_document(self):
        """update() on a non-existent document creates it (graceful fallback)."""
        db = InMemoryDatabaseClient()
        db.collection("downloads").document("doc1").update({"status": "downloading"})

        results = list(
            db.collection("downloads").where("status", "==", "downloading").stream()
        )
        assert len(results) == 1

    def test_where_not_equal(self):
        """where() supports the != operator."""
        db = InMemoryDatabaseClient()
        db.collection("downloads").document("doc1").set({"status": "completed"})
        db.collection("downloads").document("doc2").set({"status": "downloading"})
        db.collection("downloads").document("doc3").set({"status": "provisioning_vm"})

        results = list(
            db.collection("downloads").where("status", "!=", "completed").stream()
        )
        assert len(results) == 2
        ids = {r.id for r in results}
        assert ids == {"doc2", "doc3"}

    def test_where_no_matches(self):
        """where() returns empty list when no documents match."""
        db = InMemoryDatabaseClient()
        db.collection("downloads").document("doc1").set({"status": "completed"})

        results = list(
            db.collection("downloads").where("status", "==", "downloading").stream()
        )
        assert len(results) == 0

    def test_empty_collection(self):
        """Querying an empty collection returns no results."""
        db = InMemoryDatabaseClient()
        results = list(
            db.collection("nonexistent").where("field", "==", "value").stream()
        )
        assert len(results) == 0

    def test_multiple_collections(self):
        """Documents in different collections are isolated."""
        db = InMemoryDatabaseClient()
        db.collection("downloads").document("d1").set({"status": "active"})
        db.collection("uploads").document("u1").set({"status": "active"})

        downloads = list(
            db.collection("downloads").where("status", "==", "active").stream()
        )
        uploads = list(
            db.collection("uploads").where("status", "==", "active").stream()
        )
        assert len(downloads) == 1
        assert downloads[0].id == "d1"
        assert len(uploads) == 1
        assert uploads[0].id == "u1"

    def test_to_dict_returns_copy(self):
        """to_dict() returns a copy so mutations don't affect the store."""
        db = InMemoryDatabaseClient()
        db.collection("downloads").document("doc1").set({"status": "active"})

        results = list(
            db.collection("downloads").where("status", "==", "active").stream()
        )
        data = results[0].to_dict()
        assert data is not None
        data["status"] = "tampered"

        # Original should be unchanged
        results2 = list(
            db.collection("downloads").where("status", "==", "active").stream()
        )
        assert len(results2) == 1

    def test_comparison_operators(self):
        """where() supports <, <=, >, >= operators."""
        db = InMemoryDatabaseClient()
        db.collection("scores").document("a").set({"score": 10})
        db.collection("scores").document("b").set({"score": 20})
        db.collection("scores").document("c").set({"score": 30})

        gt = list(db.collection("scores").where("score", ">", 15).stream())
        assert len(gt) == 2

        gte = list(db.collection("scores").where("score", ">=", 20).stream())
        assert len(gte) == 2

        lt = list(db.collection("scores").where("score", "<", 20).stream())
        assert len(lt) == 1

        lte = list(db.collection("scores").where("score", "<=", 20).stream())
        assert len(lte) == 2


class TestCreateDatabaseClient:
    """Tests for the factory function."""

    def test_returns_in_memory_for_none(self):
        """Returns InMemoryDatabaseClient when project_id is None."""
        client = create_database_client(None)
        assert isinstance(client, InMemoryDatabaseClient)

    def test_returns_in_memory_for_placeholder(self):
        """Returns InMemoryDatabaseClient for the placeholder project ID."""
        client = create_database_client("your-gcp-project-id")
        assert isinstance(client, InMemoryDatabaseClient)

    def test_returns_in_memory_for_empty_string(self):
        """Returns InMemoryDatabaseClient for empty string (falsy)."""
        client = create_database_client("")
        assert isinstance(client, InMemoryDatabaseClient)
