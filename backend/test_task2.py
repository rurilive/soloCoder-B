import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.storage import WorkflowStorage


def test_models():
    print("Testing models...")
    
    position = Position(x=100.0, y=200.0)
    assert position.x == 100.0
    assert position.y == 200.0
    
    pos_dict = position.to_dict()
    assert pos_dict == {"x": 100.0, "y": 200.0}
    
    restored = Position.from_dict(pos_dict)
    assert restored.x == 100.0
    assert restored.y == 200.0
    print("  Position: OK")
    
    config = NodeConfig(
        code="print('hello')",
        inputs={"name": "World"},
        outputs={"result": "test"},
        params={"key": "value"}
    )
    config_dict = config.to_dict()
    assert config_dict["code"] == "print('hello')"
    assert config_dict["inputs"]["name"] == "World"
    
    restored_config = NodeConfig.from_dict(config_dict)
    assert restored_config.code == "print('hello')"
    print("  NodeConfig: OK")
    
    start_node = Node.create(
        node_type="start",
        position=Position(x=50, y=50),
        label="Start"
    )
    assert start_node.type == "start"
    assert start_node.label == "Start"
    assert start_node.id is not None
    print("  Node.create: OK")
    
    edge = Edge.create(
        source=start_node.id,
        target="node_2",
        source_handle="output",
        target_handle="input"
    )
    assert edge.source == start_node.id
    assert edge.target == "node_2"
    print("  Edge.create: OK")
    
    workflow = Workflow.create(name="Test Workflow")
    workflow.nodes.append(start_node)
    workflow.edges.append(edge)
    
    wf_dict = workflow.to_dict()
    assert wf_dict["name"] == "Test Workflow"
    assert len(wf_dict["nodes"]) == 1
    assert len(wf_dict["edges"]) == 1
    
    summary = workflow.to_summary_dict()
    assert "nodes" not in summary
    assert summary["name"] == "Test Workflow"
    print("  Workflow: OK")
    
    restored_wf = Workflow.from_dict(wf_dict)
    assert restored_wf.name == "Test Workflow"
    assert len(restored_wf.nodes) == 1
    print("  Workflow.from_dict: OK")
    
    print("All model tests passed!\n")


def test_storage():
    print("Testing storage...")
    
    temp_dir = tempfile.mkdtemp()
    try:
        storage = WorkflowStorage(temp_dir)
        
        workflows = storage.list()
        assert len(workflows) == 0
        print("  list() empty: OK")
        
        wf1 = Workflow.create(name="First Workflow")
        saved = storage.save(wf1)
        assert saved.id == wf1.id
        print("  save() new: OK")
        
        workflows = storage.list()
        assert len(workflows) == 1
        assert workflows[0].name == "First Workflow"
        print("  list() after save: OK")
        
        loaded = storage.get(wf1.id)
        assert loaded is not None
        assert loaded.name == "First Workflow"
        print("  get() existing: OK")
        
        not_found = storage.get("non-existent-id")
        assert not_found is None
        print("  get() non-existent: OK")
        
        loaded.name = "Updated Workflow"
        storage.save(loaded)
        reloaded = storage.get(wf1.id)
        assert reloaded.name == "Updated Workflow"
        print("  save() update: OK")
        
        success = storage.delete(wf1.id)
        assert success is True
        print("  delete() existing: OK")
        
        workflows = storage.list()
        assert len(workflows) == 0
        print("  list() after delete: OK")
        
        failed = storage.delete("non-existent-id")
        assert failed is False
        print("  delete() non-existent: OK")
        
        print("All storage tests passed!\n")
    finally:
        shutil.rmtree(temp_dir)


def test_workflow_structure():
    print("Testing workflow structure (Start -> Code -> End)...")
    
    start_node = Node.create(
        node_type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(params={"name": "World"}),
        label="Start"
    )
    
    code_node = Node.create(
        node_type="python_code",
        position=Position(x=300, y=100),
        config=NodeConfig(code="return f'Hello {name}'"),
        label="Python Code"
    )
    
    end_node = Node.create(
        node_type="end",
        position=Position(x=500, y=100),
        label="End"
    )
    
    edge1 = Edge.create(
        source=start_node.id,
        target=code_node.id,
        source_handle="output",
        target_handle="input"
    )
    
    edge2 = Edge.create(
        source=code_node.id,
        target=end_node.id,
        source_handle="output",
        target_handle="input"
    )
    
    workflow = Workflow.create(name="Hello World Flow")
    workflow.nodes = [start_node, code_node, end_node]
    workflow.edges = [edge1, edge2]
    
    wf_dict = workflow.to_dict()
    assert len(wf_dict["nodes"]) == 3
    assert len(wf_dict["edges"]) == 2
    
    restored = Workflow.from_dict(wf_dict)
    assert len(restored.nodes) == 3
    assert len(restored.edges) == 2
    
    node_types = [n.type for n in restored.nodes]
    assert "start" in node_types
    assert "python_code" in node_types
    assert "end" in node_types
    
    print("  Workflow structure represents Start -> Code -> End: OK")
    print("Workflow structure test passed!\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Task 2 Validation Tests")
    print("=" * 50 + "\n")
    
    try:
        test_models()
        test_storage()
        test_workflow_structure()
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
