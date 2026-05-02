"""
Unit tests for runner module.
Tests WorkflowRunner class, topological sort, data flow, and execution.
"""

import pytest
from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.runner import WorkflowRunner
from backend.nodes import NodeRegistry
from backend.sandbox import CodeSandbox


class TestTopologicalSort:
    """Tests for topological sorting."""

    def test_linear_chain(self):
        """Test topological sort on a linear chain: Start -> Code -> End."""
        workflow = Workflow.create(name="Linear Flow")
        
        start = Node.create(node_type="start", position=Position(x=100, y=100))
        code = Node.create(node_type="python_code", position=Position(x=300, y=100))
        end = Node.create(node_type="end", position=Position(x=500, y=100))
        
        workflow.nodes = [start, code, end]
        workflow.edges = [
            Edge.create(source=start.id, target=code.id),
            Edge.create(source=code.id, target=end.id),
        ]
        
        runner = WorkflowRunner(workflow)
        order = runner._topological_sort()
        order_ids = [n.id for n in order]
        
        assert order_ids.index(start.id) < order_ids.index(code.id)
        assert order_ids.index(code.id) < order_ids.index(end.id)

    def test_parallel_branches(self):
        """Test topological sort with parallel branches."""
        workflow = Workflow.create(name="Parallel Flow")
        
        start = Node.create(node_type="start", position=Position(x=100, y=100))
        code1 = Node.create(node_type="python_code", position=Position(x=300, y=50))
        code2 = Node.create(node_type="python_code", position=Position(x=300, y=150))
        end = Node.create(node_type="end", position=Position(x=500, y=100))
        
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

    def test_cycle_detection(self):
        """Test that cycles are detected and raise error."""
        workflow = Workflow.create(name="Cyclic Flow")
        
        node1 = Node.create(node_type="python_code", position=Position(x=100, y=100))
        node2 = Node.create(node_type="python_code", position=Position(x=300, y=100))
        
        workflow.nodes = [node1, node2]
        workflow.edges = [
            Edge.create(source=node1.id, target=node2.id),
            Edge.create(source=node2.id, target=node1.id),
        ]
        
        runner = WorkflowRunner(workflow)
        
        with pytest.raises(RuntimeError) as exc_info:
            runner._topological_sort()
        
        assert "cycle" in str(exc_info.value).lower()

    def test_single_node(self):
        """Test topological sort with single node."""
        workflow = Workflow.create(name="Single Node")
        
        start = Node.create(node_type="start", position=Position(x=100, y=100))
        workflow.nodes = [start]
        workflow.edges = []
        
        runner = WorkflowRunner(workflow)
        order = runner._topological_sort()
        
        assert len(order) == 1
        assert order[0].id == start.id

    def test_no_edges(self):
        """Test topological sort with multiple nodes but no edges."""
        workflow = Workflow.create(name="No Edges")
        
        node1 = Node.create(node_type="start", position=Position(x=100, y=100))
        node2 = Node.create(node_type="python_code", position=Position(x=300, y=100))
        node3 = Node.create(node_type="end", position=Position(x=500, y=100))
        
        workflow.nodes = [node1, node2, node3]
        workflow.edges = []
        
        runner = WorkflowRunner(workflow)
        order = runner._topological_sort()
        
        assert len(order) == 3


