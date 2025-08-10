import pytest
from fastapi import status
import json

class TestConfigEndpoints:
    """Test suite for configuration endpoints."""

    def test_list_configs_empty(self, client):
        """Test listing configs when none exist."""
        response = client.get("/configs/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_create_config_success(self, client):
        """Test successful config creation."""
        config_data = {
            "key": "test.setting",
            "value": "test_value",
            "description": "Test configuration setting"
        }
        
        response = client.post("/configs/", json=config_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"] == config_data["key"]
        assert data["value"] == config_data["value"]
        assert data["description"] == config_data["description"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_config_duplicate_key(self, client):
        """Test creating config with duplicate key fails."""
        config_data = {
            "key": "duplicate.test",
            "value": "value1",
            "description": "First config"
        }
        
        # Create first config
        response1 = client.post("/configs/", json=config_data)
        assert response1.status_code == status.HTTP_200_OK
        
        # Try to create config with same key
        config_data["value"] = "value2"
        response2 = client.post("/configs/", json=config_data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response2.json()["detail"]

    def test_get_config_success(self, client):
        """Test retrieving a specific config."""
        # Create a config first
        config_data = {
            "key": "get.test",
            "value": "retrieve_me",
            "description": "Config for retrieval test"
        }
        client.post("/configs/", json=config_data)
        
        # Retrieve the config
        response = client.get(f"/configs/{config_data['key']}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"] == config_data["key"]
        assert data["value"] == config_data["value"]
        assert data["description"] == config_data["description"]

    def test_get_config_not_found(self, client):
        """Test retrieving non-existent config."""
        response = client.get("/configs/nonexistent.key")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_update_config_existing(self, client):
        """Test updating an existing config."""
        # Create a config first
        config_data = {
            "key": "update.test",
            "value": "original_value",
            "description": "Original description"
        }
        client.post("/configs/", json=config_data)
        
        # Update the config
        update_data = {
            "value": "updated_value",
            "description": "Updated description"
        }
        response = client.put(f"/configs/{config_data['key']}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"] == config_data["key"]
        assert data["value"] == update_data["value"]
        assert data["description"] == update_data["description"]

    def test_update_config_create_new(self, client):
        """Test updating non-existent config creates new one."""
        update_data = {
            "value": "new_value",
            "description": "New config created via update"
        }
        key = "new.config"
        
        response = client.put(f"/configs/{key}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"] == key
        assert data["value"] == update_data["value"]
        assert data["description"] == update_data["description"]

    def test_delete_config_success(self, client):
        """Test successful config deletion."""
        # Create a config first
        config_data = {
            "key": "delete.test",
            "value": "delete_me",
            "description": "Config for deletion test"
        }
        client.post("/configs/", json=config_data)
        
        # Delete the config
        response = client.delete(f"/configs/{config_data['key']}")
        
        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]
        
        # Verify it's gone
        get_response = client.get(f"/configs/{config_data['key']}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_config_not_found(self, client):
        """Test deleting non-existent config."""
        response = client.delete("/configs/nonexistent.key")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_list_configs_with_data(self, client):
        """Test listing configs with existing data."""
        # Create multiple configs
        configs = [
            {"key": "list.test1", "value": "value1", "description": "First config"},
            {"key": "list.test2", "value": "value2", "description": "Second config"},
            {"key": "list.test3", "value": "value3", "description": "Third config"}
        ]
        
        for config in configs:
            client.post("/configs/", json=config)
        
        # List all configs
        response = client.get("/configs/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(configs)
        
        # Check if our configs are in the list
        config_keys = [config["key"] for config in data]
        for config in configs:
            assert config["key"] in config_keys

class TestConfigService:
    """Test suite for config service functionality."""

    def test_config_response_structure(self, client):
        """Test the response structure of config endpoints."""
        config_data = {
            "key": "structure.test",
            "value": "test_value",
            "description": "Structure test config"
        }
        
        response = client.post("/configs/", json=config_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        required_fields = ["key", "value", "description", "created_at", "updated_at"]
        for field in required_fields:
            assert field in data
        
        # Check data types
        assert isinstance(data["key"], str)
        assert isinstance(data["value"], str)
        assert data["description"] is None or isinstance(data["description"], str)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
        
        # Check datetime format
        from datetime import datetime
        datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))

    def test_config_with_json_value(self, client):
        """Test config with JSON value."""
        config_data = {
            "key": "json.test",
            "value": json.dumps({"nested": {"key": "value"}, "list": [1, 2, 3]}),
            "description": "JSON config test"
        }
        
        response = client.post("/configs/", json=config_data)
        assert response.status_code == status.HTTP_200_OK
        
        # Retrieve and verify
        get_response = client.get(f"/configs/{config_data['key']}")
        assert get_response.status_code == status.HTTP_200_OK
        
        data = get_response.json()
        assert data["value"] == config_data["value"]

    def test_config_without_description(self, client):
        """Test config creation without description."""
        config_data = {
            "key": "no.description",
            "value": "value_only"
        }
        
        response = client.post("/configs/", json=config_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["key"] == config_data["key"]
        assert data["value"] == config_data["value"]
        assert data["description"] is None

class TestConfigIntegration:
    """Integration tests for config functionality."""

    def test_complete_config_workflow(self, client):
        """Test the complete workflow of config management."""
        key = "workflow.test"
        
        # 1. Initially, config should not exist
        response = client.get(f"/configs/{key}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # 2. Create config
        create_data = {
            "key": key,
            "value": "initial_value",
            "description": "Workflow test config"
        }
        response = client.post("/configs/", json=create_data)
        assert response.status_code == status.HTTP_200_OK
        created_config = response.json()
        
        # 3. Verify it appears in list
        response = client.get("/configs/")
        assert response.status_code == status.HTTP_200_OK
        configs = response.json()
        config_keys = [config["key"] for config in configs]
        assert key in config_keys
        
        # 4. Retrieve specific config
        response = client.get(f"/configs/{key}")
        assert response.status_code == status.HTTP_200_OK
        retrieved_config = response.json()
        assert retrieved_config["key"] == create_data["key"]
        assert retrieved_config["value"] == create_data["value"]
        
        # 5. Update config
        update_data = {
            "value": "updated_value",
            "description": "Updated workflow test config"
        }
        response = client.put(f"/configs/{key}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        updated_config = response.json()
        assert updated_config["value"] == update_data["value"]
        assert updated_config["description"] == update_data["description"]
        
        # 6. Verify update persisted
        response = client.get(f"/configs/{key}")
        assert response.status_code == status.HTTP_200_OK
        final_config = response.json()
        assert final_config["value"] == update_data["value"]
        assert final_config["description"] == update_data["description"]
        
        # 7. Delete config
        response = client.delete(f"/configs/{key}")
        assert response.status_code == status.HTTP_200_OK
        
        # 8. Verify deletion
        response = client.get(f"/configs/{key}")
        assert response.status_code == status.HTTP_404_NOT_FOUND