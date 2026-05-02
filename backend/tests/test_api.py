"""
Unit tests for API endpoints.
Tests Flask API routes using test client.
"""

import pytest
import json
import tempfile
import shutil
import os

from backend.server import create_app
from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.storage import WorkflowStorage


class TestWorkflowAPI:
    """Tests for Workflow API endpoints."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = create_app()
        app.config.update({
            "TESTING": True,
        })
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_list_workflows_empty(self, client):
        """Test GET /api/workflows with no workflows."""
        response = client.get("/api/workflows")
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_create_workflow(self, client):
        """Test POST /api/workflows to create a workflow."""
        workflow_data = {
            "name": "Test Workflow",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {"params": {"name": "Alice"}}
                },
                {
                    "id": "node-2",
                    "type": "end",
                    "position": {"x": 300, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "node-1",
                    "target": "node-2"
                }
            ]
        }
        
        response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert "id" in data
        assert data["name"] == "Test Workflow"
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        
        workflow_id = data["id"]
        
        get_response = client.get(f"/api/workflows/{workflow_id}")
        assert get_response.status_code == 200
        get_data = get_response.get_json()
        assert get_data["id"] == workflow_id
        assert get_data["name"] == "Test Workflow"
        
        delete_response = client.delete(f"/api/workflows/{workflow_id}")
        assert delete_response.status_code == 200

    def test_get_workflow_not_found(self, client):
        """Test GET /api/workflows/<id> for non-existent workflow."""
        response = client.get("/api/workflows/non-existent-id")
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_update_workflow(self, client):
        """Test PUT /api/workflows/<id> to update a workflow."""
        create_data = {
            "name": "Original Name",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {}
                }
            ],
            "edges": []
        }
        
        create_response = client.post(
            "/api/workflows",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        assert create_response.status_code == 201
        workflow_id = create_response.get_json()["id"]
        
        update_data = {
            "name": "Updated Name",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {}
                },
                {
                    "id": "node-2",
                    "type": "end",
                    "position": {"x": 300, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "node-1",
                    "target": "node-2"
                }
            ]
        }
        
        update_response = client.put(
            f"/api/workflows/{workflow_id}",
            data=json.dumps(update_data),
            content_type="application/json"
        )
        
        assert update_response.status_code == 200
        updated = update_response.get_json()
        
        assert updated["name"] == "Updated Name"
        assert len(updated["nodes"]) == 2
        assert len(updated["edges"]) == 1
        
        client.delete(f"/api/workflows/{workflow_id}")

    def test_update_workflow_not_found(self, client):
        """Test PUT /api/workflows/<id> for non-existent workflow."""
        update_data = {
            "name": "Updated",
            "nodes": [],
            "edges": []
        }
        
        response = client.put(
            "/api/workflows/non-existent-id",
            data=json.dumps(update_data),
            content_type="application/json"
        )
        
        assert response.status_code == 404

    def test_delete_workflow_not_found(self, client):
        """Test DELETE /api/workflows/<id> for non-existent workflow."""
        response = client.delete("/api/workflows/non-existent-id")
        
        assert response.status_code == 404

    def test_run_workflow(self, client):
        """Test POST /api/workflows/<id>/run to execute a workflow."""
        workflow_data = {
            "name": "Run Test Workflow",
            "nodes": [
                {
                    "id": "start-node",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {"params": {"name": "World", "multiplier": 3}}
                },
                {
                    "id": "code-node",
                    "type": "python_code",
                    "position": {"x": 300, "y": 100},
                    "config": {
                        "code": "greeting = f'Hello {name}'\nresult = {'greeting': greeting, 'tripled': multiplier * 10}"
                    }
                },
                {
                    "id": "end-node",
                    "type": "end",
                    "position": {"x": 500, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {"id": "e1", "source": "start-node", "target": "code-node"},
                {"id": "e2", "source": "code-node", "target": "end-node"}
            ]
        }
        
        create_response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        assert create_response.status_code == 201
        workflow_id = create_response.get_json()["id"]
        
        run_response = client.post(f"/api/workflows/{workflow_id}/run")
        
        assert run_response.status_code == 200
        result = run_response.get_json()
        
        assert result["status"] == "success"
        assert result["result"] is not None
        
        final_result = result["result"]
        assert final_result["greeting"] == "Hello World"
        assert final_result["tripled"] == 30
        
        client.delete(f"/api/workflows/{workflow_id}")

    def test_run_workflow_not_found(self, client):
        """Test POST /api/workflows/<id>/run for non-existent workflow."""
        response = client.post("/api/workflows/non-existent-id/run")
        
        assert response.status_code == 404

    def test_export_workflow(self, client):
        """Test POST /api/workflows/<id>/export to export code."""
        workflow_data = {
            "name": "Export Test",
            "nodes": [
                {
                    "id": "start-1",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {"params": {"value": 5}}
                },
                {
                    "id": "code-1",
                    "type": "python_code",
                    "position": {"x": 300, "y": 100},
                    "config": {"code": "result = value * 2"}
                },
                {
                    "id": "end-1",
                    "type": "end",
                    "position": {"x": 500, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {"id": "e1", "source": "start-1", "target": "code-1"},
                {"id": "e2", "source": "code-1", "target": "end-1"}
            ]
        }
        
        create_response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        assert create_response.status_code == 201
        workflow_id = create_response.get_json()["id"]
        
        export_response = client.post(f"/api/workflows/{workflow_id}/export")
        
        assert export_response.status_code == 200
        export_data = export_response.get_json()
        
        assert "code" in export_data
        assert "filename" in export_data
        assert "Export_Test" in export_data["filename"]
        
        code = export_data["code"]
        assert "def run_workflow" in code
        assert "# Workflow: Export Test" in code
        
        client.delete(f"/api/workflows/{workflow_id}")

    def test_export_workflow_not_found(self, client):
        """Test POST /api/workflows/<id>/export for non-existent workflow."""
        response = client.post("/api/workflows/non-existent-id/export")
        
        assert response.status_code == 404

    def test_index_route(self, client):
        """Test GET / returns index page."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data or response.content_type == "text/html"

    def test_create_workflow_minimal(self, client):
        """Test POST /api/workflows with minimal data."""
        workflow_data = {
            "name": "Minimal Workflow"
        }
        
        response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Minimal Workflow"
        assert data["nodes"] == []
        assert data["edges"] == []
        
        client.delete(f"/api/workflows/{data['id']}")

    def test_create_workflow_default_name(self, client):
        """Test POST /api/workflows without name uses default."""
        workflow_data = {}
        
        response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Untitled Workflow"
        
        client.delete(f"/api/workflows/{data['id']}")

    def test_full_crud_operations(self, client):
        """Test complete CRUD lifecycle via API."""
        list_response = client.get("/api/workflows")
        assert list_response.status_code == 200
        initial_count = len(list_response.get_json())
        
        create_data = {
            "name": "CRUD Test Workflow",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {"params": {"test": "value"}}
                },
                {
                    "id": "end",
                    "type": "end",
                    "position": {"x": 300, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "end"}
            ]
        }
        
        create_response = client.post(
            "/api/workflows",
            data=json.dumps(create_data),
            content_type="application/json"
        )
        assert create_response.status_code == 201
        workflow_id = create_response.get_json()["id"]
        
        list_response = client.get("/api/workflows")
        assert list_response.status_code == 200
        
        get_response = client.get(f"/api/workflows/{workflow_id}")
        assert get_response.status_code == 200
        assert get_response.get_json()["name"] == "CRUD Test Workflow"
        
        update_data = {"name": "Updated CRUD Workflow"}
        update_response = client.put(
            f"/api/workflows/{workflow_id}",
            data=json.dumps(update_data),
            content_type="application/json"
        )
        assert update_response.status_code == 200
        assert update_response.get_json()["name"] == "Updated CRUD Workflow"
        
        delete_response = client.delete(f"/api/workflows/{workflow_id}")
        assert delete_response.status_code == 200
        
        get_deleted = client.get(f"/api/workflows/{workflow_id}")
        assert get_deleted.status_code == 404


