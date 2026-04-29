import sys
import io
import traceback
from typing import Any, Dict, Optional, Tuple

try:
    from RestrictedPython import compile_restricted_exec
    from RestrictedPython.Guards import safe_builtins, full_write_guard
    from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
    HAS_RESTRICTED_PYTHON = True
except ImportError:
    HAS_RESTRICTED_PYTHON = False


class CodeSandbox:
    def __init__(self):
        self.logs: list = []

    def log(self, message: str) -> None:
        self.logs.append(message)
        print(f"[Sandbox] {message}")

    def execute(
        self,
        node: Any,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        code = node.config.code.strip() if hasattr(node, 'config') else ""
        
        if not code:
            return {"result": None}
        
        code = self._process_code(code)
        
        local_vars = inputs.copy()
        local_vars["context"] = context
        local_vars["result"] = None
        
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        
        try:
            sys.stdout = stdout_capture
            
            if HAS_RESTRICTED_PYTHON:
                result = self._execute_restricted(code, local_vars)
            else:
                self.log("Warning: RestrictedPython not installed, running without sandbox")
                result = self._execute_unrestricted(code, local_vars)
            
            stdout_output = stdout_capture.getvalue()
            if stdout_output:
                for line in stdout_output.strip().split('\n'):
                    if line:
                        self.log(f"[stdout] {line}")
            
            return {"result": result}
            
        except Exception as e:
            self.log(f"Execution error: {str(e)}")
            self.log(traceback.format_exc())
            raise RuntimeError(f"Code execution error: {str(e)}") from e
            
        finally:
            sys.stdout = old_stdout

    def _process_code(self, code: str) -> str:
        import tokenize
        import io
        
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        except:
            return code
        
        has_return = any(
            tok[0] == tokenize.NAME and tok[1] == "return"
            for tok in tokens
        )
        
        if not has_return:
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

    def _execute_restricted(self, code: str, local_vars: Dict[str, Any]) -> Any:
        self.log("Executing in restricted mode (RestrictedPython)")
        
        try:
            safe_globals = self._get_safe_globals()
            
            compiled = compile(code, "<string>", "exec")
            exec(compiled, safe_globals, local_vars)
            
            return local_vars.get("result")
            
        except SyntaxError as e:
            self.log(f"Syntax error: {e}")
            raise
        except Exception as e:
            self.log(f"Error in execution: {e}")
            raise

    def _execute_unrestricted(self, code: str, local_vars: Dict[str, Any]) -> Any:
        exec_globals = {"__builtins__": __builtins__}
        compiled = compile(code, "<string>", "exec")
        exec(compiled, exec_globals, local_vars)
        return local_vars.get("result")

    def _get_safe_globals(self) -> Dict[str, Any]:
        if not HAS_RESTRICTED_PYTHON:
            return {"__builtins__": __builtins__}
        
        def _getattr_(obj, name):
            if isinstance(obj, (str, int, float, bool, type(None), list, dict, tuple)):
                if name.startswith('_'):
                    raise AttributeError(f"Cannot access private attribute: {name}")
            return getattr(obj, name)
        
        def _setattr_(obj, name, value):
            if isinstance(obj, (dict, list, tuple, str, int, float, bool, type(None))):
                raise TypeError(f"Cannot set attribute on {type(obj)}")
            if name.startswith('_'):
                raise AttributeError(f"Cannot set private attribute: {name}")
            return setattr(obj, name, value)
        
        def _getitem_(obj, index):
            return default_guarded_getitem(obj, index)
        
        def _getiter_(obj):
            return default_guarded_getiter(obj)
        
        def _write_(obj):
            return full_write_guard(obj)
        
        def safe_import(name, *args, **kwargs):
            allowed_modules = ['math', 'random', 'statistics', 'json', 'copy', 'collections', 'datetime', 'time']
            if name in allowed_modules:
                return __import__(name, *args, **kwargs)
            raise ImportError(f"Import of '{name}' is not allowed in sandbox")
        
        safe_builtins_dict = {
            'abs': abs,
            'all': all,
            'any': any,
            'bool': bool,
            'chr': chr,
            'dict': dict,
            'divmod': divmod,
            'enumerate': enumerate,
            'filter': filter,
            'float': float,
            'format': format,
            'frozenset': frozenset,
            'hex': hex,
            'int': int,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'iter': iter,
            'len': len,
            'list': list,
            'map': map,
            'max': max,
            'min': min,
            'next': next,
            'oct': oct,
            'ord': ord,
            'pow': pow,
            'print': print,
            'range': range,
            'repr': repr,
            'reversed': reversed,
            'round': round,
            'set': set,
            'sorted': sorted,
            'str': str,
            'sum': sum,
            'tuple': tuple,
            'type': type,
            'zip': zip,
            'True': True,
            'False': False,
            'None': None,
            '__import__': safe_import,
        }
        
        import math
        safe_builtins_dict['math'] = math
        
        safe_globals = {
            "__builtins__": safe_builtins_dict,
            "_getattr_": _getattr_,
            "_setattr_": _setattr_,
            "_write_": _write_,
            "_getitem_": _getitem_,
            "_getiter_": _getiter_,
        }
        
        return safe_globals


class SandboxResult:
    def __init__(self):
        self.success: bool = False
        self.result: Any = None
        self.error: Optional[str] = None
        self.logs: list = []
        self.stdout: str = ""
        self.stderr: str = ""
