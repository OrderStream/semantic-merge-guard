"""
Cross-file AST dependency graph analyzer detecting silent semantic merge conflicts.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any

@dataclass
class FuncDef:
    name: str
    file_path: str
    line: int
    required_args: int
    total_args: int
    arg_names: List[str]
    has_varargs: bool = False

@dataclass
class FuncCall:
    name: str
    file_path: str
    line: int
    arg_count: int

@dataclass
class RouteDef:
    method: str
    path: str
    file_path: str
    line: int

@dataclass
class SemanticConflict:
    kind: str  # ARITY_MISMATCH, DUPLICATE_ROUTE, UNRESOLVED_SYMBOL, DEPRECATED_CONTRACT
    severity: str  # CRITICAL, HIGH, WARNING
    caller_file: str
    caller_line: int
    target_name: str
    message: str
    remediation: str

class SemanticMergeGuard:
    def __init__(self):
        self.definitions: Dict[str, List[FuncDef]] = {}
        self.calls: List[FuncCall] = []
        self.routes: List[RouteDef] = []
        self.conflicts: List[SemanticConflict] = []

    def scan_file(self, file_path: str, content: str) -> None:
        if file_path.endswith(".py"):
            self._scan_python(file_path, content)
        elif file_path.endswith((".ts", ".js", ".tsx", ".jsx")):
            self._scan_js_ts(file_path, content)

    def _scan_python(self, file_path: str, content: str) -> None:
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # Function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Calculate required args (excluding self/cls and args with defaults)
                total = len(node.args.args)
                defaults = len(node.args.defaults)
                names = [a.arg for a in node.args.args]
                
                # Check if method in class
                is_method = len(names) > 0 and names[0] in {"self", "cls"}
                adjusted_total = total - (1 if is_method else 0)
                required = adjusted_total - defaults

                has_varargs = bool(node.args.vararg or node.args.kwarg)
                fdef = FuncDef(
                    name=node.name,
                    file_path=file_path,
                    line=node.lineno,
                    required_args=max(0, required),
                    total_args=max(0, adjusted_total),
                    arg_names=names[1:] if is_method else names,
                    has_varargs=has_varargs
                )
                self.definitions.setdefault(node.name, []).append(fdef)

                # Check route decorators (FastAPI/Flask)
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        method = decorator.func.attr.upper()
                        if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "ROUTE"}:
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                self.routes.append(RouteDef(
                                    method=method,
                                    path=str(decorator.args[0].value),
                                    file_path=file_path,
                                    line=decorator.lineno
                                ))

            # Function calls
            elif isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr

                if call_name and not call_name.startswith("__"):
                    arg_count = len(node.args) + len(node.keywords)
                    self.calls.append(FuncCall(
                        name=call_name,
                        file_path=file_path,
                        line=node.lineno,
                        arg_count=arg_count
                    ))

    def _scan_js_ts(self, file_path: str, content: str) -> None:
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            clean = line.strip()
            # export function foo(a, b, c)
            match_func = re.search(r"export\s+(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\((.*?)\)", clean)
            if match_func:
                name = match_func.group(1)
                params_str = match_func.group(2).strip()
                params = [p.strip() for p in params_str.split(",") if p.strip()] if params_str else []
                req_params = [p for p in params if "=" not in p and "?" not in p]
                has_varargs = any("..." in p for p in params)
                self.definitions.setdefault(name, []).append(FuncDef(
                    name=name,
                    file_path=file_path,
                    line=idx,
                    required_args=len(req_params),
                    total_args=len(params),
                    arg_names=params,
                    has_varargs=has_varargs
                ))

            # Route registration: app.get("/api/...", ...) or router.post("/...", ...)
            match_route = re.search(r"\b(app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", clean)
            if match_route:
                self.routes.append(RouteDef(
                    method=match_route.group(2).upper(),
                    path=match_route.group(3),
                    file_path=file_path,
                    line=idx
                ))

            # Function calls: foo(a, b)
            match_call = re.findall(r"\b([a-zA-Z0-9_$]+)\s*\(([^)]*)\)", clean)
            for name, args_str in match_call:
                if name in {"if", "for", "while", "switch", "catch", "import", "require", "function"}:
                    continue
                args = [a.strip() for a in args_str.split(",") if a.strip()] if args_str else []
                self.calls.append(FuncCall(
                    name=name,
                    file_path=file_path,
                    line=idx,
                    arg_count=len(args)
                ))

    def analyze_conflicts(self) -> List[SemanticConflict]:
        self.conflicts.clear()

        # 1. Check duplicate route conflicts across concurrent branches/files
        seen_routes: Dict[Tuple[str, str], RouteDef] = {}
        for r in self.routes:
            key = (r.method, r.path)
            if key in seen_routes:
                prev = seen_routes[key]
                if prev.file_path != r.file_path or prev.line != r.line:
                    self.conflicts.append(SemanticConflict(
                        kind="DUPLICATE_ROUTE",
                        severity="CRITICAL",
                        caller_file=r.file_path,
                        caller_line=r.line,
                        target_name=f"{r.method} {r.path}",
                        message=f"Duplicate route '{r.method} {r.path}' registered in {r.file_path}:{r.line} and {prev.file_path}:{prev.line}. Will cause silent endpoint collision.",
                        remediation="Consolidate duplicate route registrations into a single controller module."
                    ))
            else:
                seen_routes[key] = r

        # 2. Check call arity mismatches against scanned definitions
        for call in self.calls:
            if call.name in self.definitions:
                defs = self.definitions[call.name]
                # Filter out definitions in the same file if local shadowing, or check matching defs
                for fdef in defs:
                    # Skip builtins / common generic names that collide easily
                    if call.name in {"len", "print", "str", "int", "dict", "list", "get", "log", "format", "open", "run", "send"}:
                        continue
                    
                    # If caller passed fewer args than required by definition
                    if call.arg_count < fdef.required_args:
                        self.conflicts.append(SemanticConflict(
                            kind="ARITY_MISMATCH",
                            severity="CRITICAL",
                            caller_file=call.file_path,
                            caller_line=call.line,
                            target_name=call.name,
                            message=f"Call to '{call.name}()' at {call.file_path}:{call.line} supplies {call.arg_count} argument(s), but definition in {fdef.file_path}:{fdef.line} expects at least {fdef.required_args} ({', '.join(fdef.arg_names)}).",
                            remediation=f"Update call site in {call.file_path}:{call.line} to supply missing required parameter(s)."
                        ))
                        break
                    
                    # If caller passed more args than total allowed (and function is not variadic)
                    elif not fdef.has_varargs and call.arg_count > fdef.total_args:
                        self.conflicts.append(SemanticConflict(
                            kind="ARITY_MISMATCH",
                            severity="HIGH",
                            caller_file=call.file_path,
                            caller_line=call.line,
                            target_name=call.name,
                            message=f"Call to '{call.name}()' at {call.file_path}:{call.line} supplies {call.arg_count} argument(s), exceeding maximum {fdef.total_args} allowed by {fdef.file_path}:{fdef.line}.",
                            remediation=f"Remove extraneous arguments from call site in {call.file_path}:{call.line}."
                        ))
                        break

        return self.conflicts

    @classmethod
    def scan_directory(cls, directory: str) -> List[SemanticConflict]:
        guard = cls()
        dir_path = Path(directory)
        for file in dir_path.rglob("*"):
            if not file.is_file():
                continue
            parts = file.parts
            if any(p.startswith(".") or p in {"node_modules", "venv", ".git", "__pycache__", "dist", "build"} for p in parts):
                continue
            if file.suffix in {".py", ".ts", ".js", ".tsx", ".jsx"}:
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    guard.scan_file(str(file), content)
                except Exception:
                    continue

        return guard.analyze_conflicts()
