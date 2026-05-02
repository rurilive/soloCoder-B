"""
Unit tests for models module.
Tests Position, NodeConfig, Node, Edge, and Workflow classes.
"""

import pytest
from datetime import datetime
from backend.models import Position, NodeConfig, Node, Edge, Workflow


class TestPosition:
    """Tests for Position class."""

    def test_init_defaults(self):
        """Test default initialization."""
        pos = Position()
        assert pos.x == 0.0
        assert pos.y == 0.0

    def test_init_with_values(self):
        """Test initialization with values."""
        pos = Position(x=100.5, y=200.5)
        assert pos.x == 100.5
        assert pos.y == 200.5

    def test_to_dict(self):
        """Test conversion to dictionary."""
        pos = Position(x=150.0, y=250.0)
        d = pos.to_dict()
        assert d == {"x": 150.0, "y": 250.0}

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {"x": 100.0, "y": 200.0}
        pos = Position.from_dict(d)
        assert pos.x == 100.0
        assert pos.y == 200.0

    def test_from_dict_missing_keys(self):
        """Test from_dict with missing keys uses defaults."""
        d = {}
        pos = Position.from_dict(d)
        assert pos.x == 0.0
        assert pos.y == 0.0


class TestNodeConfig:
    """Tests for NodeConfig class."""

    def test_init_defaults(self):
        """Test default initialization."""
        config = NodeConfig()
        assert config.code == ""
        assert config.inputs == {}
        assert config.outputs == {}
        assert config.params == {}

    def test_init_with_values(self):
        """Test initialization with values."""
        config = NodeConfig(
            code="print('hello')",
            inputs={"name": "World"},
            outputs={"result": "test"},
            params={"key": "value"}
        )
        assert config.code == "print('hello')"
        assert config.inputs == {"name": "World"}
        assert config.outputs == {"result": "test"}
        assert config.params == {"key": "value"}

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = NodeConfig(
            code="result = x + y",
            inputs={"x": 1, "y": 2},
            outputs={"result": 3},
            params={"test": True}
        )
        d = config.to_dict()
        assert d["code"] == "result = x + y"
        assert d["inputs"] == {"x": 1, "y": 2}
        assert d["outputs"] == {"result": 3}
        assert d["params"] == {"test": True}

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "code": "result = x * 2",
            "inputs": {"x": 5},
            "outputs": {"result": 10},
            "params": {"multiply": 2}
        }
        config = NodeConfig.from_dict(d)
        assert config.code == "result = x * 2"
        assert config.inputs == {"x": 5}
        assert config.outputs == {"result": 10}
        assert config.params == {"multiply": 2}

    def test_from_dict_missing_keys(self):
        """Test from_dict with missing keys uses defaults."""
        d = {}
        config = NodeConfig.from_dict(d)
        assert config.code == ""
        assert config.inputs == {}
        assert config.outputs == {}
        assert config.params == {}


class TestNode:
    """Tests for Node class."""

    def test_create(self):
        """Test node creation with create class method."""
        node = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"name": "World"}),
            label="Test Start"
        )
        assert node.id is not None
        assert len(node.id) > 0
        assert node.type == "start"
        assert node.position.x == 100
        assert node.position.y == 100
        assert node.config.params == {"name": "World"}
        assert node.label == "Test Start"

    def test_create_with_id(self):
        """Test node creation with custom ID."""
        node = Node.create(
            node_type="end",
            position=Position(x=500, y=100),
            node_id="custom-end-node"
        )
        assert node.id == "custom-end-node"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        node = Node.create(
            node_type="python_code",
            position=Position(x=200, y=150),
            config=NodeConfig(code="result = 1 + 1"),
            label="Addition"
        )
        d = node.to_dict()
        assert "id" in d
        assert d["type"] == "python_code"
        assert d["position"] == {"x": 200.0, "y": 150.0}
        assert d["config"]["code"] == "result = 1 + 1"
        assert d["label"] == "Addition"

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "id": "test-node-1",
            "type": "condition",
            "position": {"x": 300, "y": 200},
            "config": {
                "params": {"expression": "value > 10"}
            },
            "label": "Condition Node"
        }
        node = Node.from_dict(d)
        assert node.id == "test-node-1"
        assert node.type == "condition"
        assert node.position.x == 300.0
        assert node.position.y == 200.0
        assert node.config.params == {"expression": "value > 10"}
        assert node.label == "Condition Node"

    def test_from_dict_missing_optional_keys(self):
        """Test from_dict with missing optional keys."""
        d = {
            "id": "simple-node",
            "type": "end",
            "position": {"x": 500, "y": 100},
            "config": {}
        }
        node = Node.from_dict(d)
        assert node.id == "simple-node"
        assert node.type == "end"
        assert node.label is None


