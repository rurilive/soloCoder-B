#!/usr/bin/env python3
"""
Test script to reproduce the issue with condition nodes and type errors
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.runner import WorkflowRunner
from backend.nodes import NodeRegistry, StartNode, ConditionNode, PythonCodeNode, EndNode
from backend.sandbox import CodeSandbox


def create_test_workflow():
    """
    Test: Start -> Condition -> PythonCode -> End
    
    This test simulates the issue described in the bug report:
    - Start node sets value = 11 (integer)
    - Condition node checks value > 10 (should be True)
    - PythonCode node tries to concatenate string with value
    """
    workflow = Workflow.create("Test Condition Type Issue")
    
    start_node = Node(
        id="start-1",
        type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(
            params={"value": 11},
            outputs={}
        ),
        label="Start"
    )
    
    condition_node = Node(
        id="condition-1",
        type="condition",
        position=Position(x=300, y=100),
        config=NodeConfig(
            params={
                "expression": "value > 10",
                "true_value": {"message": "Value is greater than 10", "status": "high"},
                "false_value": {"message": "Value is 10 or less", "status": "low"}
            }
        ),
        label="Condition"
    )
    
    # This PythonCode node tries to concatenate string with value (which is integer)
    # This should fail with "can only concatenate str (not 'int') to str"
    code_node = Node(
        id="code-1",
        type="python_code",
        position=Position(x=500, y=100),
        config=NodeConfig(
            code="""
# Try to concatenate message with value
# This will fail if value is integer
result = message + " - Status: " + status
""",
            inputs={},
            outputs={}
        ),
        label="Python Code"
    )
    
    end_node = Node(
        id="end-1",
        type="end",
        position=Position(x=700, y=100),
        config=NodeConfig(),
        label="End"
    )
    
    workflow.nodes = [start_node, condition_node, code_node, end_node]
    workflow.edges = [
        Edge(id="e1", source="start-1", target="condition-1", source_handle="output", target_handle="input"),
        Edge(id="e2", source="condition-1", target="code-1", source_handle="output-true", target_handle="input"),
        Edge(id="e3", source="code-1", target="end-1", source_handle="output", target_handle="input"),
    ]
    
    return workflow


def test_placeholder_resolution():
    """
    Test the _resolve_placeholders function behavior
    
    Issue: When the entire value is a placeholder like ${value},
    it returns the original type (e.g., integer). But when the placeholder
    is part of a string, it converts to string. This inconsistency can cause issues.
    """
    print("\n" + "=" * 60)
    print("Test: Placeholder Resolution Behavior")
    print("=" * 60)
    
    from backend.runner import WorkflowRunner
    from backend.models import Workflow, Node, Edge, Position, NodeConfig
    
    # Create a simple workflow to test placeholder resolution
    workflow = Workflow.create("Test Placeholders")
    
    start_node = Node(
        id="start-1",
        type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(
            params={"value": 11},
            outputs={}
        ),
        label="Start"
    )
    
    # This node uses config.inputs with placeholders
    code_node = Node(
        id="code-1",
        type="python_code",
        position=Position(x=300, y=100),
        config=NodeConfig(
            code="""
# Check types of inputs
print(f"value type: {type(value)}")
print(f"my_value type: {type(my_value)}")
print(f"my_string type: {type(my_string)}")
result = f"value={value}, my_value={my_value}, my_string={my_string}"
""",
            inputs={
                "my_value": "${start-1.value}",  # Entire value is placeholder
                "my_string": "Value is ${start-1.value}"  # Placeholder is part of string
            },
            outputs={}
        ),
        label="Python Code"
    )
    
    workflow.nodes = [start_node, code_node]
    workflow.edges = [
        Edge(id="e1", source="start-1", target="code-1", source_handle="output", target_handle="input"),
    ]
    
    runner = WorkflowRunner(workflow, CodeSandbox())
    
    # Manually test _resolve_placeholders
    print("\nTesting _resolve_placeholders manually:")
    
    # Simulate the state after start node executes
    runner.node_outputs["start-1"] = {"params": {"value": 11}}
    
    # Test case 1: entire value is placeholder
    test_value_1 = "${start-1.params.value}"
    result_1 = runner._resolve_placeholders(test_value_1)
    print(f"  Input: '{test_value_1}'")
    print(f"  Result: {result_1} (type: {type(result_1).__name__})")
    
    # Test case 2: placeholder is part of string
    test_value_2 = "Value is ${start-1.params.value}"
    result_2 = runner._resolve_placeholders(test_value_2)
    print(f"  Input: '{test_value_2}'")
    print(f"  Result: {result_2} (type: {type(result_2).__name__})")
    
    # Check for type inconsistency
    if type(result_1) != type(result_2):
        print("\n  ⚠️  TYPE INCONSISTENCY DETECTED!")
        print(f"    When entire value is placeholder: returns {type(result_1).__name__}")
        print(f"    When placeholder is part of string: returns {type(result_2).__name__}")
        return False
    else:
        print("\n  ✓ Types are consistent")
        return True


def test_condition_inputs_passed_to_next_node():
    """
    Test that condition node's _inputs are properly passed to next node
    and check for type issues
    """
    print("\n" + "=" * 60)
    print("Test: Condition Node Inputs Passed to Next Node")
    print("=" * 60)
    
    workflow = create_test_workflow()
    runner = WorkflowRunner(workflow, CodeSandbox())
    result = runner.run()
    
    print(f"Status: {result['status']}")
    print(f"Result: {result.get('result')}")
    print(f"Error: {result.get('error')}")
    print(f"Node Outputs: {result.get('node_outputs', {})}")
    
    if result['status'] == 'success':
        print("✓ Test passed")
        return True
    else:
        print(f"✗ Test failed: {result.get('error')}")
        print(f"Logs: {result.get('logs', [])}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Condition Node Type Issue Test Suite")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Placeholder resolution behavior
    all_passed = test_placeholder_resolution() and all_passed
    
    # Test 2: Condition node with PythonCode that concatenates strings
    all_passed = test_condition_inputs_passed_to_next_node() and all_passed
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)
