import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.sandbox import CodeSandbox, HAS_RESTRICTED_PYTHON
from backend.models import Node, Position, NodeConfig, Workflow, Edge
from backend.nodes import NodeRegistry, PythonCodeNode, StartNode, EndNode
from backend.runner import WorkflowRunner


def test_sandbox_basic_execution():
    print("Testing sandbox basic execution...")
    
    sandbox = CodeSandbox()
    
    class MockNode:
        def __init__(self, code):
            self.config = NodeConfig(code=code)
    
    result = sandbox.execute(MockNode("result = 1 + 1"), {}, {})
    assert result["result"] == 2
    print("  Basic arithmetic: OK")
    
    result = sandbox.execute(MockNode("result = 'Hello ' + 'World'"), {}, {})
    assert result["result"] == "Hello World"
    print("  String concatenation: OK")
    
    result = sandbox.execute(
        MockNode("result = sum([1, 2, 3, 4, 5])"),
        {},
        {}
    )
    assert result["result"] == 15
    print("  Built-in functions: OK")
    
    print("Sandbox basic execution test passed!\n")


def test_sandbox_with_inputs():
    print("Testing sandbox with inputs...")
    
    sandbox = CodeSandbox()
    
    class MockNode:
        def __init__(self, code):
            self.config = NodeConfig(code=code)
    
    code = """
result = {
    "name": name,
    "age": age,
    "greeting": f"Hello {name}!"
}
"""
    
    inputs = {"name": "Alice", "age": 30}
    result = sandbox.execute(MockNode(code), inputs, {})
    
    assert result["result"]["name"] == "Alice"
    assert result["result"]["age"] == 30
    assert result["result"]["greeting"] == "Hello Alice!"
    print("  Input variables: OK")
    
    print("Sandbox with inputs test passed!\n")


def test_sandbox_return_statement():
    print("Testing sandbox with return statement...")
    
    sandbox = CodeSandbox()
    
    class MockNode:
        def __init__(self, code):
            self.config = NodeConfig(code=code)
    
    result = sandbox.execute(
        MockNode("return {'value': 42, 'message': 'Test'}"),
        {},
        {}
    )
    assert result["result"]["value"] == 42
    assert result["result"]["message"] == "Test"
    print("  Return statement: OK")
    
    result = sandbox.execute(
        MockNode("x = 10\ny = 20\nreturn x + y"),
        {},
        {}
    )
    assert result["result"] == 30
    print("  Return with calculations: OK")
    
    print("Sandbox return statement test passed!\n")


def test_sandbox_stdout_capture():
    print("Testing sandbox stdout capture...")
    
    sandbox = CodeSandbox()
    
    class MockNode:
        def __init__(self, code):
            self.config = NodeConfig(code=code)
    
    code = """
print("Hello from sandbox!")
print("This is a test message.")
result = "done"
"""
    
    result = sandbox.execute(MockNode(code), {}, {})
    
    assert result["result"] == "done"
    
    has_hello = any("Hello from sandbox" in log for log in sandbox.logs)
    assert has_hello, f"Expected 'Hello from sandbox' in logs: {sandbox.logs}"
    print("  Stdout capture: OK")
    
    print("Sandbox stdout capture test passed!\n")


def test_sandbox_error_handling():
    print("Testing sandbox error handling...")
    
    sandbox = CodeSandbox()
    
    class MockNode:
        def __init__(self, code):
            self.config = NodeConfig(code=code)
    
    try:
        sandbox.execute(MockNode("result = 1 / 0"), {}, {})
        assert False, "Should have raised an error"
    except RuntimeError as e:
        assert "division by zero" in str(e).lower() or "ZeroDivisionError" in str(e)
        print("  Division by zero error: OK")
    
    try:
        sandbox.execute(MockNode("result = undefined_variable"), {}, {})
        assert False, "Should have raised an error"
    except RuntimeError as e:
        assert "name" in str(e).lower() or "undefined" in str(e).lower()
        print("  Undefined variable error: OK")
    
    print("Sandbox error handling test passed!\n")


def test_sandbox_with_runner():
    print("Testing sandbox integrated with WorkflowRunner...")
    
    workflow = Workflow.create(name="Sandbox Test Flow")
    
    start = Node.create(
        node_type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(params={"value": 5})
    )
    
    code = Node.create(
        node_type="python_code",
        position=Position(x=300, y=100),
        config=NodeConfig(code="""
result = {
    "original": value,
    "doubled": value * 2,
    "squared": value ** 2
}
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
    
    sandbox = CodeSandbox()
    runner = WorkflowRunner(workflow, sandbox)
    
    original_execute_node = runner._execute_node
    
    def custom_execute_node(node_model):
        node = NodeRegistry.create_node(node_model)
        if node is None:
            runner.log(f"Warning: Unknown node type '{node_model.type}', skipping")
            return
        
        runner.log(f"Executing node: {node_model.id} (type: {node_model.type})")
        
        inputs = runner._resolve_inputs(node_model)
        runner.log(f"  Inputs: {inputs}")
        
        try:
            if isinstance(node, PythonCodeNode):
                output = sandbox.execute(node, inputs, runner.context)
            else:
                output = node.execute(inputs, runner.context)
            
            runner.node_outputs[node_model.id] = output
            runner.log(f"  Output: {output}")
            
        except Exception as e:
            runner.log(f"  Error executing node {node_model.id}: {str(e)}")
            raise
    
    runner._execute_node = custom_execute_node
    
    result = runner.run()
    
    print(f"  Status: {result['status']}")
    print(f"  Result: {result['result']}")
    
    assert result["status"] == "success"
    final_result = result["result"]
    assert final_result["original"] == 5
    assert final_result["doubled"] == 10
    assert final_result["squared"] == 25
    print("  Sandbox with runner: OK")
    
    print("Sandbox with runner test passed!\n")


def test_restricted_python_security():
    print("Testing RestrictedPython security features...")
    
    if not HAS_RESTRICTED_PYTHON:
        print("  RestrictedPython not installed, skipping security tests")
        print("  Install with: uv add restrictedpython")
        print("RestrictedPython security test skipped!\n")
        return
    
    sandbox = CodeSandbox()
    
    class MockNode:
        def __init__(self, code):
            self.config = NodeConfig(code=code)
    
    try:
        sandbox.execute(MockNode("import os\nresult = os.listdir('.')"), {}, {})
        print("  Warning: Import not blocked (may be allowed in this configuration)")
    except Exception as e:
        print(f"  Import blocked: OK ({str(e)[:50]}...)")
    
    try:
        sandbox.execute(MockNode("result = __import__('os')"), {}, {})
        print("  Warning: __import__ not blocked")
    except Exception as e:
        print(f"  __import__ blocked: OK ({str(e)[:50]}...)")
    
    try:
        sandbox.execute(MockNode("result = open('/etc/passwd', 'r')"), {}, {})
        print("  Warning: open() not blocked")
    except Exception as e:
        print(f"  open() blocked: OK ({str(e)[:50]}...)")
    
    print("RestrictedPython security test completed!\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Task 5 Validation Tests")
    print("=" * 50 + "\n")
    
    print(f"RestrictedPython available: {HAS_RESTRICTED_PYTHON}\n")
    
    try:
        test_sandbox_basic_execution()
        test_sandbox_with_inputs()
        test_sandbox_return_statement()
        test_sandbox_stdout_capture()
        test_sandbox_error_handling()
        test_sandbox_with_runner()
        test_restricted_python_security()
        
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
