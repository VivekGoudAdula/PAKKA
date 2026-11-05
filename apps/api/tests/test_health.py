"""
Tests for the Pakka API — Phase 0 health check tests.
"""

from app.routers.health import health


class TestHealth:
    """Health endpoint tests."""

    def test_health_returns_200(self) -> None:
        """GET /health must return valid health response."""
        resp = health()
        assert resp.status == "ok"

    def test_health_returns_ok_status(self) -> None:
        """GET /health body must contain status=ok."""
        resp = health()
        assert resp.status == "ok"

    def test_health_returns_version(self) -> None:
        """GET /health body must contain a version string."""
        resp = health()
        assert resp.version == "0.1.0"
        assert len(resp.version) > 0
