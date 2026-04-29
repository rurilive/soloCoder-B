import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.server import create_app
from backend.models import Workflow, Node, Edge, Position, NodeConfig


def test_api_list_workflows():
    print("Testing API: GET /api/workflows...")
    
    app = create_app()
    client = app.test_client()
    
    response = client.get("/api/workflows")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    print(f"  Response: {data}")
    print("  GET /api/workflows: OK")
    print("API list test passed!\n")


def test_api_create_workflow():
    print("Testing API: POST /api/workflows...")
    
    app = create_app()
    client = app.test_client()
    
    workflow_data = {
        "name": "Test Workflow",
        "nodes": [
            {
                "id": "node-1",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "config": {"params": {"name": "Alice", "value": 42}}
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
    
    response = client.post("/api/workflows", 
        data=json.dumps(workflow_data),
        content_type="application/json"
    )
    
    assert response.status_code == 201
    data = response.get_json()
    assert "id" in data
    assert data["name"] == "Test Workflow"
    assert len(data["nodes"]) == 2
    print(f"  Created workflow ID: {data['id']}")
    print("  POST /api/workflows: OK")
    
    workflow_id = data["id"]
    
    get_response = client.get(f"/api/workflows/{workflow_id}")
    assert get_response.status_code == 200
    get_data = get_response.get_json()
    assert get_data["id"] == workflow_id
    print("  GET /api/workflows/<id>: OK")
    
    update_data = {
        "name": "Updated Workflow",
        "nodes": data["nodes"] + [{
            "id": "node-3",
            "type": "python_code",
            "position": {"x": 500, "y": 100},
            "config": {"code": "result = value * 2"}
        }]
    }
    
    put_response = client.put(f"/api/workflows/{workflow_id}",
        data=json.dumps(update_data),
        content_type="application/json"
    )
    assert put_response.status_code == 200
    put_data = put_response.get_json()
    assert put_data["name"] == "Updated Workflow"
    assert len(put_data["nodes"]) == 3
    print("  PUT /api/workflows/<id>: OK")
    
    delete_response = client.delete(f"/api/workflows/{workflow_id}")
    assert delete_response.status_code == 200
    print("  DELETE /api/workflows/<id>: OK")
    
    get_deleted = client.get(f"/api/workflows/{workflow_id}")
    assert get_deleted.status_code == 404
    print("  Workflow deleted successfully: OK")
    
    print("API CRUD test passed!\n")


def test_api_run_workflow():
    print("Testing API: POST /api/workflows/<id>/run...")
    
    app = create_app()
    client = app.test_client()
    
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
                "config": {"code": "greeting = f'Hello {name}'\nresult = {'greeting': greeting, 'tripled': multiplier * 10}"}
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
    
    create_response = client.post("/api/workflows", 
        data=json.dumps(workflow_data),
        content_type="application/json"
    )
    assert create_response.status_code == 201
    workflow_id = create_response.get_json()["id"]
    print(f"  Created workflow: {workflow_id}")
    
    run_response = client.post(f"/api/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    result = run_response.get_json()
    
    print(f"  Status: {result.get('status')}")
    print(f"  Result: {result.get('result')}")
    print(f"  Logs: {result.get('logs', [])[:5]}")
    
    assert result["status"] == "success"
    assert result["result"] is not None
    
    final_result = result["result"]
    assert final_result["greeting"] == "Hello World"
    assert final_result["tripled"] == 30
    
    print("  POST /api/workflows/<id>/run: OK")
    print("API run test passed!\n")
    
    client.delete(f"/api/workflows/{workflow_id}")


def test_api_export_workflow():
    print("Testing API: POST /api/workflows/<id>/export...")
    
    app = create_app()
    client = app.test_client()
    
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
    
    create_response = client.post("/api/workflows", 
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
    
    print(f"  Filename: {export_data['filename']}")
    print(f"  Code length: {len(code)} chars")
    print("  POST /api/workflows/<id>/export: OK")
    print("API export test passed!\n")
    
    client.delete(f"/api/workflows/{workflow_id}")


def test_api_error_handling():
    print("Testing API error handling...")
    
    app = create_app()
    client = app.test_client()
    
    get_response = client.get("/api/workflows/non-existent-id")
    assert get_response.status_code == 404
    print("  GET non-existent workflow: 404 OK")
    
    put_response = client.put("/api/workflows/non-existent-id",
        data=json.dumps({"name": "Test"}),
        content_type="application/json"
    )
    assert put_response.status_code == 404
    print("  PUT non-existent workflow: 404 OK")
    
    delete_response = client.delete("/api/workflows/non-existent-id")
    assert delete_response.status_code == 404
    print("  DELETE non-existent workflow: 404 OK")
    
    run_response = client.post("/api/workflows/non-existent-id/run")
    assert run_response.status_code == 404
    print("  RUN non-existent workflow: 404 OK")
    
    print("API error handling test passed!\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Task 6 Validation Tests")
    print("=" * 50 + "\n")
    
    try:
        test_api_list_workflows()
        test_api_create_workflow()
        test_api_run_workflow()
        test_api_export_workflow()
        test_api_error_handling()
        
        print("=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
