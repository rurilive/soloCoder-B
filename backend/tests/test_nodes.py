"""
Unit tests for nodes module.
Tests NodeRegistry, BaseNode subclasses, and node execution.
"""

import pytest
from backend.models import Node, Position, NodeConfig, Workflow, Edge
from backend.nodes import (
    BaseNode, StartNode, EndNode, PythonCodeNode,
    ConditionNode, NodeRegistry
)


class TestNodeRegistry:
    """Tests for NodeRegistry class."""

    def test_get_all_returns_registered_nodes(self):
        """Test get_all returns all registered node types."""
        all_nodes = NodeRegistry.get_all()
        assert len(all_nodes) >= 4
        
        node_types = [nc.node_type for nc in all_nodes]
        assert "start" in node_types
        assert "end" in node_types
        assert "python_code" in node_types
        assert "condition" in node_types

    def test_get_returns_correct_class(self):
        """Test get returns the correct class for each type."""
        assert NodeRegistry.get("start") == StartNode
        assert NodeRegistry.get("end") == EndNode
        assert NodeRegistry.get("python_code") == PythonCodeNode
        assert NodeRegistry.get("condition") == ConditionNode

    def test_get_unknown_type_returns_none(self):
        """Test get returns None for unknown type."""
        assert NodeRegistry.get("unknown_type") is None
        assert NodeRegistry.get("") is None
        assert NodeRegistry.get(None) is None

    def test_get_node_types_returns_metadata(self):
        """Test get_node_types returns metadata about all types."""
        types_info = NodeRegistry.get_node_types()
        assert len(types_info) == len(NodeRegistry.get_all())
        
        for info in types_info:
            assert "type" in info
            assert "label" in info
            assert "input_schema" in info
            assert "output_schema" in info

    def test_create_node_creates_correct_instance(self):
        """Test create_node creates correct instance type."""
        start_model = Node.create(
            node_type="start",
            position=Position(x=100, y=100)
        )
        start_node = NodeRegistry.create_node(start_model)
        assert isinstance(start_node, StartNode)

        end_model = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        end_node = NodeRegistry.create_node(end_model)
        assert isinstance(end_node, EndNode)

    def test_create_node_unknown_type_returns_none(self):
        """Test create_node returns None for unknown type."""
        unknown_model = Node.create(
            node_type="unknown",
            position=Position(x=100, y=100)
        )
        node = NodeRegistry.create_node(unknown_model)
        assert node is None


class TestStartNode:
    """Tests for StartNode class."""

    def test_node_type_and_label(self):
        """Test node_type and label class attributes."""
        assert StartNode.node_type == "start"
        assert StartNode.label == "Start"

    def test_get_default_config(self):
        """Test get_default_config returns expected default."""
        config = StartNode.get_default_config()
        assert isinstance(config, NodeConfig)
        assert config.params == {}
        assert config.outputs == {"params": {}}

    def test_execute_returns_params(self):
        """Test execute returns the params from config."""
        model = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"name": "World", "count": 42})
        )
        node = StartNode(model)
        
        result = node.execute({}, {})
        
        assert "params" in result
        assert result["params"]["name"] == "World"
        assert result["params"]["count"] == 42

    def test_execute_empty_params(self):
        """Test execute with empty params returns empty dict."""
        model = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig()
        )
        node = StartNode(model)
        
        result = node.execute({}, {})
        
        assert result["params"] == {}

    def test_get_input_output_definition(self):
        """Test input and output schemas."""
        model = Node.create(
            node_type="start",
            position=Position(x=100, y=100)
        )
        node = StartNode(model)
        
        assert node.get_input_definition() == {}
        output_def = node.get_output_definition()
        assert "params" in output_def


