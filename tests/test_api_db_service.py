"""Tests for API SQLite storage service."""

import pytest

from pipeworks_mud_mapper.services import api_db_service


def test_service_crud_round_trip(tmp_path):
    """Services can be created, updated, listed, and deleted."""
    db_path = tmp_path / "api.db"

    service_id = api_db_service.create_service(
        name="Name Generator",
        base_url="http://localhost:8000",
        auth_type="bearer",
        auth_secret="token",
        default_headers={"X-Client": "mapper"},
        enabled=False,
        notes="Test service",
        db_path=db_path,
    )

    services = api_db_service.list_services(db_path)
    assert len(services) == 1
    assert services[0]["id"] == service_id
    assert services[0]["enabled"] is False

    loaded = api_db_service.get_service(service_id, db_path=db_path)
    assert loaded["name"] == "Name Generator"
    assert loaded["base_url"] == "http://localhost:8000"
    assert loaded["auth_type"] == "bearer"
    assert loaded["auth_secret"] == "token"
    assert loaded["default_headers"] == {"X-Client": "mapper"}
    assert loaded["notes"] == "Test service"

    api_db_service.update_service(
        service_id,
        name="Name Generator Updated",
        base_url="http://localhost:8001",
        auth_type="none",
        auth_secret=None,
        default_headers={},
        enabled=True,
        notes=None,
        db_path=db_path,
    )

    updated = api_db_service.get_service(service_id, db_path=db_path)
    assert updated["name"] == "Name Generator Updated"
    assert updated["base_url"] == "http://localhost:8001"
    assert updated["enabled"] is True

    api_db_service.delete_service(service_id, db_path=db_path)
    assert api_db_service.list_services(db_path) == []


def test_service_list_excludes_disabled(tmp_path):
    """Disabled services can be filtered out of list_services."""
    db_path = tmp_path / "api.db"
    api_db_service.create_service(
        name="Enabled",
        base_url="http://example.com",
        enabled=True,
        db_path=db_path,
    )
    api_db_service.create_service(
        name="Disabled",
        base_url="http://example.com",
        enabled=False,
        db_path=db_path,
    )

    services = api_db_service.list_services(db_path, include_disabled=False)
    assert len(services) == 1
    assert services[0]["name"] == "Enabled"


def test_command_crud_round_trip(tmp_path):
    """Commands can be created, updated, listed, and deleted."""
    db_path = tmp_path / "api.db"
    service_id = api_db_service.create_service(
        name="Service",
        base_url="http://localhost:8000",
        db_path=db_path,
    )

    command_id = api_db_service.create_command(
        service_id=service_id,
        name="Generate",
        method="post",
        path="/api/generate",
        query={"limit": 5},
        headers={"X-Client": "mapper"},
        body={"class": "goblin"},
        timeout_seconds=10,
        db_path=db_path,
    )

    commands = api_db_service.list_commands(service_id, db_path=db_path)
    assert len(commands) == 1
    assert commands[0]["id"] == command_id

    loaded = api_db_service.get_command(command_id, db_path=db_path)
    assert loaded["method"] == "POST"
    assert loaded["query"] == {"limit": 5}
    assert loaded["headers"] == {"X-Client": "mapper"}
    assert loaded["body"] == {"class": "goblin"}

    api_db_service.update_command(
        command_id,
        service_id=service_id,
        name="Generate Updated",
        method="GET",
        path="/api/generate",
        query={},
        headers={},
        body=None,
        timeout_seconds=None,
        db_path=db_path,
    )

    updated = api_db_service.get_command(command_id, db_path=db_path)
    assert updated["name"] == "Generate Updated"
    assert updated["method"] == "GET"

    api_db_service.delete_command(command_id, db_path=db_path)
    assert api_db_service.list_commands(service_id, db_path=db_path) == []


def test_missing_entities_raise_key_error(tmp_path):
    """Missing records should raise KeyError."""
    db_path = tmp_path / "api.db"
    with pytest.raises(KeyError):
        api_db_service.get_service("missing", db_path=db_path)
    with pytest.raises(KeyError):
        api_db_service.get_command("missing", db_path=db_path)


def test_invalid_json_falls_back(tmp_path):
    """Invalid JSON in stored headers should fall back safely."""
    db_path = tmp_path / "api.db"
    service_id = api_db_service.create_service(
        name="Name API",
        base_url="http://example.com",
        db_path=db_path,
    )

    with api_db_service._connect(db_path) as conn:
        conn.execute(
            "UPDATE api_services SET default_headers_json = '{bad json' WHERE id = ?",
            (service_id,),
        )

    services = api_db_service.list_services(db_path)
    assert services[0]["default_headers"] == {}
