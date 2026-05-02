"""
Unit tests for exporter module.
Tests WorkflowExporter class for code generation.
"""

import pytest
from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.exporter import WorkflowExporter


class TestWorkflowExporter:
    """Tests for WorkflowExporter class."""

    def test_init(self):
        """Test exporter initialization."""
        workflow = Workflow.create(name="Test Flow")
        exporter = WorkflowExporter(workflow)
        
        assert exporter.workflow == workflow

    def test_export_generates_valid_python(self):
        """Test export generates syntactically valid Python code."""
        workflow = Workflow.create(name="Simple Flow")
        
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
        
        workflow.nodes = [start, code, end]
        workflow.edges = [
            Edge.create(source=start.id, target=code.id),
            Edge.create(source=code.id, target=end.id),
        ]
        
        exporter = WorkflowExporter(workflow)
        code = exporter.export()
        
        compile(code, "<string>", "exec")
        
        assert "#!/usr/bin/env python3" in code
        assert "# Workflow: Simple Flow" in code
        assert "def run_workflow" in code
        assert 'if __name__ == "__main__"' in code

    def test_export_includes_imports(self):
        """Test export includes necessary imports."""
        workflow = Workflow.create(name="Imports Test")
        exporter = WorkflowExporter(workflow)
        code = exporter.export()
        
        assert "import math" in code
        assert "import json" in code

    def test_export_includes_workflow_name(self):
        """Test export includes workflow name in comment."""
        workflow = Workflow.create(name="My Custom Workflow")
        exporter = WorkflowExporter(workflow)
        code = exporter.export()
        
        assert "# Workflow: My Custom Workflow" in code

    def test_export_with_condition_node(self):
        """Test export with condition node."""
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
                "true_value": {"result": "High"},
                "false_value": {"result": "Low"}
            })
        )
        
        workflow.nodes = [start, condition]
        workflow.edges = [
            Edge.create(source=start.id, target=condition.id),
        ]
        
        exporter = WorkflowExporter(workflow)
        code = exporter.export()
        
        compile(code, "<string>", "exec")
        
        assert "condition" in code.lower()

    def test_export_with_multiple_nodes(self):
        """Test export with multiple nodes."""
        workflow = Workflow.create(name="Multi Node Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"values": [1, 2, 3]})
        )
        
        code1 = Node.create(
            node_type="python_code",
            position=Position(x=300, y=50),
            config=NodeConfig(code="result = sum(values)")
        )
        
        code2 = Node.create(
            node_type="python_code",
            position=Position(x=300, y=150),
            config=NodeConfig(code="result = len(values)")
        )
        
        end = Node.create(
            node_type="end",
            position=Position(x=500, y=100)
        )
        
        workflow.nodes = [start, code1, code2, end]
        workflow.edges = [
            Edge.create(source=start.id, target=code1.id),
            Edge.create(source=start.id, target=code2.id),
        ]
        
        exporter = WorkflowExporter(workflow)
        code = exporter.export()
        
        compile(code, "<string>", "exec")
        
        assert "node_outputs" in code

    def test_get_execution_order_no_edges(self):
        """Test _get_execution_order with no edges."""
        workflow = Workflow.create(name="No Edges Flow")
        
        node1 = Node.create(node_type="start", position=Position(x=100, y=100))
        node2 = Node.create(node_type="python_code", position=Position(x=300, y=100))
        
        workflow.nodes = [node1, node2]
        workflow.edges = []
        
        exporter = WorkflowExporter(workflow)
        order = exporter._get_execution_order()
        
        assert len(order) == 2

    def test_get_execution_order_with_edges(self):
        """Test _get_execution_order with edges."""
        workflow = Workflow.create(name="With Edges Flow")
        
        node1 = Node.create(node_type="start", position=Position(x=100, y=100))
        node2 = Node.create(node_type="python_code", position=Position(x=300, y=100))
        node3 = Node.create(node_type="end", position=Position(x=500, y=100))
        
        workflow.nodes = [node1, node2, node3]
        workflow.edges = [
            Edge.create(source=node1.id, target=node2.id),
            Edge.create(source=node2.id, target=node3.id),
        ]
        
        exporter = WorkflowExporter(workflow)
        order = exporter._get_execution_order()
        order_ids = [n.id for n in order]
        
        assert order_ids.index(node1.id) < order_ids.index(node2.id)
        assert order_ids.index(node2.id) < order_ids.index(node3.id)

    def test_generate_inputs_code(self):
        """Test _generate_inputs_code method."""
        workflow = Workflow.create(name="Inputs Test")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100)
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100)
        )
        
        workflow.nodes = [start, code]
        workflow.edges = [
            Edge.create(source=start.id, target=code.id),
        ]
        
        exporter = WorkflowExporter(workflow)
        
        execution_order = [start, code]
        inputs_code = exporter._generate_inputs_code(code, execution_order)
        
        assert start.id in inputs_code

    def test_full_export_executable(self):
        """Test that exported code is complete and can be compiled."""
        workflow = Workflow.create(name="Executable Flow")
        
        start = Node.create(
            node_type="start",
            position=Position(x=100, y=100),
            config=NodeConfig(params={"a": 10, "b": 20})
        )
        
        code = Node.create(
            node_type="python_code",
            position=Position(x=300, y=100),
            config=NodeConfig(code="""
total = a + b
product = a * b
result = {"sum": total, "product": product}
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
        
        exporter = WorkflowExporter(workflow)
        exported_code = exporter.export()
        
        local_vars = {}
        exec(exported_code, local_vars)
        
        assert "run_workflow" in local_vars


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