class TestSimpleWorkflowExecution:
    """Tests for simple workflow execution."""

    def test_hello_world_flow(self):
        """Test simple Start -> Code -> End flow."""
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
        
        assert result["status"] == "success"
        assert result["result"] is not None
        
        final_result = result["result"]
        assert isinstance(final_result, dict)
        assert final_result["greeting"] == "Hello World"
        assert final_result["doubled"] == 20

    def test_workflow_with_sandbox(self):
        """Test workflow execution with CodeSandbox."""
        workflow = Workflow.create(name="Sandbox Flow")
        
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
        result = runner.run()
        
        assert result["status"] == "success"
        final_result = result["result"]
        assert final_result["original"] == 5
        assert final_result["doubled"] == 10
        assert final_result["squared"] == 25

    def test_empty_workflow(self):
        """Test execution of empty workflow."""
        workflow = Workflow.create(name="Empty Flow")
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"
        assert result["result"] is None

    def test_start_only_workflow(self):
        """Test workflow with only Start node."""
        workflow = Workflow.create(name="Start Only")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"test": "value"})
        )
        
        workflow.nodes = [start]
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"

    def test_error_in_node(self):
        """Test error handling during node execution."""
        workflow = Workflow.create(name="Error Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={})
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = 1 / 0")
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
        
        assert result["status"] == "error"
        assert "division by zero" in result["error"].lower() or "ZeroDivisionError" in result["error"]


class TestDataFlow:
    """Tests for data flow between nodes."""

    def test_start_node_params_passed(self):
        """Test that Start node params are passed to downstream nodes."""
        workflow = Workflow.create(name="Params Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"x": 10, "y": 20})
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = x + y")
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
        
        assert result["status"] == "success"
        assert result["result"] == 30

    def test_multiple_inputs_merged(self):
        """Test that inputs from multiple sources are merged."""
        workflow = Workflow.create(name="Merge Flow")
        
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
        
        workflow.nodes = [start, code_sum, code_len]
        workflow.edges = [
            Edge.create(source=start.id, target=code_sum.id),
            Edge.create(source=start.id, target=code_len.id),
        ]
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"
        
        sum_output = runner.node_outputs.get(code_sum.id, {})
        len_output = runner.node_outputs.get(code_len.id, {})
        
        assert sum_output.get("result") == 15
        assert len_output.get("result") == 5


class TestPlaceholderResolution:
    """Tests for placeholder resolution in _resolve_placeholders."""

    def test_simple_placeholder(self):
        """Test resolution of simple placeholder like ${node.key}."""
        workflow = Workflow.create(name="Placeholder Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node_a": {"params": {"value": 42}}
        }
        
        result = runner._resolve_placeholders("${node_a.params.value}")
        assert result == 42

    def test_string_interpolation(self):
        """Test placeholder in string interpolation."""
        workflow = Workflow.create(name="Interpolation Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node_a": {"result": "hello"}
        }
        
        result = runner._resolve_placeholders("Value is ${node_a.result}")
        assert result == "Value is hello"

    def test_dict_placeholder(self):
        """Test placeholder that returns entire dict."""
        workflow = Workflow.create(name="Dict Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node_a": {"result": {"value": 42, "name": "Test"}}
        }
        
        result = runner._resolve_placeholders("${node_a.result}")
        assert isinstance(result, dict)
        assert result["value"] == 42
        assert result["name"] == "Test"

    def test_nested_value_access(self):
        """Test nested value access in placeholders."""
        workflow = Workflow.create(name="Nested Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "data": {"result": {"user": {"name": "Alice", "age": 30}}}
        }
        
        assert runner._resolve_placeholders("${data.result.user.name}") == "Alice"
        assert runner._resolve_placeholders("${data.result.user.age}") == 30

    def test_list_access(self):
        """Test list index access in placeholders."""
        workflow = Workflow.create(name="List Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "data": {"result": [10, 20, 30, 40, 50]}
        }
        
        assert runner._resolve_placeholders("${data.result.0}") == 10
        assert runner._resolve_placeholders("${data.result.2}") == 30

    def test_unknown_node_returns_original(self):
        """Test unknown node returns original string."""
        workflow = Workflow.create(name="Unknown Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "known": {"result": "value"}
        }
        
        result = runner._resolve_placeholders("${unknown.result}")
        assert result == "${unknown.result}"

    def test_unknown_key_returns_original(self):
        """Test unknown key returns original string."""
        workflow = Workflow.create(name="Unknown Key Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node": {"result": {"known": "value"}}
        }
        
        result = runner._resolve_placeholders("${node.result.unknown}")
        assert result == "${node.result.unknown}"

    def test_dict_value_placeholder(self):
        """Test placeholder resolution in dict values."""
        workflow = Workflow.create(name="Dict Value Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node": {"result": 42}
        }
        
        result = runner._resolve_placeholders({
            "static": "value",
            "dynamic": "${node.result}"
        })
        
        assert result["static"] == "value"
        assert result["dynamic"] == 42

    def test_list_value_placeholder(self):
        """Test placeholder resolution in list values."""
        workflow = Workflow.create(name="List Value Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node": {"result": 100}
        }
        
        result = runner._resolve_placeholders([
            "static",
            "${node.result}",
            "${node.result} multiplied"
        ])
        
        assert result[0] == "static"
        assert result[1] == 100
        assert result[2] == "100 multiplied"

    def test_non_string_non_collection_passthrough(self):
        """Test that non-string, non-collection values pass through unchanged."""
        workflow = Workflow.create(name="Passthrough Test")
        
        runner = WorkflowRunner(workflow)
        
        assert runner._resolve_placeholders(42) == 42
        assert runner._resolve_placeholders(3.14) == 3.14
        assert runner._resolve_placeholders(True) is True
        assert runner._resolve_placeholders(None) is None


class TestConditionNodeInWorkflow:
    """Tests for Condition node in workflow context."""

    def test_condition_true_branch(self):
        """Test condition node when condition is true."""
        workflow = Workflow.create(name="Condition True Flow")
        
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
                "true_value": {"result": "High"},
                "false_value": {"result": "Low"}
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
        result = runner.run()
        
        assert result["status"] == "success"
        
        condition_output = runner.node_outputs.get(condition.id, {})
        assert condition_output.get("condition") is True
        assert condition_output.get("true") == {"result": "High"}

    def test_condition_false_branch(self):
        """Test condition node when condition is false."""
        workflow = Workflow.create(name="Condition False Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"value": 5})
        )
        
        condition = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "value > 10",
                "true_value": {"result": "High"},
                "false_value": {"result": "Low"}
            })
        )
        
        workflow.nodes = [start, condition]
        workflow.edges = [
            Edge.create(source=start.id, target=condition.id),
        ]
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"
        
        condition_output = runner.node_outputs.get(condition.id, {})
        assert condition_output.get("condition") is False
        assert condition_output.get("false") == {"result": "Low"}

    def test_complex_condition_expression(self):
        """Test complex condition expressions."""
        workflow = Workflow.create(name="Complex Condition Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={
                "name": "Alice",
                "age": 25,
                "score": 85,
                "items": [1, 2, 3]
            })
        )
        
        condition = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "age >= 18 and score >= 80 and len(items) > 0",
                "true_value": {"result": "All conditions passed"},
                "false_value": {"result": "Some conditions failed"}
            })
        )
        
        workflow.nodes = [start, condition]
        workflow.edges = [
            Edge.create(source=start.id, target=condition.id),
        ]
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"
        
        condition_output = runner.node_outputs.get(condition.id, {})
        assert condition_output.get("condition") is True


