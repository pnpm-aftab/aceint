from __future__ import annotations

import ast
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional


def extract_expected_outputs(content: str) -> list[str]:
    """Extract expected outputs from problem content HTML."""
    outputs = []
    # Match patterns like "Output: [0,1]" or "<strong>Output:</strong> [0,1]"
    # Clean HTML tags first
    text = re.sub(r"<[^>]+>", " ", content)
    # Match Output: followed by value until newline or next Example/Constraint
    pattern = re.compile(r"Output:\s*(.*?)(?:\s*Explanation|Example|Constraints|$)", re.DOTALL)
    for match in pattern.finditer(text):
        val = match.group(1).strip()
        if val:
            # Try to extract just the first line/block of output
            val = val.split("\n")[0].strip()
            outputs.append(val)
    return outputs


def parse_test_cases(test_cases_str: str, arg_count: int) -> list[list[str]]:
    """Parse test cases from string into groups of arguments."""
    if not test_cases_str:
        return []
    lines = [l.strip() for l in test_cases_str.split("\n") if l.strip()]
    if not lines:
        return []

    # If we have arg_count, group lines
    results = []
    for i in range(0, len(lines), arg_count):
        results.append(lines[i : i + arg_count])
    return results


def get_python3_starter(problem: dict) -> str:
    snippets = problem.get("code_snippets") or []
    starter = next((s.get("code", "") for s in snippets if s.get("lang") == "python3"), "")
    if not starter:
        starter = next((s.get("code", "") for s in snippets if s.get("lang") == "python"), "")
    return starter


def make_compilable_starter(code: str) -> str:
    """Ensure starter code parses even when dataset snippet omits method body."""
    candidate = (code or "").rstrip() + "\n"
    if "List[" in candidate and "from typing import List" not in candidate:
        candidate = "from typing import List\n\n" + candidate
    try:
        ast.parse(candidate)
        return candidate
    except SyntaxError:
        # Many dataset snippets end at a function signature line.
        lines = [line.rstrip("\n") for line in candidate.splitlines()]
        last_non_empty = ""
        for line in reversed(lines):
            if line.strip():
                last_non_empty = line
                break

        indent = "        "
        if last_non_empty:
            leading = len(last_non_empty) - len(last_non_empty.lstrip(" "))
            indent = " " * (leading + 4)

        fixed = candidate + f"{indent}pass\n"
        # If this still fails, return original so user can see untouched starter.
        try:
            ast.parse(fixed)
            return fixed
        except SyntaxError:
            return candidate


def get_arg_count(starter_code: str) -> int:
    """Parse starter code to find the number of arguments in the primary method."""
    compilable = make_compilable_starter(starter_code)
    try:
        tree = ast.parse(compilable)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("__"):
                # Count arguments excluding 'self'
                args = [arg for arg in node.args.args if arg.arg != "self"]
                return len(args)
    except Exception:
        pass
    return 1


class ListNode:
    def __init__(self, val: int = 0, next: Optional[ListNode] = None):
        self.val = val
        self.next = next

    def __repr__(self) -> str:
        vals = []
        curr = self
        while curr:
            vals.append(str(curr.val))
            curr = curr.next
        return f"[{','.join(vals)}]"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ListNode):
            return False
        return str(self) == str(other)


def list_to_list_node(values: List[int]) -> Optional[ListNode]:
    if not values:
        return None
    head = ListNode(values[0])
    curr = head
    for val in values[1:]:
        curr.next = ListNode(val)
        curr = curr.next
    return head


class TreeNode:
    def __init__(
        self,
        val: int = 0,
        left: Optional[TreeNode] = None,
        right: Optional[TreeNode] = None,
    ):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        # Simple BFS representation for comparison
        result = []
        queue = [self]
        while queue:
            node = queue.pop(0)
            if node:
                result.append(str(node.val))
                queue.append(node.left)
                queue.append(node.right)
            else:
                result.append("null")
        # Trim trailing nulls
        while result and result[-1] == "null":
            result.pop()
        return f"[{','.join(result)}]"


def to_env_list_node(values: List[int], node_class: Any) -> Any:
    if not values:
        return None
    head = node_class(values[0])
    curr = head
    for val in values[1:]:
        curr.next = node_class(val)
        curr = curr.next
    return head


