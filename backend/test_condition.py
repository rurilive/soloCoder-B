#!/usr/bin/env python3
"""
Test script for Condition Node functionality

Test cases:
1. Start -> Condition -> End (direct value from Start)
2. Start -> PythonCode -> Condition -> End (value passed through code)
3. Complex condition expressions
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Workflow, Node, Edge, Position, NodeConfig
from backend.runner import WorkflowRunner
from backend.nodes import NodeRegistry, StartNode, ConditionNode, PythonCodeNode, EndNode
from backend.sandbox import CodeSandbox


def create_test_workflow_1():
    """Test: Start -> Condition -> End"""
    workflow = Workflow.create("Test Condition Workflow 1")
    
    start_node = Node(
        id="start-1",
        type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(
            params={"value": 15},
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
                "true_value": {"result": "Value is greater than 10"},
                "false_value": {"result": "Value is 10 or less"}
            }
        ),
        label="Condition"
    )
    
    end_node = Node(
        id="end-1",
        type="end",
        position=Position(x=500, y=100),
        config=NodeConfig(),
        label="End"
    )
    
    workflow.nodes = [start_node, condition_node, end_node]
    workflow.edges = [
        Edge(id="e1", source="start-1", target="condition-1", source_handle="output", target_handle="input"),
        Edge(id="e2", source="condition-1", target="end-1", source_handle="output", target_handle="input"),
    ]
    
    return workflow


def create_test_workflow_2():
    """Test: Start -> PythonCode -> Condition -> End"""
    workflow = Workflow.create("Test Condition Workflow 2")
    
    start_node = Node(
        id="start-1",
        type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(
            params={"input_value": 25},
            outputs={}
        ),
        label="Start"
    )
    
    code_node = Node(
        id="code-1",
        type="python_code",
        position=Position(x=300, y=100),
        config=NodeConfig(
            code="""
