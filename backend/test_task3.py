import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.models import Node, Position, NodeConfig, Workflow
from backend.nodes import (
    BaseNode, StartNode, EndNode, PythonCodeNode, 
    ConditionNode, NodeRegistry
)


def test_node_registry():
    print("Testing NodeRegistry...")
    
    all_types = NodeRegistry.get_all()
    assert len(all_types) >= 4
    print(f"  Registered {len(all_types)} node types")
    
    start_class = NodeRegistry.get("start")
    assert start_class is not None
    assert start_class == StartNode
    print("  get('start'): OK")
    
    unknown = NodeRegistry.get("unknown_type")
    assert unknown is None
    print("  get('unknown'): OK (returns None)")
    
    types_info = NodeRegistry.get_node_types()
    assert len(types_info) == len(all_types)
    for t in types_info:
        assert "type" in t
        assert "label" in t
    print("  get_node_types(): OK")
    
    print("NodeRegistry tests passed!\n")


def test_start_node():
    print("Testing StartNode...")
    
    config = NodeConfig(params={"name": "World", "count": 42})
    node_model = Node.create(
        node_type="start",
        position=Position(x=100, y=100),
        config=config,
        label="Test Start"
    )
    
    start_node = NodeRegistry.create_node(node_model)
    assert start_node is not None
    assert isinstance(start_node, StartNode)
    print("  create_node: OK")
    
    result = start_node.execute({}, {})
    assert "params" in result
    assert result["params"]["name"] == "World"
    assert result["params"]["count"] == 42
    print("  execute returns params: OK")
    
    default_config = StartNode.get_default_config()
    assert isinstance(default_config, NodeConfig)
    print("  get_default_config: OK")
    
    print("StartNode tests passed!\n")


def test_end_node():
    print("Testing EndNode...")
    
    node_model = Node.create(
        node_type="end",
        position=Position(x=100, y=100)
    )
    
    end_node = NodeRegistry.create_node(node_model)
    assert end_node is not None
    assert isinstance(end_node, EndNode)
    
    context = {}
    inputs = {"result": {"data": "final result"}}
    result = end_node.execute(inputs, context)
    
    assert "__final_result__" in context
    assert context["__final_result__"]["data"] == "final result"
    print("  execute stores result in context: OK")
    
    result = end_node.execute({"direct": "input"}, {})
    print("EndNode tests passed!\n")


def test_python_code_node():
    print("Testing PythonCodeNode...")
    
    code = """
result = x + y
return {"sum": result, "product": x * y}
"""
    config = NodeConfig(code=code)
    node_model = Node.create(
        node_type="python_code",
        position=Position(x=100, y=100),
        config=config
    )
    
    code_node = NodeRegistry.create_node(node_model)
    assert code_node is not None
    assert isinstance(code_node, PythonCodeNode)
    
    inputs = {"x": 5, "y": 3}
    result = code_node.execute(inputs, {})
    
    assert "result" in result
    output = result["result"]
    assert output["sum"] == 8
    assert output["product"] == 15
    print("  execute with variables: OK")
    
    hello_code = 'return "Hello " + name'
    config2 = NodeConfig(code=hello_code)
    node_model2 = Node.create(
        node_type="python_code",
        position=Position(x=100, y=100),
        config=config2
    )
    code_node2 = PythonCodeNode(node_model2)
    result2 = code_node2.execute({"name": "World"}, {})
    assert result2["result"] == "Hello World"
    print("  execute simple return: OK")
    
    default_config = PythonCodeNode.get_default_config()
    assert "code" in default_config.to_dict()
    print("  get_default_config has code: OK")
    
    print("PythonCodeNode tests passed!\n")


def test_condition_node():
    print("Testing ConditionNode...")
    
    config = NodeConfig(params={
        "expression": "value > 10",
        "true_value": "High",
        "false_value": "Low"
    })
    node_model = Node.create(
        node_type="condition",
        position=Position(x=100, y=100),
        config=config
    )
    
    cond_node = NodeRegistry.create_node(node_model)
    assert cond_node is not None
    assert isinstance(cond_node, ConditionNode)
    
    result1 = cond_node.execute({"value": 15}, {})
    assert result1["condition"] is True
    assert result1["true"] == "High"
    print("  condition true: OK")
    
    result2 = cond_node.execute({"value": 5}, {})
    assert result2["condition"] is False
    assert result2["false"] == "Low"
    print("  condition false: OK")
    
    print("ConditionNode tests passed!\n")


def test_node_creation_from_registry():
    print("Testing NodeRegistry.create_node for all types...")
    
    test_cases = [
        ("start", StartNode),
        ("end", EndNode),
        ("python_code", PythonCodeNode),
        ("condition", ConditionNode),
    ]
    
    for node_type, expected_class in test_cases:
        node_model = Node.create(
            node_type=node_type,
            position=Position(x=0, y=0)
        )
        node = NodeRegistry.create_node(node_model)
        assert node is not None
        assert isinstance(node, expected_class)
        print(f"  {node_type} -> {expected_class.__name__}: OK")
    
    print("All node type creation tests passed!\n")


def test_simple_flow():
    print("Testing simple flow simulation (Start -> Code -> End)...")
    
    start_model = Node.create(
        node_type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(params={"name": "Alice", "age": 30})
    )
    start_node = NodeRegistry.create_node(start_model)
    
    code = 'return f"Name: {name}, Age: {age}"'
    code_model = Node.create(
        node_type="python_code",
        position=Position(x=300, y=100),
        config=NodeConfig(code=code)
    )
    code_node = NodeRegistry.create_node(code_model)
    
    end_model = Node.create(
        node_type="end",
        position=Position(x=500, y=100)
    )
    end_node = NodeRegistry.create_node(end_model)
    
    context = {}
    
    start_output = start_node.execute({}, context)
    print(f"  Start output: {start_output}")
    
    code_inputs = start_output["params"]
    code_output = code_node.execute(code_inputs, context)
    print(f"  Code output: {code_output}")
    
    end_inputs = {"result": code_output["result"]}
    end_node.execute(end_inputs, context)
    print(f"  Final result in context: {context.get('__final_result__')}")
    
    assert context["__final_result__"] == "Name: Alice, Age: 30"
    print("  Flow simulation: OK")
    
    print("Simple flow test passed!\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Task 3 Validation Tests")
    print("=" * 50 + "\n")
    
    try:
        test_node_registry()
        test_start_node()
        test_end_node()
        test_python_code_node()
        test_condition_node()
        test_node_creation_from_registry()
        test_simple_flow()
        
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
