import pytest
from fastapi import status

class TestProjectsEndpoints:
    """Test suite for projects endpoints."""

    def test_create_project_success(self, client, sample_project_data):
        """Test successful project creation."""
        response = client.post("/projects/", json=sample_project_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == sample_project_data["name"]
        assert "id" in data
        assert "created_at" in data
        assert data["id"] == 1

    def test_create_project_duplicate_name(self, client, sample_project_data):
        """Test creating project with duplicate name fails."""
        # Create first project
        response1 = client.post("/projects/", json=sample_project_data)
        assert response1.status_code == status.HTTP_200_OK
        
        # Try to create project with same name
        response2 = client.post("/projects/", json=sample_project_data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response2.json()["detail"]

    def test_create_project_invalid_data(self, client):
        """Test creating project with invalid data."""
        invalid_data = {"invalid_field": "value"}
        response = client.post("/projects/", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_empty_name(self, client):
        """Test creating project with empty name."""
        empty_name_data = {"name": ""}
        response = client.post("/projects/", json=empty_name_data)
        # Should succeed but with empty name (validation can be added later)
        assert response.status_code == status.HTTP_200_OK

    def test_list_projects_empty(self, client):
        """Test listing projects when none exist."""
        response = client.get("/projects/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_projects_with_data(self, client, multiple_projects_data):
        """Test listing projects with existing data."""
        # Create multiple projects
        created_projects = []
        for project_data in multiple_projects_data:
            response = client.post("/projects/", json=project_data)
            assert response.status_code == status.HTTP_200_OK
            created_projects.append(response.json())
        
        # List all projects
        response = client.get("/projects/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(multiple_projects_data)
        
        # Check if all created projects are in the list
        project_names = [project["name"] for project in data]
        for expected_project in multiple_projects_data:
            assert expected_project["name"] in project_names

    def test_list_projects_response_structure(self, client, sample_project_data):
        """Test the response structure of list projects endpoint."""
        # Create a project first
        client.post("/projects/", json=sample_project_data)
        
        response = client.get("/projects/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        
        project = data[0]
        assert "id" in project
        assert "name" in project
        assert "created_at" in project
        assert project["name"] == sample_project_data["name"]
        # Check that created_at is a valid ISO datetime string
        from datetime import datetime
        datetime.fromisoformat(project["created_at"].replace('Z', '+00:00'))

    def test_project_creation_auto_increment_id(self, client, multiple_projects_data):
        """Test that project IDs auto-increment correctly."""
        created_ids = []
        
        for project_data in multiple_projects_data:
            response = client.post("/projects/", json=project_data)
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            created_ids.append(data["id"])
        
        # Check that IDs are incrementing
        assert created_ids == [1, 2, 3]
        assert len(set(created_ids)) == len(created_ids)  # All IDs are unique

class TestProjectsIntegration:
    """Integration tests for projects functionality."""

    def test_create_and_list_workflow(self, client):
        """Test the complete workflow of creating and listing projects."""
        # Initially, no projects should exist
        response = client.get("/projects/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 0
        
        # Create first project
        project1_data = {"name": "Integration Test Project 1"}
        response = client.post("/projects/", json=project1_data)
        assert response.status_code == status.HTTP_200_OK
        project1 = response.json()
        
        # List should now contain one project
        response = client.get("/projects/")
        assert response.status_code == status.HTTP_200_OK
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["name"] == project1_data["name"]
        
        # Create second project
        project2_data = {"name": "Integration Test Project 2"}
        response = client.post("/projects/", json=project2_data)
        assert response.status_code == status.HTTP_200_OK
        project2 = response.json()
        
        # List should now contain two projects
        response = client.get("/projects/")
        assert response.status_code == status.HTTP_200_OK
        projects = response.json()
        assert len(projects) == 2
        
        project_names = [p["name"] for p in projects]
        assert project1_data["name"] in project_names
        assert project2_data["name"] in project_names