class TestEdge:
    """Tests for Edge class."""

    def test_create(self):
        """Test edge creation with create class method."""
        edge = Edge.create(
            source="start-node",
            target="code-node",
            source_handle="output",
            target_handle="input"
        )
        assert edge.id is not None
        assert edge.source == "start-node"
        assert edge.target == "code-node"
        assert edge.source_handle == "output"
        assert edge.target_handle == "input"

    def test_create_with_id(self):
        """Test edge creation with custom ID."""
        edge = Edge.create(
            source="a",
            target="b",
            edge_id="custom-edge-id"
        )
        assert edge.id == "custom-edge-id"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        edge = Edge.create(
            source="node-1",
            target="node-2",
            source_handle="output-true",
            target_handle="input"
        )
        d = edge.to_dict()
        assert "id" in d
        assert d["source"] == "node-1"
        assert d["target"] == "node-2"
        assert d["source_handle"] == "output-true"
        assert d["target_handle"] == "input"

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "id": "edge-123",
            "source": "start",
            "target": "end",
            "source_handle": "out",
            "target_handle": "in"
        }
        edge = Edge.from_dict(d)
        assert edge.id == "edge-123"
        assert edge.source == "start"
        assert edge.target == "end"
        assert edge.source_handle == "out"
        assert edge.target_handle == "in"

    def test_from_dict_missing_optional_keys(self):
        """Test from_dict with missing optional handle keys."""
        d = {
            "id": "simple-edge",
            "source": "a",
            "target": "b"
        }
        edge = Edge.from_dict(d)
        assert edge.source_handle is None
        assert edge.target_handle is None


class TestWorkflow:
    """Tests for Workflow class."""

    def test_create(self):
        """Test workflow creation."""
        wf = Workflow.create(name="Test Workflow")
        assert wf.id is not None
        assert wf.name == "Test Workflow"
        assert wf.nodes == []
        assert wf.edges == []
        assert wf.created_at is not None
        assert wf.updated_at is not None

    def test_create_with_id(self):
        """Test workflow creation with custom ID."""
        wf = Workflow.create(name="Custom ID Flow", workflow_id="custom-flow-id")
        assert wf.id == "custom-flow-id"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        wf = Workflow.create(name="Simple Flow")
        wf.nodes.append(Node.create(
            node_type="start",
            position=Position(x=100, y=100)
        ))
        wf.edges.append(Edge.create(
            source="start",
            target="end"
        ))
        
        d = wf.to_dict()
        assert d["id"] == wf.id
        assert d["name"] == "Simple Flow"
        assert len(d["nodes"]) == 1
        assert len(d["edges"]) == 1
        assert "created_at" in d
        assert "updated_at" in d

    def test_to_summary_dict(self):
        """Test summary dictionary (without nodes/edges)."""
        wf = Workflow.create(name="Summary Test")
        summary = wf.to_summary_dict()
        assert summary["id"] == wf.id
        assert summary["name"] == "Summary Test"
        assert "nodes" not in summary
        assert "edges" not in summary
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "id": "test-flow",
            "name": "Restored Flow",
            "nodes": [
                {
                    "id": "n1",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {}
                }
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2"
                }
            ],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00"
        }
        wf = Workflow.from_dict(d)
        assert wf.id == "test-flow"
        assert wf.name == "Restored Flow"
        assert len(wf.nodes) == 1
        assert len(wf.edges) == 1
        assert wf.nodes[0].id == "n1"
        assert wf.edges[0].source == "n1"

    def test_update_timestamp(self):
        """Test that update_timestamp changes updated_at."""
        import time
        wf = Workflow.create(name="Timestamp Test")
        original_updated = wf.updated_at
        
        time.sleep(0.01)
        wf.update_timestamp()
        
        assert wf.updated_at != original_updated

    def test_from_dict_missing_nodes_edges(self):
        """Test from_dict with missing nodes/edges uses empty lists."""
        d = {
            "id": "minimal-flow",
            "name": "Minimal"
        }
        wf = Workflow.from_dict(d)
        assert wf.nodes == []
        assert wf.edges == []

    def test_full_workflow_serialization(self):
        """Test complete round-trip serialization."""
        original = Workflow.create(name="Round Trip Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"name": "World"})
        )
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = f'Hello {name}'")
        )
        end = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        
        original.nodes = [start, code, end]
        original.edges = [
            Edge.create(source=start.id, target=code.id),
            Edge.create(source=code.id, target=end.id)
        ]
        
        wf_dict = original.to_dict()
        restored = Workflow.from_dict(wf_dict)
        
        assert restored.id == original.id
        assert restored.name == original.name
        assert len(restored.nodes) == 3
        assert len(restored.edges) == 2
        
        original_node_types = [n.type for n in original.nodes]
        restored_node_types = [n.type for n in restored.nodes]
        assert original_node_types == restored_node_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