class TestEndNode:
    """Tests for EndNode class."""

    def test_node_type_and_label(self):
        """Test node_type and label class attributes."""
        assert EndNode.node_type == "end"
        assert EndNode.label == "End"

    def test_execute_stores_result_in_context(self):
        """Test execute stores result in context's __final_result__."""
        model = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        node = EndNode(model)
        context = {}
        inputs = {"result": {"data": "final result", "value": 42}}
        
        result = node.execute(inputs, context)
        
        assert "__final_result__" in context
        assert context["__final_result__"]["data"] == "final result"
        assert context["__final_result__"]["value"] == 42
        assert result == {}

    def test_execute_uses_inputs_if_no_result_key(self):
        """Test execute uses entire inputs if 'result' key not present."""
        model = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        node = EndNode(model)
        context = {}
        inputs = {"direct": "input", "other": "value"}
        
        node.execute(inputs, context)
        
        assert context["__final_result__"] == {"direct": "input", "other": "value"}

    def test_get_input_output_definition(self):
        """Test input and output schemas."""
        model = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        node = EndNode(model)
        
        input_def = node.get_input_definition()
        assert "result" in input_def
        assert node.get_output_definition() == {}


class TestPythonCodeNode:
    """Tests for PythonCodeNode class."""

    def test_node_type_and_label(self):
        """Test node_type and label class attributes."""
        assert PythonCodeNode.node_type == "python_code"
        assert PythonCodeNode.label == "Python Code"

    def test_get_default_config(self):
        """Test get_default_config has code field."""
        config = PythonCodeNode.get_default_config()
        assert isinstance(config, NodeConfig)
        assert "code" in config.to_dict()
        assert len(config.code) > 0

    def test_execute_basic_arithmetic(self):
        """Test execute with basic arithmetic."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = x + y")
        )
        node = PythonCodeNode(model)
        
        result = node.execute({"x": 5, "y": 3}, {})
        
        assert result["result"] == 8

    def test_execute_with_return_statement(self):
        """Test execute with return statement converted to result."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="return {'sum': x + y, 'product': x * y}")
        )
        node = PythonCodeNode(model)
        
        result = node.execute({"x": 5, "y": 3}, {})
        
        assert result["result"]["sum"] == 8
        assert result["result"]["product"] == 15

    def test_execute_empty_code_returns_none(self):
        """Test execute with empty code returns None."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        node = PythonCodeNode(model)
        
        result = node.execute({}, {})
        
        assert result["result"] is None

    def test_execute_whitespace_only_code(self):
        """Test execute with whitespace-only code returns None."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="   \n  \n   ")
        )
        node = PythonCodeNode(model)
        
        result = node.execute({}, {})
        
        assert result["result"] is None

    def test_execute_accesses_context(self):
        """Test execute can access context variable."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = context.get('test_key', 'default')")
        )
        node = PythonCodeNode(model)
        
        result = node.execute({}, {"test_key": "context_value"})
        
        assert result["result"] == "context_value"

    def test_execute_error_raises_runtime_error(self):
        """Test execute raises RuntimeError on code errors."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = 1 / 0")
        )
        node = PythonCodeNode(model)
        
        with pytest.raises(RuntimeError) as exc_info:
            node.execute({}, {})
        
        assert "division by zero" in str(exc_info.value).lower() or "ZeroDivisionError" in str(exc_info.value)

    def test_execute_undefined_variable_error(self):
        """Test execute raises error for undefined variable."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = undefined_var")
        )
        node = PythonCodeNode(model)
        
        with pytest.raises(RuntimeError):
            node.execute({}, {})

    def test_contains_return_statement_detection(self):
        """Test return statement detection."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        node = PythonCodeNode(model)
        
        assert node._contains_return_statement("result = 1 + 1") is False
        assert node._contains_return_statement("return 42") is True
        assert node._contains_return_statement("x = 5\nreturn x * 2") is True
        assert node._contains_return_statement('print("return")') is False

    def test_process_code_replaces_return(self):
        """Test _process_code replaces return statements."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        node = PythonCodeNode(model)
        
        code_with_return = "x = 5\nreturn x * 2"
        processed = node._process_code(code_with_return)
        
        assert "return" not in processed.strip().split('\n')[-1]
        assert "result =" in processed

    def test_process_code_indented_return(self):
        """Test _process_code handles indented return statements."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        node = PythonCodeNode(model)
        
        code = "x = 5\nif x > 0:\n    return 'positive'\nelse:\n    return 'non-positive'"
        processed = node._process_code(code)
        
        assert "return 'positive'" not in processed
        assert "result = 'positive'" in processed
        assert "return 'non-positive'" not in processed
        assert "result = 'non-positive'" in processed

    def test_process_code_bare_return(self):
        """Test _process_code handles bare return statement."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="")
        )
        node = PythonCodeNode(model)
        
        code = "if done:\n    return"
        processed = node._process_code(code)
        
        assert "    result = None" in processed

    def test_complex_code_execution(self):
        """Test complex code with loops and conditionals."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="""
