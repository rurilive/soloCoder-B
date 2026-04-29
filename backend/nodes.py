from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from .models import Node, NodeConfig


class BaseNode(ABC):
    node_type: str = "base"
    label: str = "Base Node"
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}

    def __init__(self, node_model: Node):
        self.model = node_model
        self.config = node_model.config

    @classmethod
    def get_default_config(cls) -> NodeConfig:
        return NodeConfig()

    @abstractmethod
    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def get_input_definition(self) -> Dict[str, Any]:
        return self.input_schema.copy()

    def get_output_definition(self) -> Dict[str, Any]:
        return self.output_schema.copy()


class StartNode(BaseNode):
    node_type: str = "start"
    label: str = "Start"
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {
        "params": {"type": "object", "description": "Initial workflow parameters"}
    }

    @classmethod
    def get_default_config(cls) -> NodeConfig:
        return NodeConfig(
            params={},
            outputs={"params": {}}
        )

    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        params = self.config.params.copy()
        return {"params": params}


class EndNode(BaseNode):
    node_type: str = "end"
    label: str = "End"
    input_schema: Dict[str, Any] = {
        "result": {"type": "any", "description": "Final workflow result"}
    }
    output_schema: Dict[str, Any] = {}

    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        result = inputs.get("result", inputs)
        context["__final_result__"] = result
        return {}


class PythonCodeNode(BaseNode):
    node_type: str = "python_code"
    label: str = "Python Code"
    input_schema: Dict[str, Any] = {
        "*": {"type": "any", "description": "Dynamic inputs from connections"}
    }
    output_schema: Dict[str, Any] = {
        "result": {"type": "any", "description": "Code execution result"}
    }

    @classmethod
    def get_default_config(cls) -> NodeConfig:
        return NodeConfig(
            code="# Write your Python code here\n# Input variables are available as local variables\n# Assign to 'result' variable or use return statement\n\nname = 'World'\nresult = f'Hello {name}'\n",
            inputs={},
            outputs={}
        )

    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        code = self.config.code.strip()
        
        if not code:
            return {"result": None}
        
        local_vars = inputs.copy()
        local_vars["context"] = context
        local_vars["result"] = None
        
        try:
            exec_globals = {"__builtins__": __builtins__}
            
            processed_code = self._process_code(code)
            compiled = compile(processed_code, "<string>", "exec")
            exec(compiled, exec_globals, local_vars)
            
            result = local_vars.get("result")
            return {"result": result}
        except Exception as e:
            raise RuntimeError(f"Code execution error: {str(e)}") from e

    def _process_code(self, code: str) -> str:
        if not self._contains_return_statement(code):
            return code
        
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('return '):
                indent = line[:len(line) - len(stripped)]
                expr = stripped[7:]
                processed_lines.append(f'{indent}result = {expr}')
            elif stripped == 'return':
                indent = line[:len(line) - len(stripped)]
                processed_lines.append(f'{indent}result = None')
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)

    def _contains_return_statement(self, code: str) -> bool:
        import tokenize
        import io
        
        try:
            tokens = tokenize.generate_tokens(io.StringIO(code).readline)
            for tok in tokens:
                tok_type, tok_string, _, _, _ = tok
                if tok_type == tokenize.NAME and tok_string == "return":
                    return True
        except:
            pass
        
        return False


class ConditionNode(BaseNode):
    node_type: str = "condition"
    label: str = "Condition"
    input_schema: Dict[str, Any] = {
        "value": {"type": "any", "description": "Value to evaluate"}
    }
    output_schema: Dict[str, Any] = {
        "true": {"type": "any", "description": "Output if condition is true"},
        "false": {"type": "any", "description": "Output if condition is false"}
    }
    
    SAFE_BUILTINS = {
        'abs': abs,
        'bool': bool,
        'dict': dict,
        'float': float,
        'int': int,
        'len': len,
        'list': list,
        'max': max,
        'min': min,
        'range': range,
        'reversed': reversed,
        'round': round,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'True': True,
        'False': False,
        'None': None,
    }

    @classmethod
    def get_default_config(cls) -> NodeConfig:
        return NodeConfig(
            params={
                "expression": "value > 10",
                "true_value": {"result": "Value is greater than 10"},
                "false_value": {"result": "Value is 10 or less"}
            }
        )

    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        value = inputs.get("value")
        expression = self.config.params.get("expression", "value is not None")
        
        local_vars = {"value": value}
        local_vars.update(inputs)
        
        safe_globals = {"__builtins__": self.SAFE_BUILTINS}
        
        try:
            condition_result = eval(expression, safe_globals, local_vars)
        except Exception as e:
            raise RuntimeError(f"Condition evaluation error: {str(e)}") from e
        
        true_value = self.config.params.get("true_value", value)
        false_value = self.config.params.get("false_value", None)
        
        if condition_result:
            return {"true": true_value, "false": None, "condition": True}
        else:
            return {"true": None, "false": false_value, "condition": False}


class NodeRegistry:
    _registry: Dict[str, Type[BaseNode]] = {}

    @classmethod
    def register(cls, node_class: Type[BaseNode]) -> None:
        cls._registry[node_class.node_type] = node_class

    @classmethod
    def get(cls, node_type: str) -> Optional[Type[BaseNode]]:
        return cls._registry.get(node_type)

    @classmethod
    def get_all(cls) -> List[Type[BaseNode]]:
        return list(cls._registry.values())

    @classmethod
    def get_node_types(cls) -> List[Dict[str, Any]]:
        return [
            {
                "type": nc.node_type,
                "label": nc.label,
                "input_schema": nc.input_schema,
                "output_schema": nc.output_schema,
            }
            for nc in cls._registry.values()
        ]

    @classmethod
    def create_node(cls, node_model: Node) -> Optional[BaseNode]:
        node_class = cls.get(node_model.type)
        if node_class:
            return node_class(node_model)
        return None


NodeRegistry.register(StartNode)
NodeRegistry.register(EndNode)
NodeRegistry.register(PythonCodeNode)
NodeRegistry.register(ConditionNode)
