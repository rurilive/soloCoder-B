"""
Unit tests for sandbox module.
Tests CodeSandbox class for safe code execution.
"""

import pytest
from backend.models import Node, Position, NodeConfig
from backend.sandbox import CodeSandbox, HAS_RESTRICTED_PYTHON, SandboxResult


class MockNode:
    """Mock node class for testing."""
    def __init__(self, code):
        self.config = NodeConfig(code=code)


class TestCodeSandbox:
    """Tests for CodeSandbox class."""

    def test_init(self):
        """Test sandbox initialization."""
        sandbox = CodeSandbox()
        assert sandbox.logs == []

    def test_log_method(self):
        """Test log method appends to logs and prints."""
        sandbox = CodeSandbox()
        sandbox.log("Test message")
        
        assert len(sandbox.logs) == 1
        assert "Test message" in sandbox.logs[0]

    def test_execute_basic_arithmetic(self):
        """Test basic arithmetic execution."""
        sandbox = CodeSandbox()
        
        result = sandbox.execute(MockNode("result = 1 + 1"), {}, {})
        assert result["result"] == 2
        
        result = sandbox.execute(MockNode("result = 10 * 5"), {}, {})
        assert result["result"] == 50
        
        result = sandbox.execute(MockNode("result = 100 / 4"), {}, {})
        assert result["result"] == 25.0

    def test_execute_string_operations(self):
        """Test string operations in sandbox."""
        sandbox = CodeSandbox()
        
        result = sandbox.execute(MockNode("result = 'Hello ' + 'World'"), {}, {})
        assert result["result"] == "Hello World"
        
        result = sandbox.execute(MockNode("result = len('test')"), {}, {})
        assert result["result"] == 4
        
        result = sandbox.execute(MockNode("result = 'hello'.upper()"), {}, {})
        assert result["result"] == "HELLO"

    def test_execute_with_inputs(self):
        """Test execution with input variables."""
        sandbox = CodeSandbox()
        
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

    def test_execute_empty_code(self):
        """Test execution with empty code returns None."""
        sandbox = CodeSandbox()
        
        result = sandbox.execute(MockNode(""), {}, {})
        assert result["result"] is None
        
        result = sandbox.execute(MockNode("   \n\n   "), {}, {})
        assert result["result"] is None

    def test_execute_with_return_statement(self):
        """Test execution with return statement."""
        sandbox = CodeSandbox()
        
        result = sandbox.execute(
            MockNode("return {'value': 42, 'message': 'Test'}"),
            {},
            {}
        )
        assert result["result"]["value"] == 42
        assert result["result"]["message"] == "Test"
        
        result = sandbox.execute(
            MockNode("x = 10\ny = 20\nreturn x + y"),
            {},
            {}
        )
        assert result["result"] == 30

    def test_execute_bare_return(self):
        """Test execution with bare return statement."""
        sandbox = CodeSandbox()
        
        result = sandbox.execute(
            MockNode("x = 10\nif x > 5:\n    return\nresult = 'done'"),
            {},
            {}
        )

    def test_execute_complex_code(self):
        """Test execution of complex code with loops and conditionals."""
        sandbox = CodeSandbox()
        
        code = """
total = 0
for i in range(1, 6):
    total += i

if total > 10:
    result = {"status": "high", "value": total}
else:
    result = {"status": "low", "value": total}
"""
        result = sandbox.execute(MockNode(code), {}, {})
        
        assert result["result"]["status"] == "high"
        assert result["result"]["value"] == 15

    def test_execute_list_operations(self):
        """Test list operations in sandbox."""
        sandbox = CodeSandbox()
        
        result = sandbox.execute(
            MockNode("result = sum([1, 2, 3, 4, 5])"),
            {},
            {}
        )
        assert result["result"] == 15
        
        result = sandbox.execute(
            MockNode("result = max([5, 2, 8, 1])"),
            {},
            {}
        )
        assert result["result"] == 8
        
        result = sandbox.execute(
            MockNode("result = min([5, 2, 8, 1])"),
            {},
            {}
        )
        assert result["result"] == 1
        
        result = sandbox.execute(
            MockNode("result = len([1, 2, 3])"),
            {},
            {}
        )
        assert result["result"] == 3

    def test_execute_dict_operations(self):
        """Test dictionary operations in sandbox."""
        sandbox = CodeSandbox()
        
        code = """
data = {"name": "Alice", "age": 30}
data["city"] = "New York"
result = data
"""
        result = sandbox.execute(MockNode(code), {}, {})
        
        assert result["result"]["name"] == "Alice"
        assert result["result"]["age"] == 30
        assert result["result"]["city"] == "New York"

    def test_execute_error_handling(self):
        """Test error handling in sandbox."""
        sandbox = CodeSandbox()
        
        with pytest.raises(RuntimeError) as exc_info:
            sandbox.execute(MockNode("result = 1 / 0"), {}, {})
        
        assert "division by zero" in str(exc_info.value).lower() or "ZeroDivisionError" in str(exc_info.value)

    def test_execute_undefined_variable_error(self):
        """Test error for undefined variable."""
        sandbox = CodeSandbox()
        
        with pytest.raises(RuntimeError):
            sandbox.execute(MockNode("result = undefined_var"), {}, {})

    def test_execute_syntax_error(self):
        """Test syntax error handling."""
        sandbox = CodeSandbox()
        
        with pytest.raises(RuntimeError):
            sandbox.execute(MockNode("result = 1 + "), {}, {})

    def test_execute_accesses_context(self):
        """Test that code can access context variable."""
        sandbox = CodeSandbox()
        
        result = sandbox.execute(
            MockNode("result = context.get('test_key', 'default')"),
            {},
            {"test_key": "context_value"}
        )
        assert result["result"] == "context_value"

    def test_process_code_replaces_return(self):
        """Test _process_code replaces return statements."""
        sandbox = CodeSandbox()
        
        code_with_return = "x = 5\nreturn x * 2"
        processed = sandbox._process_code(code_with_return)
        
        assert "return" not in processed.strip().split('\n')[-1]
        assert "result =" in processed

    def test_process_code_indented_return(self):
        """Test _process_code handles indented return."""
        sandbox = CodeSandbox()
        
        code = "x = 5\nif x > 0:\n    return 'positive'\nelse:\n    return 'non-positive'"
        processed = sandbox._process_code(code)
        
        assert "return 'positive'" not in processed
        assert "result = 'positive'" in processed
        assert "return 'non-positive'" not in processed
        assert "result = 'non-positive'" in processed

    def test_process_code_bare_return(self):
        """Test _process_code handles bare return."""
        sandbox = CodeSandbox()
        
        code = "if done:\n    return"
        processed = sandbox._process_code(code)
        
        assert "    result = None" in processed

    def test_process_code_no_return(self):
        """Test _process_code leaves code without return unchanged."""
        sandbox = CodeSandbox()
        
        code = "result = 1 + 1\nprint('done')"
        processed = sandbox._process_code(code)
        
        assert processed == code


class TestSandboxIntegration:
    """Integration tests for sandbox with workflow runner."""

    def test_sandbox_with_workflow_runner(self):
        """Test sandbox integrated with WorkflowRunner."""
        from backend.models import Workflow, Node, Edge, Position, NodeConfig
        from backend.runner import WorkflowRunner
        from backend.nodes import NodeRegistry, PythonCodeNode, StartNode, EndNode
        
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
        
        assert result["status"] == "success"
        final_result = result["result"]
        assert final_result["original"] == 5
        assert final_result["doubled"] == 10
        assert final_result["squared"] == 25


class TestSandboxResult:
    """Tests for SandboxResult class."""

    def test_init_defaults(self):
        """Test default initialization of SandboxResult."""
        result = SandboxResult()
        
        assert result.success is False
        assert result.result is None
        assert result.error is None
        assert result.logs == []
        assert result.stdout == ""
        assert result.stderr == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