def to_env_tree_node(values: List[Optional[int]], node_class: Any) -> Any:
    if not values or values[0] is None:
        return None
    root = node_class(values[0])
    queue = [root]
    i = 1
    while queue and i < len(values):
        node = queue.pop(0)
        if i < len(values) and values[i] is not None:
            node.left = node_class(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = node_class(values[i])
            queue.append(node.right)
        i += 1
    return root


def list_node_to_list(node: Any) -> List[int]:
    result = []
    curr = node
    while curr:
        result.append(curr.val)
        curr = curr.next
    return result


def tree_node_to_list(node: Any) -> List[Optional[int]]:
    if not node:
        return []
    result = []
    queue = [node]
    while queue:
        curr = queue.pop(0)
        if curr:
            result.append(curr.val)
            queue.append(curr.left)
            queue.append(curr.right)
        else:
            result.append(None)
    while result and result[-1] is None:
        result.pop()
    return result


def execute_code(
    code: str,
    test_input: Any,
    class_name: str = "Solution",
    function_name: str | None = None,
) -> Any:
    """Execute code against test input."""
    # Setup environment
    import typing

    safe_globals = {
        "ListNode": ListNode,
        "TreeNode": TreeNode,
        "Optional": typing.Optional,
        "List": typing.List,
        "Dict": typing.Dict,
        "Set": typing.Set,
        "Tuple": typing.Tuple,
        "Any": typing.Any,
        "Union": typing.Union,
        "defaultdict": defaultdict,
        "__builtins__": __builtins__,
    }

    # Execute solution code
    exec(code, safe_globals)

    if class_name not in safe_globals:
        raise ValueError(f"Class {class_name} not found in code")

    sol_class = safe_globals[class_name]
    instance = sol_class()

    # Parse input
    if isinstance(test_input, str):
        try:
            # Try to parse single string input (might be a tuple of args)
            parsed = ast.literal_eval(test_input)
            if isinstance(parsed, tuple):
                args = list(parsed)
            else:
                args = [parsed]
        except (ValueError, SyntaxError):
            # Fallback to string if not a valid literal
            args = [test_input]
    elif isinstance(test_input, (list, tuple)):
        # Already grouped arguments
        args = []
        for inp in test_input:
            if isinstance(inp, str):
                try:
                    # Try to parse each string argument
                    # Handle LeetCode-specific booleans
                    if inp.lower() == "true":
                        args.append(True)
                    elif inp.lower() == "false":
                        args.append(False)
                    elif inp.lower() == "null":
                        args.append(None)
                    else:
                        args.append(ast.literal_eval(inp))
                except (ValueError, SyntaxError):
                    args.append(inp)
            else:
                args.append(inp)
    else:
        args = [test_input]

    # Find the function to call
    if function_name and hasattr(instance, function_name):
        func = getattr(instance, function_name)
    else:
        # Find first public method
        for name in dir(instance):
            if not name.startswith("_"):
                attr = getattr(instance, name)
                if callable(attr):
                    func = attr
                    function_name = name
                    break
        else:
            raise ValueError(f"No public method found in {class_name}")

    # Convert args based on type hints if possible
    import typing
    try:
        # Use get_type_hints on the method
        hints = typing.get_type_hints(func, globalns=safe_globals)
        
        # Get the classes from safe_globals to match redefined classes in code
        env_list_node = safe_globals.get("ListNode", ListNode)
        env_tree_node = safe_globals.get("TreeNode", TreeNode)

        # Get parameter names from the function signature
        import inspect
        sig = inspect.signature(func)
        
        converted_args = []
        param_items = list(sig.parameters.items())
        # Filter out 'self' if present in sig
        if param_items and param_items[0][0] == 'self':
            param_items = param_items[1:]

        for i, (param_name, param) in enumerate(param_items):
            if i >= len(args):
                break
            
            arg_val = args[i]
            hint = hints.get(param_name, Any)
            
            # Handle Optional[T] or T | None
            origin = typing.get_origin(hint)
            if origin is typing.Union or (hasattr(typing, "UnionType") and origin is typing.UnionType):
                # Extract the non-None type
                args_types = typing.get_args(hint)
                hint = next((t for t in args_types if t is not type(None)), Any)

            # Conversion based on hint
            # We check if hint is our ListNode OR the one from the environment
            if (hint is ListNode or hint is env_list_node) and isinstance(arg_val, list):
                # We need to use the constructor of the class that the function expects
                # But our list_to_list_node uses our ListNode. 
                # Let's make a more generic converter.
                converted_args.append(to_env_list_node(arg_val, env_list_node))
            elif (hint is TreeNode or hint is env_tree_node) and isinstance(arg_val, list):
                converted_args.append(to_env_tree_node(arg_val, env_tree_node))
            else:
                converted_args.append(arg_val)
        
        args = converted_args
    except Exception as e:
        # Fallback to original args if hints fail
        pass

    # Call the function
    result = func(*args)

    # Convert results back to serializable types if they are ListNode/TreeNode
    # Use __class__.__name__ to be more resilient to redefined classes
    if result.__class__.__name__ == "ListNode":
        return list_node_to_list(result)
    if result.__class__.__name__ == "TreeNode":
        return tree_node_to_list(result)

    return result


def compare_results(actual: Any, expected: Any) -> bool:
    """Compare actual result with expected result with smart matching."""
    if actual == expected:
        return True

    # Handle numeric comparisons (e.g., float precision)
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(actual - expected) < 1e-5

    # Handle lists
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False
        
        # Try exact order comparison first
        if all(compare_results(a, e) for a, e in zip(actual, expected)):
            return True
            
        # Try sorted comparison (for problems where order doesn't matter)
        try:
            # Only if they are simple lists (not nested)
            if all(not isinstance(x, (list, dict)) for x in actual):
                return sorted(actual) == sorted(expected)
        except (TypeError, ValueError):
            pass

        # Handle list of lists (e.g., group anagrams) - compare as sets of sorted lists
        try:
            if all(isinstance(x, list) for x in actual) and all(isinstance(x, list) for x in expected):
                actual_sorted = [sorted(a) for a in actual]
                expected_sorted = [sorted(e) for e in expected]
                actual_sorted.sort()
                expected_sorted.sort()
                if actual_sorted == expected_sorted:
                    return True
        except (TypeError, ValueError):
            pass

    return False
