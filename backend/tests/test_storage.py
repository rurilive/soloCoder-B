"""
Unit tests for storage module.
Tests WorkflowStorage class with file system storage.
"""

import os
import json
import tempfile
import shutil
import pytest
from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.storage import WorkflowStorage


class TestWorkflowStorage:
    """Tests for WorkflowStorage class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a storage instance with temporary directory."""
        return WorkflowStorage(temp_dir)

    def test_init_creates_directory(self, temp_dir):
        """Test that storage creates the data directory if it doesn't exist."""
        new_dir = os.path.join(temp_dir, "new_storage")
        assert not os.path.exists(new_dir)
        
        WorkflowStorage(new_dir)
        
        assert os.path.exists(new_dir)

    def test_list_empty(self, storage):
        """Test list returns empty list when no workflows exist."""
        workflows = storage.list()
        assert workflows == []

    def test_save_creates_file(self, storage, temp_dir):
        """Test save creates a JSON file."""
        wf = Workflow.create(name="Test Flow")
        storage.save(wf)
        
        expected_file = os.path.join(temp_dir, f"{wf.id}.json")
        assert os.path.exists(expected_file)

    def test_save_and_get(self, storage):
        """Test save and get round-trip."""
        original = Workflow.create(name="Saved Flow")
        original.nodes.append(Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"test": "value"})
        ))
        
        saved = storage.save(original)
        assert saved.id == original.id
        assert saved.name == original.name
        
        loaded = storage.get(original.id)
        assert loaded is not None
        assert loaded.id == original.id
        assert loaded.name == "Saved Flow"
        assert len(loaded.nodes) == 1
        assert loaded.nodes[0].config.params == {"test": "value"}

    def test_get_nonexistent_returns_none(self, storage):
        """Test get returns None for non-existent workflow."""
        result = storage.get("non-existent-id")
        assert result is None

    def test_list_after_save(self, storage):
        """Test list shows saved workflows."""
        wf1 = Workflow.create(name="First Flow")
        wf2 = Workflow.create(name="Second Flow")
        
        storage.save(wf1)
        storage.save(wf2)
        
        workflows = storage.list()
        assert len(workflows) == 2
        
        names = [w.name for w in workflows]
        assert "First Flow" in names
        assert "Second Flow" in names

    def test_list_sorted_by_updated_at(self, storage):
        """Test list is sorted by updated_at (newest first)."""
        import time
        
        wf1 = Workflow.create(name="Old Flow")
        wf2 = Workflow.create(name="New Flow")
        
        storage.save(wf1)
        time.sleep(0.01)
        storage.save(wf2)
        
        workflows = storage.list()
        assert len(workflows) == 2
        assert workflows[0].name == "New Flow"
        assert workflows[1].name == "Old Flow"

    def test_update_workflow(self, storage):
        """Test updating an existing workflow."""
        wf = Workflow.create(name="Original Name")
        storage.save(wf)
        
        loaded = storage.get(wf.id)
        loaded.name = "Updated Name"
        loaded.nodes.append(Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        ))
        storage.save(loaded)
        
        reloaded = storage.get(wf.id)
        assert reloaded.name == "Updated Name"
        assert len(reloaded.nodes) == 1
        assert reloaded.nodes[0].type == "end"

    def test_delete_existing(self, storage):
        """Test delete returns True and removes file for existing workflow."""
        wf = Workflow.create(name="To Delete")
        storage.save(wf)
        
        assert storage.get(wf.id) is not None
        
        result = storage.delete(wf.id)
        assert result is True
        assert storage.get(wf.id) is None

    def test_delete_nonexistent_returns_false(self, storage):
        """Test delete returns False for non-existent workflow."""
        result = storage.delete("non-existent-id")
        assert result is False

    def test_full_crud_operations(self, storage):
        """Test complete CRUD lifecycle."""
        workflows = storage.list()
        assert len(workflows) == 0
        
        wf = Workflow.create(name="CRUD Test")
        wf.nodes = [
            Node.create(node_type="start", position=Position(x=100, y=100)),
            Node.create(node_type="end", position=Position(x=500, y=100))
        ]
        wf.edges = [
            Edge.create(source=wf.nodes[0].id, target=wf.nodes[1].id)
        ]
        
        storage.save(wf)
        
        workflows = storage.list()
        assert len(workflows) == 1
        
        loaded = storage.get(wf.id)
        assert loaded.id == wf.id
        assert loaded.name == "CRUD Test"
        assert len(loaded.nodes) == 2
        assert len(loaded.edges) == 1
        
        loaded.name = "Updated CRUD"
        storage.save(loaded)
        
        reloaded = storage.get(wf.id)
        assert reloaded.name == "Updated CRUD"
        
        storage.delete(wf.id)
        workflows = storage.list()
        assert len(workflows) == 0

    def test_get_workflow_path(self, storage, temp_dir):
        """Test internal _get_workflow_path method."""
        wf = Workflow.create(name="Test")
        path = storage._get_workflow_path(wf.id)
        
        expected = os.path.join(temp_dir, f"{wf.id}.json")
        assert path == expected

    def test_storage_with_default_path(self):
        """Test storage uses default path when none provided."""
        storage = WorkflowStorage()
        
        default_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "workflows"
        )
        assert storage.data_dir == default_dir

    def test_save_creates_valid_json(self, storage, temp_dir):
        """Test saved files contain valid JSON."""
        wf = Workflow.create(name="JSON Test")
        wf.nodes.append(Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = 1 + 1")
        ))
        
        storage.save(wf)
        
        filepath = os.path.join(temp_dir, f"{wf.id}.json")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["id"] == wf.id
        assert data["name"] == "JSON Test"
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["type"] == "python_code"

    def test_list_skips_invalid_json(self, storage, temp_dir):
        """Test list skips files with invalid JSON."""
        wf = Workflow.create(name="Valid Flow")
        storage.save(wf)
        
        invalid_file = os.path.join(temp_dir, "invalid.json")
        with open(invalid_file, "w") as f:
            f.write("this is not valid json")
        
        wrong_ext = os.path.join(temp_dir, "wrong.txt")
        with open(wrong_ext, "w") as f:
            f.write('{"id": "test"}')
        
        workflows = storage.list()
        assert len(workflows) == 1
        assert workflows[0].name == "Valid Flow"

    def test_get_returns_none_for_invalid_json(self, storage, temp_dir):
        """Test get returns None for files with invalid JSON."""
        invalid_file = os.path.join(temp_dir, "corrupted.json")
        with open(invalid_file, "w") as f:
            f.write("not valid { json ]")
        
        storage._get_workflow_path = lambda x: invalid_file
        result = storage.get("corrupted")
        assert result is None

    def test_complex_workflow_persistence(self, storage):
        """Test persisting a complex workflow with multiple nodes and edges."""
        workflow = Workflow.create(name="Complex Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"name": "Alice", "age": 30})
        )
        
        code1 = Node.create(
            node_type="python_code",
            position=Position(x=300, y=50),
            config=NodeConfig(code="result = f'Hello {name}'")
        )
        
        code2 = Node.create(
            node_type="python_code",
            position=Position(x=300, y=150),
            config=NodeConfig(code="result = age * 2")
        )
        
        condition = Node.create(
            node_type="condition",
            position=Position(x=500, y=100),
            config=NodeConfig(params={
                "expression": "value > 50",
                "true_value": {"result": "Old"},
                "false_value": {"result": "Young"}
            })
        )
        
        end = Node.create(
            node_type="end",
            position=Position(x=700, y=100)
        )
        
        workflow.nodes = [start, code1, code2, condition, end]
        workflow.edges = [
            Edge.create(source=start.id, target=code1.id),
            Edge.create(source=start.id, target=code2.id),
            Edge.create(source=code2.id, target=condition.id),
            Edge.create(source=condition.id, target=end.id)
        ]
        
        storage.save(workflow)
        
        loaded = storage.get(workflow.id)
        assert loaded.id == workflow.id
        assert loaded.name == "Complex Flow"
        assert len(loaded.nodes) == 5
        assert len(loaded.edges) == 4
        
        node_types = [n.type for n in loaded.nodes]
        assert "start" in node_types
        assert "python_code" in node_types
        assert "condition" in node_types
        assert "end" in node_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
