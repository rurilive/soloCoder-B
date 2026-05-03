from typing import Any, Dict, List, Set, Optional
from collections import deque
from enum import Enum

from .models import Workflow, Node, Edge
from .nodes import NodeRegistry, BaseNode


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    
    @classmethod
    def from_string(cls, level_str: str) -> 'LogLevel':
        level_map = {
            'DEBUG': cls.DEBUG,
            'INFO': cls.INFO,
            'WARNING': cls.WARNING,
            'ERROR': cls.ERROR,
        }
        return level_map.get(level_str.upper(), cls.INFO)


class WorkflowRunner:
    def __init__(self, workflow: Workflow, sandbox: Optional[Any] = None, log_level: LogLevel = LogLevel.INFO):
        self.workflow = workflow
        self.sandbox = sandbox
        self.log_level = log_level
        self.node_outputs: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
        try:
            self.log(f"Starting workflow: {self.workflow.name}", LogLevel.INFO)
            
            execution_order = self._topological_sort()
            self.log(f"Execution order: {[n.id for n in execution_order]}", LogLevel.DEBUG)
            
            for node_model in execution_order:
                self._execute_node(node_model)
            
            final_result = self.context.get("__final_result__")
            if final_result is None:
                end_nodes = [n for n in self.workflow.nodes if n.type == "end"]
                if end_nodes:
                    end_node_id = end_nodes[0].id
                    final_result = self.node_outputs.get(end_node_id)
            
            self.log("Workflow execution completed successfully", LogLevel.INFO)
            
            return {
                "status": "success",
                "result": final_result,
                "logs": self.logs,
                "node_outputs": {k: str(v) for k, v in self.node_outputs.items()}
            }
            
        except Exception as e:
            self.log(f"Error: {str(e)}", LogLevel.ERROR)
            import traceback
            self.log(traceback.format_exc(), LogLevel.ERROR)
            
            return {
                "status": "error",
                "error": str(e),
                "logs": self.logs,
                "node_outputs": {k: str(v) for k, v in self.node_outputs.items()}
            }

    def _topological_sort(self) -> List[Node]:
        nodes = self.workflow.nodes
        edges = self.workflow.edges
        
        node_map = {node.id: node for node in nodes}
        
        in_degree: Dict[str, int] = {node.id: 0 for node in nodes}
        adjacency: Dict[str, List[str]] = {node.id: [] for node in nodes}
        
        for edge in edges:
            source = edge.source
            target = edge.target
            if source in adjacency and target in in_degree:
                adjacency[source].append(target)
                in_degree[target] += 1
        
        queue = deque()
        for node_id, degree in in_degree.items():
            if degree == 0:
                queue.append(node_id)
        
        execution_order: List[str] = []
        
        while queue:
            node_id = queue.popleft()
            execution_order.append(node_id)
            
            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(execution_order) != len(nodes):
            raise RuntimeError("Workflow contains a cycle (not a valid DAG)")
        
        return [node_map[node_id] for node_id in execution_order]

    def _execute_node(self, node_model: Node) -> None:
        node = NodeRegistry.create_node(node_model)
        if node is None:
            self.log(f"Warning: Unknown node type '{node_model.type}', skipping", LogLevel.WARNING)
            return
        
        self.log(f"Executing node: {node_model.id} (type: {node_model.type})", LogLevel.INFO)
        
        inputs = self._resolve_inputs(node_model)
        self.log(f"  Inputs: {inputs}", LogLevel.DEBUG)
        
        try:
            from .nodes import PythonCodeNode
            
            if isinstance(node, PythonCodeNode) and self.sandbox and hasattr(self.sandbox, 'execute'):
                output = self.sandbox.execute(node, inputs, self.context)
            else:
                output = node.execute(inputs, self.context)
            
            self.node_outputs[node_model.id] = output
            self.log(f"  Output: {output}", LogLevel.DEBUG)
            
        except Exception as e:
            self.log(f"  Error executing node {node_model.id}: {str(e)}", LogLevel.ERROR)
            raise

    def _resolve_inputs(self, node_model: Node) -> Dict[str, Any]:
        inputs: Dict[str, Any] = {}
        
        incoming_edges = [
            e for e in self.workflow.edges if e.target == node_model.id
        ]
        
        for edge in incoming_edges:
            source_id = edge.source
            source_output = self.node_outputs.get(source_id, {})
            source_handle = edge.source_handle
            
            handled = False
            
            if source_handle == "output-true":
                if isinstance(source_output, dict) and "true" in source_output:
                    true_value = source_output.get("true")
                    if isinstance(true_value, dict):
                        inputs.update(true_value)
                    elif true_value is not None:
                        inputs["result"] = true_value
                    
                    if isinstance(source_output, dict) and "_inputs" in source_output:
                        original_inputs = source_output.get("_inputs", {})
                        for key, value in original_inputs.items():
                            if key not in inputs:
                                inputs[key] = value
                    
                    handled = True
            
            elif source_handle == "output-false":
                if isinstance(source_output, dict) and "false" in source_output:
                    false_value = source_output.get("false")
                    if isinstance(false_value, dict):
                        inputs.update(false_value)
                    elif false_value is not None:
                        inputs["result"] = false_value
                    
                    if isinstance(source_output, dict) and "_inputs" in source_output:
                        original_inputs = source_output.get("_inputs", {})
                        for key, value in original_inputs.items():
                            if key not in inputs:
                                inputs[key] = value
                    
                    handled = True
            
            if not handled:
                if isinstance(source_output, dict):
                    if "params" in source_output and len(source_output) == 1:
                        params = source_output["params"]
                        if isinstance(params, dict):
                            inputs.update(params)
                    else:
                        inputs.update(source_output)
                elif source_output is not None:
                    inputs["result"] = source_output
        
        config_inputs = node_model.config.inputs
        for key, value in config_inputs.items():
            if key not in inputs:
                resolved_value = self._resolve_placeholders(value)
                inputs[key] = resolved_value
        
        return inputs

    def _resolve_placeholders(self, value: Any) -> Any:
        if isinstance(value, str):
            import re
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            if not matches:
                return value
            
            result = value
            for match in matches:
                replacement = self._get_nested_value(match)
                
                if replacement is not None:
                    placeholder = f"${{{match}}}"
                    if value == placeholder:
                        return replacement
                    result = result.replace(placeholder, str(replacement))
            
            return result
        
        elif isinstance(value, dict):
            return {k: self._resolve_placeholders(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._resolve_placeholders(item) for item in value]
        
        return value

    def _get_nested_value(self, path: str) -> Any:
        parts = path.split('.')
        if not parts:
            return None
        
        node_id = parts[0]
        node_output = self.node_outputs.get(node_id)
        
        if node_output is None:
            return None
        
        if len(parts) == 1:
            return node_output
        
        current = node_output
        for key in parts[1:]:
            if isinstance(current, dict):
                if key in current:
                    current = current[key]
                else:
                    return None
            elif isinstance(current, (list, tuple)):
                try:
                    idx = int(key)
                    current = current[idx]
                except (ValueError, IndexError):
                    return None
            else:
                if hasattr(current, key):
                    current = getattr(current, key)
                else:
                    return None
        
        return current

    def log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        log_entry = {
            "level": level.name,
            "message": message,
            "timestamp": self._get_timestamp()
        }
        self.logs.append(log_entry)
        print(f"[Runner] [{level.name}] {message}")
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
