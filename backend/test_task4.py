import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.runner import WorkflowRunner
from backend.nodes import NodeRegistry


def test_topological_sort():
    print("Testing topological sort...")
    
    workflow = Workflow.create(name="Test Flow")
    
    start = Node.create(node_type="start", position=Position(x=100, y=100))
    code1 = Node.create(node_type="python_code", position=Position(x=300, y=100))
    code2 = Node.create(node_type="python_code", position=Position(x=300, y=250))
    end = Node.create(node_type="end", position=Position(x=500, y=175))
    
    workflow.nodes = [start, code1, code2, end]
    workflow.edges = [
        Edge.create(source=start.id, target=code1.id),
        Edge.create(source=start.id, target=code2.id),
        Edge.create(source=code1.id, target=end.id),
        Edge.create(source=code2.id, target=end.id),
    ]
    
    runner = WorkflowRunner(workflow)
    order = runner._topological_sort()
    order_ids = [n.id for n in order]
    
    assert order_ids.index(start.id) < order_ids.index(code1.id)
    assert order_ids.index(start.id) < order_ids.index(code2.id)
    assert order_ids.index(code1.id) < order_ids.index(end.id)
    assert order_ids.index(code2.id) < order_ids.index(end.id)
    
    print(f"  Execution order: {order_ids}")
    print("  Topological sort: OK")
    print("Topological sort test passed!\n")


def test_cycle_detection():
    print("Testing cycle detection...")
    
    workflow = Workflow.create(name="Cyclic Flow")
    
    node1 = Node.create(node_type="python_code", position=Position(x=100, y=100))
    node2 = Node.create(node_type="python_code", position=Position(x=300, y=100))
    
    workflow.nodes = [node1, node2]
    workflow.edges = [
        Edge.create(source=node1.id, target=node2.id),
        Edge.create(source=node2.id, target=node1.id),
    ]
    
    runner = WorkflowRunner(workflow)
    
    try:
        runner._topological_sort()
        assert False, "Should have raised an error for cyclic workflow"
    except RuntimeError as e:
        assert "cycle" in str(e).lower()
        print("  Cycle detected correctly: OK")
    
    print("Cycle detection test passed!\n")


def test_simple_workflow_execution():
    print("Testing simple workflow execution (Start -> Code -> End)...")
    
    workflow = Workflow.create(name="Hello World Flow")
    
    start = Node.create(
        node_type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(params={"name": "World", "multiplier": 2})
    )
    
    code = Node.create(
        node_type="python_code",
        position=Position(x=300, y=100),
        config=NodeConfig(code="""
greeting = f"Hello {name}"
doubled = multiplier * 10
result = {"greeting": greeting, "doubled": doubled}
""")
    )
    
    end = Node.create(
        node_type="end",
        position=Position(x=500, y=100)
    )
    
    workflow.nodes = [start, code, end]
    workflow.edges = [
        Edge.create(source=start.id, target=code.id),
        Edge.create(source=code.id, target=end.id),
    ]
    
    runner = WorkflowRunner(workflow)
    result = runner.run()
    
    print(f"  Status: {result['status']}")
    print(f"  Result: {result['result']}")
    print(f"  Logs: {result['logs']}")
    
    assert result["status"] == "success"
    assert result["result"] is not None
    
    final_result = result["result"]
    assert isinstance(final_result, dict)
    assert final_result["greeting"] == "Hello World"
    assert final_result["doubled"] == 20
    
    print("  Simple workflow execution: OK")
    print("Simple workflow execution test passed!\n")