total = 0
for i in range(values):
    total += i
    
if total > 10:
    result = {"status": "high", "value": total}
else:
    result = {"status": "low", "value": total}
""")
        )
        node = PythonCodeNode(model)
        
        result = node.execute({"values": 5}, {})
        
        assert result["result"]["status"] == "low"
        assert result["result"]["value"] == 10

    def test_string_operations(self):
        """Test string operations in code."""
        model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="""
greeting = f"Hello {name}!"
upper_greeting = greeting.upper()
length = len(upper_greeting)
result = {"greeting": greeting, "upper": upper_greeting, "length": length}
""")
        )
        node = PythonCodeNode(model)
        
        result = node.execute({"name": "World"}, {})
        
        assert result["result"]["greeting"] == "Hello World!"
        assert result["result"]["upper"] == "HELLO WORLD!"
        assert result["result"]["length"] == 12


class TestConditionNode:
    """Tests for ConditionNode class."""

    def test_node_type_and_label(self):
        """Test node_type and label class attributes."""
        assert ConditionNode.node_type == "condition"
        assert ConditionNode.label == "Condition"

    def test_get_default_config(self):
        """Test get_default_config has expected params."""
        config = ConditionNode.get_default_config()
        assert isinstance(config, NodeConfig)
        assert "expression" in config.params
        assert "true_value" in config.params
        assert "false_value" in config.params

    def test_execute_condition_true(self):
        """Test execute when condition is true."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "value > 10",
                "true_value": {"result": "High"},
                "false_value": {"result": "Low"}
            })
        )
        node = ConditionNode(model)
        
        result = node.execute({"value": 15}, {})
        
        assert result["condition"] is True
        assert result["true"] == {"result": "High"}
        assert result["false"] is None

    def test_execute_condition_false(self):
        """Test execute when condition is false."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "value > 10",
                "true_value": {"result": "High"},
                "false_value": {"result": "Low"}
            })
        )
        node = ConditionNode(model)
        
        result = node.execute({"value": 5}, {})
        
        assert result["condition"] is False
        assert result["true"] is None
        assert result["false"] == {"result": "Low"}

    def test_execute_default_expression(self):
        """Test execute uses default expression if missing."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={})
        )
        node = ConditionNode(model)
        
        result = node.execute({"value": 15}, {})
        
        assert result["condition"] is True

    def test_execute_complex_expression(self):
        """Test execute with complex boolean expressions."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "age >= 18 and score >= 80 and len(items) > 0",
                "true_value": {"result": "Pass"},
                "false_value": {"result": "Fail"}
            })
        )
        node = ConditionNode(model)
        
        inputs = {"age": 25, "score": 85, "items": [1, 2, 3]}
        result = node.execute(inputs, {})
        
        assert result["condition"] is True
        assert result["true"] == {"result": "Pass"}

    def test_execute_complex_expression_false(self):
        """Test complex expression that evaluates to false."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "age >= 18 and score >= 80",
                "true_value": {"result": "Pass"},
                "false_value": {"result": "Fail"}
            })
        )
        node = ConditionNode(model)
        
        inputs = {"age": 16, "score": 90}
        result = node.execute(inputs, {})
        
        assert result["condition"] is False
        assert result["false"] == {"result": "Fail"}

    def test_execute_passes_inputs_in_output(self):
        """Test execute includes _inputs in output."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "value > 0",
                "true_value": {},
                "false_value": {}
            })
        )
        node = ConditionNode(model)
        
        inputs = {"value": 10, "extra": "data"}
        result = node.execute(inputs, {})
        
        assert "_inputs" in result
        assert result["_inputs"]["value"] == 10
        assert result["_inputs"]["extra"] == "data"

    def test_execute_invalid_expression_raises_error(self):
        """Test execute raises RuntimeError for invalid expression."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "this is not valid python ++",
                "true_value": {},
                "false_value": {}
            })
        )
        node = ConditionNode(model)
        
        with pytest.raises(RuntimeError):
            node.execute({"value": 10}, {})

    def test_execute_undefined_variable_in_expression(self):
        """Test execute with undefined variable in expression."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "undefined_var > 0",
                "true_value": {},
                "false_value": {}
            })
        )
        node = ConditionNode(model)
        
        with pytest.raises(RuntimeError):
            node.execute({"other_var": 10}, {})

    def test_get_input_output_definition(self):
        """Test input and output schemas."""
        model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100)
        )
        node = ConditionNode(model)
        
        input_def = node.get_input_definition()
        assert "value" in input_def
        
        output_def = node.get_output_definition()
        assert "true" in output_def
        assert "false" in output_def

    def test_safe_builtins_available(self):
        """Test that safe builtins are available in condition expressions."""
        test_cases = [
            ("abs(-5) == 5", {}, True),
            ("len([1, 2, 3]) == 3", {}, True),
            ("str(123) == '123'", {}, True),
            ("int('42') == 42", {}, True),
            ("float('3.14') > 3", {}, True),
            ("bool(1) and bool('test')", {}, True),
            ("max(1, 2, 3) == 3", {}, True),
            ("min(1, 2, 3) == 1", {}, True),
            ("sum([1, 2, 3]) == 6", {}, True),
            ("sorted([3, 1, 2]) == [1, 2, 3]", {}, True),
            ("list(reversed([1, 2, 3])) == [3, 2, 1]", {}, True),
            ("round(3.7) == 4", {}, True),
        ]
        
        for expr, inputs, expected in test_cases:
            model = Node.create(
                node_type="condition",
                position=Position(x=300, y=100),
                config=NodeConfig(params={
                    "expression": expr,
                    "true_value": True,
                    "false_value": False
                })
            )
            node = ConditionNode(model)
            result = node.execute(inputs, {})
            assert result["condition"] == expected, f"Failed for: {expr}"


class TestNodeIntegration:
    """Integration tests for node system."""

    def test_start_to_end_flow(self):
        """Test simple Start -> End flow."""
        start_model = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"message": "Hello"})
        )
        end_model = Node.create(
            node_type="end",
            position=Position(x=300, y=100)
        )
        
        start_node = StartNode(start_model)
        end_node = EndNode(end_model)
        context = {}
        
        start_output = start_node.execute({}, context)
        end_inputs = {"result": start_output["params"]}
        end_node.execute(end_inputs, context)
        
        assert context["__final_result__"]["message"] == "Hello"

    def test_start_to_code_to_end_flow(self):
        """Test Start -> PythonCode -> End flow."""
        start_model = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"name": "Alice", "age": 30})
        )
        code_model = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="result = f'{name} is {age} years old'")
        )
        end_model = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        
        start_node = StartNode(start_model)
        code_node = PythonCodeNode(code_model)
        end_node = EndNode(end_model)
        context = {}
        
        start_output = start_node.execute({}, context)
        code_output = code_node.execute(start_output["params"], context)
        end_node.execute({"result": code_output["result"]}, context)
        
        assert context["__final_result__"] == "Alice is 30 years old"

    def test_conditional_flow(self):
        """Test flow with condition node."""
        start_model = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"value": 75})
        )
        condition_model = Node.create(
            node_type="condition",
            position=Position(x=300, y=100),
            config=NodeConfig(params={
                "expression": "value >= 50",
                "true_value": {"result": "Passed"},
                "false_value": {"result": "Failed"}
            })
        )
        end_model = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        
        start_node = StartNode(start_model)
        condition_node = ConditionNode(condition_model)
        end_node = EndNode(end_model)
        context = {}
        
        start_output = start_node.execute({}, context)
        condition_output = condition_node.execute(start_output["params"], context)
        
        assert condition_output["condition"] is True
        assert condition_output["true"]["result"] == "Passed"
        
        end_node.execute({"result": condition_output["true"]}, context)
        assert context["__final_result__"]["result"] == "Passed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
