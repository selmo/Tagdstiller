import pytest
from fastapi import status
from io import BytesIO

class TestFileEndpoints:
    """Test suite for file endpoints."""

    def test_upload_file_to_existing_project(self, client, sample_project_data):
        """Test uploading a file to an existing project."""
        # First create a project
        response = client.post("/projects/", json=sample_project_data)
        assert response.status_code == status.HTTP_200_OK
        project = response.json()
        project_id = project["id"]
        
        # Create a test file
        test_file_content = b"This is a test file content"
        test_file = BytesIO(test_file_content)
        
        # Upload file to project
        response = client.post(
            f"/projects/{project_id}/upload",
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_id"] == project_id
        assert data["filename"] == "test.txt"
        assert "filepath" in data
        assert "size" in data
        assert "uploaded_at" in data
        assert data["size"] == len(test_file_content)

    def test_upload_file_to_nonexistent_project(self, client):
        """Test uploading a file to a non-existent project."""
        test_file_content = b"This is a test file content"
        test_file = BytesIO(test_file_content)
        
        # Try to upload to non-existent project (ID 999)
        response = client.post(
            "/projects/999/upload",
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_list_files_for_existing_project(self, client, sample_project_data):
        """Test listing files for an existing project."""
        # Create a project
        response = client.post("/projects/", json=sample_project_data)
        assert response.status_code == status.HTTP_200_OK
        project = response.json()
        project_id = project["id"]
        
        # Initially, project should have no files
        response = client.get(f"/projects/{project_id}/files")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_files_for_nonexistent_project(self, client):
        """Test listing files for a non-existent project."""
        response = client.get("/projects/999/files")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_upload_multiple_files_and_list(self, client, sample_project_data):
        """Test uploading multiple files and then listing them."""
        # Create a project
        response = client.post("/projects/", json=sample_project_data)
        assert response.status_code == status.HTTP_200_OK
        project = response.json()
        project_id = project["id"]
        
        # Upload multiple files
        files_to_upload = [
            ("file1.txt", b"Content of file 1"),
            ("file2.txt", b"Content of file 2"),
            ("file3.txt", b"Content of file 3")
        ]
        
        uploaded_files = []
        for filename, content in files_to_upload:
            test_file = BytesIO(content)
            response = client.post(
                f"/projects/{project_id}/upload",
                files={"file": (filename, test_file, "text/plain")}
            )
            assert response.status_code == status.HTTP_200_OK
            uploaded_files.append(response.json())
        
        # List files
        response = client.get(f"/projects/{project_id}/files")
        assert response.status_code == status.HTTP_200_OK
        
        files_list = response.json()
        assert len(files_list) == len(files_to_upload)
        
        # Check that all uploaded files are in the list
        filenames_in_list = [f["filename"] for f in files_list]
        for filename, _ in files_to_upload:
            assert filename in filenames_in_list

    def test_file_upload_response_structure(self, client, sample_project_data):
        """Test the response structure of file upload endpoint."""
        # Create a project
        response = client.post("/projects/", json=sample_project_data)
        project_id = response.json()["id"]
        
        # Upload a file
        test_file_content = b"Test content"
        test_file = BytesIO(test_file_content)
        
        response = client.post(
            f"/projects/{project_id}/upload",
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check required fields
        required_fields = ["id", "project_id", "filename", "filepath", "size", "uploaded_at"]
        for field in required_fields:
            assert field in data
        
        # Check data types and values
        assert isinstance(data["id"], int)
        assert isinstance(data["project_id"], int)
        assert isinstance(data["filename"], str)
        assert isinstance(data["filepath"], str)
        assert isinstance(data["size"], int)
        assert isinstance(data["uploaded_at"], str)
        # Check that uploaded_at is a valid ISO datetime string
        from datetime import datetime
        datetime.fromisoformat(data["uploaded_at"].replace('Z', '+00:00'))

class TestFileIntegration:
    """Integration tests for file functionality."""

    def test_complete_file_workflow(self, client):
        """Test the complete workflow from project creation to file management."""
        # Create a project
        project_data = {"name": "File Integration Test Project"}
        response = client.post("/projects/", json=project_data)
        assert response.status_code == status.HTTP_200_OK
        project_id = response.json()["id"]
        
        # Initially no files
        response = client.get(f"/projects/{project_id}/files")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 0
        
        # Upload first file
        file1_content = b"First file content"
        file1 = BytesIO(file1_content)
        response = client.post(
            f"/projects/{project_id}/upload",
            files={"file": ("document1.txt", file1, "text/plain")}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Check file list now has one file
        response = client.get(f"/projects/{project_id}/files")
        assert response.status_code == status.HTTP_200_OK
        files = response.json()
        assert len(files) == 1
        assert files[0]["filename"] == "document1.txt"
        
        # Upload second file
        file2_content = b"Second file content with more data"
        file2 = BytesIO(file2_content)
        response = client.post(
            f"/projects/{project_id}/upload",
            files={"file": ("document2.txt", file2, "text/plain")}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Check file list now has two files
        response = client.get(f"/projects/{project_id}/files")
        assert response.status_code == status.HTTP_200_OK
        files = response.json()
        assert len(files) == 2
        
        filenames = [f["filename"] for f in files]
        assert "document1.txt" in filenames
        assert "document2.txt" in filenames