class TestWorkflowExecutionAPI:
    """Tests for workflow execution via API."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = create_app()
        app.config.update({
            "TESTING": True,
        })
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_simple_execution(self, client):
        """Test simple Start -> Code -> End execution."""
        workflow_data = {
            "name": "Simple Execution",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {"params": {"x": 10, "y": 20}}
                },
                {
                    "id": "code",
                    "type": "python_code",
                    "position": {"x": 300, "y": 100},
                    "config": {"code": "result = x + y"}
                },
                {
                    "id": "end",
                    "type": "end",
                    "position": {"x": 500, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "code"},
                {"id": "e2", "source": "code", "target": "end"}
            ]
        }
        
        create_response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        workflow_id = create_response.get_json()["id"]
        
        run_response = client.post(f"/api/workflows/{workflow_id}/run")
        
        assert run_response.status_code == 200
        result = run_response.get_json()
        
        assert result["status"] == "success"
        assert result["result"] == 30
        
        client.delete(f"/api/workflows/{workflow_id}")

    def test_execution_with_error(self, client):
        """Test execution with error in code."""
        workflow_data = {
            "name": "Error Execution",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {"params": {}}
                },
                {
                    "id": "code",
                    "type": "python_code",
                    "position": {"x": 300, "y": 100},
                    "config": {"code": "result = 1 / 0"}
                },
                {
                    "id": "end",
                    "type": "end",
                    "position": {"x": 500, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "code"},
                {"id": "e2", "source": "code", "target": "end"}
            ]
        }
        
        create_response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        workflow_id = create_response.get_json()["id"]
        
        run_response = client.post(f"/api/workflows/{workflow_id}/run")
        
        assert run_response.status_code == 200
        result = run_response.get_json()
        
        assert result["status"] == "error"
        assert "error" in result
        
        client.delete(f"/api/workflows/{workflow_id}")

    def test_execution_logs(self, client):
        """Test that execution returns logs."""
        workflow_data = {
            "name": "Logs Test",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {"params": {"value": 5}}
                },
                {
                    "id": "end",
                    "type": "end",
                    "position": {"x": 300, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "end"}
            ]
        }
        
        create_response = client.post(
            "/api/workflows",
            data=json.dumps(workflow_data),
            content_type="application/json"
        )
        workflow_id = create_response.get_json()["id"]
        
        run_response = client.post(f"/api/workflows/{workflow_id}/run")
        
        assert run_response.status_code == 200
        result = run_response.get_json()
        
        assert "logs" in result
        assert len(result["logs"]) > 0
        
        client.delete(f"/api/workflows/{workflow_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