# Double the input value
result = input_value * 2
""",
            inputs={},
            outputs={}
        ),
        label="Python Code"
    )
    
    condition_node = Node(
        id="condition-1",
        type="condition",
        position=Position(x=500, y=100),
        config=NodeConfig(
            params={
                "expression": "result > 30",
                "true_value": {"result": "Result is greater than 30"},
                "false_value": {"result": "Result is 30 or less"}
            }
        ),
        label="Condition"
    )
    
    end_node = Node(
        id="end-1",
        type="end",
        position=Position(x=700, y=100),
        config=NodeConfig(),
        label="End"
    )
    
    workflow.nodes = [start_node, code_node, condition_node, end_node]
    workflow.edges = [
        Edge(id="e1", source="start-1", target="code-1", source_handle="output", target_handle="input"),
        Edge(id="e2", source="code-1", target="condition-1", source_handle="output", target_handle="input"),
        Edge(id="e3", source="condition-1", target="end-1", source_handle="output", target_handle="input"),
    ]
    
    return workflow


def create_test_workflow_3():
    """Test: Complex condition expressions"""
    workflow = Workflow.create("Test Condition Workflow 3")
    
    start_node = Node(
        id="start-1",
        type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(
            params={
                "name": "Alice",
                "age": 25,
                "score": 85,
                "items": [1, 2, 3]
            },
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
                "expression": "age >= 18 and score >= 80 and len(items) > 0",
                "true_value": {"result": "All conditions passed"},
                "false_value": {"result": "Some conditions failed"}
            }
        ),
        label="Condition"
    )
    
    end_node = Node(
        id="end-1",
        type="end",
        position=Position(x=500, y=100),
        config=NodeConfig(),
        label="End"
    )
    
    workflow.nodes = [start_node, condition_node, end_node]
    workflow.edges = [
        Edge(id="e1", source="start-1", target="condition-1", source_handle="output", target_handle="input"),
        Edge(id="e2", source="condition-1", target="end-1", source_handle="output", target_handle="input"),
    ]
    
    return workflow


def test_condition_node_direct():
    """Test 1: Start -> Condition -> End"""
    print("=" * 60)
    print("Test 1: Start -> Condition -> End (value=15, condition=value > 10)")
    print("=" * 60)
    
    workflow = create_test_workflow_1()
    runner = WorkflowRunner(workflow, CodeSandbox())
    result = runner.run()
    
    print(f"Status: {result['status']}")
    print(f"Result: {result['result']}")
    print(f"Node Outputs: {result.get('node_outputs', {})}")
    
    if result['status'] == 'success':
        condition_output = runner.node_outputs.get('condition-1')
        print(f"Condition Output: {condition_output}")
        
        # value=15 > 10 should be True
        assert condition_output.get('condition') == True, f"Expected True, got {condition_output.get('condition')}"
        assert condition_output.get('true') == {"result": "Value is greater than 10"}
        print("✓ Test 1 PASSED")
        return True
    else:
        print(f"✗ Test 1 FAILED: {result.get('error')}")
        print(f"Logs: {result.get('logs', [])}")
        return False


def test_condition_node_with_code():
    """Test 2: Start -> PythonCode -> Condition -> End"""
    print("\n" + "=" * 60)
    print("Test 2: Start -> PythonCode -> Condition -> End")
    print("  Start input_value=25, Code doubles to 50, Condition: result > 30")
    print("=" * 60)
    
    workflow = create_test_workflow_2()
    runner = WorkflowRunner(workflow, CodeSandbox())
    result = runner.run()
    
    print(f"Status: {result['status']}")
    print(f"Result: {result['result']}")
    print(f"Node Outputs: {result.get('node_outputs', {})}")
    
    if result['status'] == 'success':
        code_output = runner.node_outputs.get('code-1')
        condition_output = runner.node_outputs.get('condition-1')
        
        print(f"Code Output: {code_output}")
        print(f"Condition Output: {condition_output}")
        
        # 25 * 2 = 50 > 30 should be True
        assert code_output.get('result') == 50, f"Expected 50, got {code_output.get('result')}"
        assert condition_output.get('condition') == True, f"Expected True, got {condition_output.get('condition')}"
        print("✓ Test 2 PASSED")
        return True
    else:
        print(f"✗ Test 2 FAILED: {result.get('error')}")
        print(f"Logs: {result.get('logs', [])}")
        return False


def test_condition_complex():
    """Test 3: Complex condition expressions"""
    print("\n" + "=" * 60)
    print("Test 3: Complex condition expressions")
    print("  Expression: age >= 18 and score >= 80 and len(items) > 0")
    print("  Values: age=25, score=85, items=[1,2,3]")
    print("=" * 60)
    
    workflow = create_test_workflow_3()
    runner = WorkflowRunner(workflow, CodeSandbox())
    result = runner.run()
    
    print(f"Status: {result['status']}")
    print(f"Result: {result['result']}")
    print(f"Node Outputs: {result.get('node_outputs', {})}")
    
    if result['status'] == 'success':
        condition_output = runner.node_outputs.get('condition-1')
        print(f"Condition Output: {condition_output}")
        
        # All conditions should be True
        assert condition_output.get('condition') == True, f"Expected True, got {condition_output.get('condition')}"
        print("✓ Test 3 PASSED")
        return True
    else:
        print(f"✗ Test 3 FAILED: {result.get('error')}")
        print(f"Logs: {result.get('logs', [])}")
        return False


def test_condition_false_case():
    """Test 4: Condition that should be False"""
    print("\n" + "=" * 60)
    print("Test 4: Condition that should be False")
    print("  Start value=5, Condition: value > 10")
    print("=" * 60)
    
    workflow = Workflow.create("Test Condition False")
    
    start_node = Node(
        id="start-1",
        type="start",
        position=Position(x=100, y=100),
        config=NodeConfig(
            params={"value": 5},
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
                "true_value": {"result": "Greater"},
                "false_value": {"result": "Not Greater"}
            }
        ),
        label="Condition"
    )
    
    workflow.nodes = [start_node, condition_node]
    workflow.edges = [
        Edge(id="e1", source="start-1", target="condition-1", source_handle="output", target_handle="input"),
    ]
    
    runner = WorkflowRunner(workflow, CodeSandbox())
    result = runner.run()
    
    print(f"Status: {result['status']}")
    
    if result['status'] == 'success':
        condition_output = runner.node_outputs.get('condition-1')
        print(f"Condition Output: {condition_output}")
        
        # value=5 > 10 should be False
        assert condition_output.get('condition') == False, f"Expected False, got {condition_output.get('condition')}"
        assert condition_output.get('false') == {"result": "Not Greater"}
        print("✓ Test 4 PASSED")
        return True
    else:
        print(f"✗ Test 4 FAILED: {result.get('error')}")
        print(f"Logs: {result.get('logs', [])}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Condition Node Test Suite")
    print("=" * 60)
    
    all_passed = True
    
    all_passed = test_condition_node_direct() and all_passed
    all_passed = test_condition_node_with_code() and all_passed
    all_passed = test_condition_complex() and all_passed
    all_passed = test_condition_false_case() and all_passed
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)