def test_data_flow_between_nodes():
    print("Testing data flow between multiple nodes...")
    
    workflow = Workflow.create(name="Data Flow")
    
    start = Node.create(
        node_type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(params={"values": [1, 2, 3, 4, 5]})
    )
    
    code_sum = Node.create(
        node_type="python_code",
        position=Position(x=300, y=50),
        config=NodeConfig(code="result = sum(values)")
    )
    
    code_len = Node.create(
        node_type="python_code",
        position=Position(x=300, y=150),
        config=NodeConfig(code="result = len(values)")
    )
    
    code_combine = Node.create(
        node_type="python_code",
        position=Position(x=500, y=100),
        config=NodeConfig(code="""
result = {
    "sum": sum_result,
    "length": len_result,
    "average": sum_result / len_result if len_result > 0 else 0
}
""")
    )
    
    end = Node.create(
        node_type="end",
        position=Position(x=700, y=100)
    )
    
    workflow.nodes = [start, code_sum, code_len, code_combine, end]
    workflow.edges = [
        Edge.create(source=start.id, target=code_sum.id),
        Edge.create(source=start.id, target=code_len.id),
        Edge.create(source=code_sum.id, target=code_combine.id),
        Edge.create(source=code_len.id, target=code_combine.id),
        Edge.create(source=code_combine.id, target=end.id),
    ]
    
    runner = WorkflowRunner(workflow)
    
    original_resolve_inputs = runner._resolve_inputs
    
    def custom_resolve(node_model):
        inputs = original_resolve_inputs(node_model)
        
        if node_model.id == code_combine.id:
            sum_output = runner.node_outputs.get(code_sum.id, {})
            len_output = runner.node_outputs.get(code_len.id, {})
            
            if isinstance(sum_output, dict) and "result" in sum_output:
                inputs["sum_result"] = sum_output["result"]
            if isinstance(len_output, dict) and "result" in len_output:
                inputs["len_result"] = len_output["result"]
        
        return inputs
    
    runner._resolve_inputs = custom_resolve
    
    result = runner.run()
    
    print(f"  Status: {result['status']}")
    print(f"  Result: {result['result']}")
    print(f"  Logs: {result['logs']}")
    
    assert result["status"] == "success"
    
    final_result = result["result"]
    assert final_result["sum"] == 15
    assert final_result["length"] == 5
    assert final_result["average"] == 3.0
    
    print("  Data flow between nodes: OK")
    print("Data flow test passed!\n")


def test_placeholder_resolution():
    print("Testing placeholder resolution...")
    
    workflow = Workflow.create(name="Placeholder Test")
    
    runner = WorkflowRunner(workflow)
    runner.node_outputs = {
        "node_a": {"result": {"value": 42, "name": "Test"}},
        "node_b": {"result": "hello"}
    }
    
    result1 = runner._resolve_placeholders("${node_a.result.value}")
    assert result1 == 42, f"Expected 42, got {result1}"
    print("  Simple placeholder: OK")
    
    result2 = runner._resolve_placeholders("Value is ${node_b.result}")
    assert result2 == "Value is hello", f"Expected 'Value is hello', got {result2}"
    print("  String interpolation: OK")
    
    result3 = runner._resolve_placeholders("${node_a.result}")
    assert isinstance(result3, dict)
    assert result3["value"] == 42
    print("  Dict placeholder: OK")
    
    print("Placeholder resolution test passed!\n")


def test_condition_node():
    print("Testing condition node in workflow...")
    
    workflow = Workflow.create(name="Condition Flow")
    
    start = Node.create(
        node_type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(params={"value": 15})
    )
    
    condition = Node.create(
        node_type="condition",
        position=Position(x=300, y=100),
        config=NodeConfig(params={
            "expression": "value > 10",
            "true_value": "High",
            "false_value": "Low"
        })
    )
    
    end = Node.create(
        node_type="end",
        position=Position(x=500, y=100)
    )
    
    workflow.nodes = [start, condition, end]
    workflow.edges = [
        Edge.create(source=start.id, target=condition.id),
        Edge.create(source=condition.id, target=end.id),
    ]
    
    runner = WorkflowRunner(workflow)
    
    original_resolve_inputs = runner._resolve_inputs
    
    def custom_resolve(node_model):
        inputs = original_resolve_inputs(node_model)
        
        if node_model.id == condition.id:
            start_output = runner.node_outputs.get(start.id, {})
            if isinstance(start_output, dict) and "params" in start_output:
                inputs["value"] = start_output["params"].get("value")
        
        return inputs
    
    runner._resolve_inputs = custom_resolve
    
    result = runner.run()
    
    print(f"  Status: {result['status']}")
    print(f"  Result: {result['result']}")
    
    assert result["status"] == "success"
    
    condition_output = runner.node_outputs.get(condition.id, {})
    assert condition_output.get("condition") is True
    assert condition_output.get("true") == "High"
    
    print("  Condition node execution: OK")
    print("Condition node test passed!\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Task 4 Validation Tests")
    print("=" * 50 + "\n")
    
    try:
        test_topological_sort()
        test_cycle_detection()
        test_simple_workflow_execution()
        test_data_flow_between_nodes()
        test_placeholder_resolution()
        test_condition_node()
        
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