class TestRunnerLogging:
    """Tests for runner logging functionality."""

    def test_runner_logs_execution(self):
        """Test that runner logs execution steps."""
        workflow = Workflow.create(name="Logging Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"test": "value"})
        )
        
        end = Node.create(
            node_type="end",
            position=Position(x=300, y=100)
        )
        
        workflow.nodes = [start, end]
        workflow.edges = [
            Edge.create(source=start.id, target=end.id),
        ]
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"
        assert len(result["logs"]) > 0
        assert any("Starting workflow" in log for log in result["logs"])
        assert any("Execution order" in log for log in result["logs"])
        assert any("Executing node" in log for log in result["logs"])

    def test_runner_node_outputs_recorded(self):
        """Test that node outputs are recorded in result."""
        workflow = Workflow.create(name="Outputs Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"value": 42})
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = value * 2")
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
        
        assert result["status"] == "success"
        assert "node_outputs" in result
        assert len(result["node_outputs"]) > 0


class TestInputResolution:
    """Tests for _resolve_inputs method."""

    def test_resolve_inputs_from_prev_node(self):
        """Test inputs resolved from previous node output."""
        workflow = Workflow.create(name="Input Resolution Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"x": 10, "y": 20})
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        
        workflow.nodes = [start, code]
        workflow.edges = [
            Edge.create(source=start.id, target=code.id),
        ]
        
        runner = WorkflowRunner(workflow)
        
        runner.node_outputs[start.id] = {"params": {"x": 10, "y": 20}}
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["x"] == 10
        assert inputs["y"] == 20

    def test_resolve_inputs_with_config_inputs(self):
        """Test inputs from config.inputs with placeholders."""
        workflow = Workflow.create(name="Config Inputs Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"base": 10}),
            node_id="start"
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(
                code="",
                inputs={"multiplier": 2, "msg": "Value is ${start.params.base}"}
            )
        )
        
        workflow.nodes = [start, code]
        workflow.edges = [
            Edge.create(source=start.id, target=code.id),
        ]
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs["start"] = {"params": {"base": 10}}
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["multiplier"] == 2
        assert inputs["base"] == 10
        assert inputs["msg"] == "Value is 10"


class TestUnknownNodeType:
    """Tests for handling unknown node types."""

    def test_unknown_node_type_skipped(self):
        """Test that unknown node types are skipped with warning."""
        workflow = Workflow.create(name="Unknown Node Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"value": 42})
        )
        
        unknown = Node(
            id="unknown_node",
            type="non_existent_type",
            position=Position(x=300, y=100),
            config=NodeConfig()
        )
        
        end = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        
        workflow.nodes = [start, unknown, end]
        workflow.edges = [
            Edge.create(source=start.id, target=unknown.id),
            Edge.create(source=unknown.id, target=end.id),
        ]
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"
        assert any("Unknown node type" in log or "non_existent_type" in log for log in result["logs"])


class TestNestedValueAccess:
    """Tests for _get_nested_value method edge cases."""

    def test_single_part_path_returns_node_output(self):
        """Test that path with single part returns entire node output."""
        workflow = Workflow.create(name="Single Part Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node": {"result": 42, "other": "value"}
        }
        
        result = runner._get_nested_value("node")
        assert result == {"result": 42, "other": "value"}

    def test_empty_path_returns_none(self):
        """Test that empty path returns None."""
        workflow = Workflow.create(name="Empty Path Test")
        
        runner = WorkflowRunner(workflow)
        result = runner._get_nested_value("")
        assert result is None

    def test_list_index_value_error_returns_none(self):
        """Test that invalid list index returns None."""
        workflow = Workflow.create(name="List Index Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "data": {"result": [1, 2, 3]}
        }
        
        result = runner._get_nested_value("data.result.invalid")
        assert result is None

    def test_list_index_out_of_range_returns_none(self):
        """Test that list index out of range returns None."""
        workflow = Workflow.create(name="List Range Test")
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "data": {"result": [1, 2, 3]}
        }
        
        result = runner._get_nested_value("data.result.100")
        assert result is None

    def test_non_dict_list_getattr(self):
        """Test getattr access on objects (simulated with tuple)."""
        workflow = Workflow.create(name="Getattr Test")
        
        class TestObj:
            def __init__(self):
                self.value = 42
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs = {
            "node": {"obj": TestObj()}
        }
        
        result = runner._get_nested_value("node.obj.value")
        assert result == 42


class TestSourceHandleInputs:
    """Tests for source_handle based input resolution."""

    def test_output_true_handle_with_dict_value(self):
        """Test source_handle='output-true' with dict value."""
        workflow = Workflow.create(name="True Handle Test")
        
        condition = Node.create(
            node_type="condition",
            position=Position(x=100, y=100),
            config=NodeConfig()
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        
        workflow.nodes = [condition, code]
        workflow.edges = [
            Edge.create(
                source=condition.id, 
                target=code.id,
                source_handle="output-true"
            ),
        ]
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs[condition.id] = {
            "true": {"x": 10, "y": 20},
            "_inputs": {"extra": "value"}
        }
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["x"] == 10
        assert inputs["y"] == 20
        assert inputs["extra"] == "value"

    def test_output_true_handle_with_non_dict_value(self):
        """Test source_handle='output-true' with non-dict value."""
        workflow = Workflow.create(name="True Handle Non-Dict Test")
        
        condition = Node.create(
            node_type="condition",
            position=Position(x=100, y=100),
            config=NodeConfig()
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        
        workflow.nodes = [condition, code]
        workflow.edges = [
            Edge.create(
                source=condition.id, 
                target=code.id,
                source_handle="output-true"
            ),
        ]
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs[condition.id] = {
            "true": 42
        }
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["result"] == 42

    def test_output_false_handle_with_dict_value(self):
        """Test source_handle='output-false' with dict value."""
        workflow = Workflow.create(name="False Handle Test")
        
        condition = Node.create(
            node_type="condition",
            position=Position(x=100, y=100),
            config=NodeConfig()
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        
        workflow.nodes = [condition, code]
        workflow.edges = [
            Edge.create(
                source=condition.id, 
                target=code.id,
                source_handle="output-false"
            ),
        ]
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs[condition.id] = {
            "false": {"a": 1, "b": 2},
            "_inputs": {"backup": "value"}
        }
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["a"] == 1
        assert inputs["b"] == 2
        assert inputs["backup"] == "value"

    def test_output_false_handle_with_non_dict_value(self):
        """Test source_handle='output-false' with non-dict value."""
        workflow = Workflow.create(name="False Handle Non-Dict Test")
        
        condition = Node.create(
            node_type="condition",
            position=Position(x=100, y=100),
            config=NodeConfig()
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        
        workflow.nodes = [condition, code]
        workflow.edges = [
            Edge.create(
                source=condition.id, 
                target=code.id,
                source_handle="output-false"
            ),
        ]
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs[condition.id] = {
            "false": "error message"
        }
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["result"] == "error message"

    def test_non_dict_source_output(self):
        """Test when source_output is not a dict and not None."""
        workflow = Workflow.create(name="Non-Dict Output Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100)
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        
        workflow.nodes = [start, code]
        workflow.edges = [
            Edge.create(source=start.id, target=code.id),
        ]
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs[start.id] = 42
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["result"] == 42

    def test_source_output_with_params_key_only(self):
        """Test source_output with only 'params' key."""
        workflow = Workflow.create(name="Params Only Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100)
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        
        workflow.nodes = [start, code]
        workflow.edges = [
            Edge.create(source=start.id, target=code.id),
        ]
        
        runner = WorkflowRunner(workflow)
        runner.node_outputs[start.id] = {"params": {"x": 10, "y": 20}}
        
        inputs = runner._resolve_inputs(code)
        
        assert inputs["x"] == 10
        assert inputs["y"] == 20


class TestNoFinalResult:
    """Tests for workflow with no __final_result__ but has end node."""

    def test_end_node_output_used_as_final_result(self):
        """Test that end node output is used when no __final_result__."""
        workflow = Workflow.create(name="End Node Result Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"value": 100})
        )
        
        end = Node.create(
            node_type="end",
            position=Position(x=300, y=100)
        )
        
        workflow.nodes = [start, end]
        workflow.edges = [
            Edge.create(source=start.id, target=end.id),
        ]
        
        runner = WorkflowRunner(workflow)
        result = runner.run()
        
        assert result["status"] == "success"
        assert result["result"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
