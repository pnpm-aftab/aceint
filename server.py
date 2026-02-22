"""LeetCode Helper - Pure Python HTTP server."""
import http.server
import html
import json
import os
import socketserver
import sys
import threading
import urllib.parse
import mimetypes
import ast
import requests
from pathlib import Path
from leetcode_helper.runner import execute_code, get_arg_count, make_compilable_starter, get_python3_starter, parse_test_cases, extract_expected_outputs, compare_results
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
AURORA_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")


# Configuration
PORT = 8888
DATA_DIR = Path("data")
STATIC_DIR = Path("static")
SOLUTIONS_DIR = Path("solutions")


# Load data at module level for sharing across requests
def load_problems_index():
    """Load the lightweight problems index."""
    index_file = DATA_DIR / "problems_index.json"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_full_problem(problem_id, cache):
    """Load a single problem from the full problems.json."""
    if problem_id in cache:
        return cache[problem_id]

    problems_file = DATA_DIR / "problems.json"
    if not problems_file.exists():
        return None

    with open(problems_file, "r", encoding="utf-8") as f:
        problems = json.load(f)

    for p in problems:
        pid = str(p.get("id") or p.get("frontend_id"))
        cache[pid] = p

    return cache.get(problem_id)


def load_progress():
    """Load user progress from file."""
    progress_file = DATA_DIR / "progress.json"
    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    # New structure: {"solved": {"problem_id": {"code": "...", "timestamp": "...", "passed": True}}}
    return {"solved": {}, "submissions": {}, "roadmap": {"currentDay": 1, "currentPhase": 1, "completedDays": [], "unlockedPhases": [1]}}


def save_progress(progress):
    """Save user progress to file."""
    progress_file = DATA_DIR / "progress.json"
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


# Shared data
problems_index = load_problems_index()
problems_cache = {}
progress = load_progress()


class LeetCodeHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP handler for LeetCode Helper."""

    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_file(self, filepath):
        """Send a static file."""
        if not filepath.exists():
            self.send_error(404, "File not found")
            return

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(filepath))
        if content_type is None:
            content_type = "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()

        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urllib.parse.urlparse(self.path)

        # API routes
        if parsed.path == "/api/problems":
            self.get_problems(parsed)
        elif parsed.path.startswith("/api/problem/"):
            problem_id = parsed.path.split("/")[-1]
            self.get_problem(problem_id)
        elif parsed.path == "/api/progress":
            self.send_json(progress)
        elif parsed.path == "/api/roadmap/progress":
            self.get_roadmap_progress()
        elif parsed.path == "/" or parsed.path == "/index.html":
            self.send_file(STATIC_DIR / "index.html")
        elif parsed.path.startswith("/static/"):
            # Strip /static/ prefix
            static_path = parsed.path[8:]
            self.send_file(STATIC_DIR / static_path)
        elif parsed.path.endswith(".css"):
            self.send_file(STATIC_DIR / parsed.path.lstrip("/"))
        elif parsed.path.endswith(".js"):
            self.send_file(STATIC_DIR / parsed.path.lstrip("/"))
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/ai/solution":
            self.get_ai_solution()
        elif parsed.path == "/api/ai/explain":
            self.get_ai_explanation()
        elif parsed.path == "/api/hints":
            self.get_hint()
        elif parsed.path == "/api/run":
            self.run_code()
        elif parsed.path == "/api/progress":
            self.update_progress()
        elif parsed.path == "/api/roadmap/progress":
            self.update_roadmap_progress()
        else:
            self.send_error(404, "Not Found")

    def get_problems(self, parsed):
        """Get list of problems with optional filters."""
        # Parse query params
        params = urllib.parse.parse_qs(parsed.query)
        difficulty = params.get("difficulty", [None])[0]
        search = params.get("search", [None])[0]
        status_filter = params.get("status", [None])[0]  # "solved" or "unsolved"
        tag = params.get("tag", [None])[0]

        problems = problems_index.copy()
        solved_dict = progress.get("solved", {})

        # Apply filters
        filtered = []
        for p in problems:
            # Difficulty filter
            if difficulty and p.get("difficulty") != difficulty:
                continue

            # Status filter
            pid = str(p.get("id") or p.get("frontend_id"))
            is_solved = pid in solved_dict
            if status_filter == "solved" and not is_solved:
                continue
            if status_filter == "unsolved" and is_solved:
                continue

            # Tag filter
            if tag and tag not in p.get("topic_tags", []):
                continue

            # Search filter
            if search:
                search_lower = search.lower()
                title = p.get("title", "").lower()
                tags = " ".join(p.get("topic_tags", [])).lower()
                if search_lower not in title and search_lower not in tags:
                    continue

            # Add solved status
            p_with_status = p.copy()
            p_with_status["solved"] = is_solved
            filtered.append(p_with_status)

        self.send_json(filtered)

    def get_problem(self, problem_id):
        """Get full problem details."""
        problem = load_full_problem(problem_id, problems_cache)
        if not problem:
            self.send_json({"error": "Problem not found"}, 404)
            return

        # Add solved status
        pid = str(problem.get("id") or problem.get("frontend_id"))
        problem["solved"] = pid in progress.get("solved", {})

        self.send_json(problem)

    def run_code(self):
        """Execute Python code against test cases."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_json({"error": "No content"}, 400)
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        code = data.get("code", "")
        problem_id = str(data.get("problem_id", ""))
        class_name = data.get("class_name", "Solution")
        function_name = data.get("function_name") # Will be auto-detected if None

        if not code:
            self.send_json({"error": "No code provided"}, 400)
            return

        # Fetch problem details to get proper test cases and argument count
        problem = load_full_problem(problem_id, problems_cache)
        if problem:
            starter = get_python3_starter(problem)
            arg_count = get_arg_count(starter)
            test_cases = parse_test_cases(problem.get("example_test_cases", ""), arg_count)
            expected_outputs = extract_expected_outputs(problem.get("content", ""))
        else:
            # Fallback to provided data if problem not found in cache
            test_cases = data.get("test_cases", [])
            expected_outputs = data.get("expected_outputs", [])

        results = []
        for i, test_input in enumerate(test_cases):
            expected = expected_outputs[i] if i < len(expected_outputs) else None
            result = self.execute_test(code, test_input, i, class_name, function_name, expected)
            results.append(result)

        passed = sum(1 for r in results if r["passed"])
        self.send_json({
            "results": results,
            "passed": passed,
            "total": len(results),
        })


    def execute_test(self, code, test_input, index, class_name, function_name, expected_output=None):
        """Execute a single test case using the new runner."""
        try:
            # The test_input from the web might be a list of inputs already
            actual = execute_code(code, test_input, class_name, function_name)
            
            # Compare output with expected
            if expected_output:
                try:
                    # Clean the expected output string (it often comes from problem description)
                    # Decode HTML entities (e.g., &quot; -> ") and parse it
                    decoded_output = html.unescape(expected_output.strip())
                    expected_val = ast.literal_eval(decoded_output)
                except:
                    # Fallback for booleans
                    if expected_output.strip().lower() == "true":
                        expected_val = True
                    elif expected_output.strip().lower() == "false":
                        expected_val = False
                    elif expected_output.strip().lower() == "null":
                        expected_val = None
                    else:
                        expected_val = expected_output
                
                passed = compare_results(actual, expected_val)
                
                return {
                    "passed": passed,
                    "input": str(test_input),
                    "actual": str(actual),
                    "expected": str(expected_val),
                }
            else:
                return {
                    "passed": True,
                    "input": str(test_input),
                    "actual": str(actual),
                }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "passed": False,
                "error": str(e),
                "test_input": str(test_input),
            }

    def _build_ai_messages(self, conversation_history, problem_title, problem_description, starter_code, current_code, test_results, test_cases, mode="chat", hint_level=1, question=None):
        """Build unified AI messages for all interactions.
        
        Args:
            mode: 'solution', 'chat', or 'hint'
            hint_level: hint level for hint mode
            question: optional direct question for chat mode
        """
        context_blocks = []
        
        if problem_title:
            context_blocks.append(f"Problem: {problem_title}")
        
        if problem_description:
            context_blocks.append(f"Description: {problem_description[:3000]}")
        
        if mode != "solution" and mode != "chat" and starter_code:
            context_blocks.append(f"Starter Code:\n```python\n{starter_code}\n```")
        
        if current_code:
            context_blocks.append(f"Current Code in Editor:\n```python\n{current_code}\n```")
        
        if test_results:
            passed_count = test_results.get("passed", 0)
            total_count = test_results.get("total", 0)
            
            test_guidance = ""
            if total_count > 0:
                if passed_count == 0:
                    test_guidance = "No tests pass - focus on fixing the core logic/algorithm."
                elif passed_count < total_count:
                    test_guidance = f"Some tests fail ({total_count - passed_count}/{total_count}) - focus on edge cases or specific test failures."
                else:
                    test_guidance = "All tests pass - you can suggest optimizations or alternative approaches."
            
            context_blocks.append(f"Test Results: {passed_count}/{total_count} tests passed")
            context_blocks.append(f"Guidance: {test_guidance}")
            
            if test_results.get("results"):
                failed_cases = [r for r in test_results["results"] if not r.get("passed", True)]
                if failed_cases:
                    context_blocks.append("\nFailed Test Cases:")
                    for i, case in enumerate(failed_cases[:2], 1):
                        context_blocks.append(f"  Case {i}:")
                        context_blocks.append(f"    Input: {case.get('input', '')[:100]}")
                        context_blocks.append(f"    Expected: {case.get('expected', '')[:100]}")
                        context_blocks.append(f"    Actual: {case.get('actual', '')[:100]}")
        
        if test_cases and mode != "chat":
            # Format test cases for context
            test_cases_str = ""
            for tc in test_cases[:3]:
                if isinstance(tc, list):
                    test_cases_str += f"Input: {tc}\n"
                elif isinstance(tc, dict):
                    input_val = tc.get('input', '')
                    output_val = tc.get('output', '')
                    test_cases_str += f"Input: {input_val}"
                    if output_val:
                        test_cases_str += f" Output: {output_val}"
                    test_cases_str += "\n"
                elif isinstance(tc, str):
                    test_cases_str += f"Input: {tc}\n"
            context_blocks.append(f"Test Cases:\n{test_cases_str}")
        
        context_str = "\n\n".join(context_blocks)
        
        # Build prompt based on mode
        if mode == "solution":
            prompt = f"""You are a helpful Python coding tutor helping with LeetCode-style problems. 
{context_str}

Task:
1. Start with a clean, basic solution that's easy to understand.
2. Keep it simple first - optimize later if user asks.
3. Briefly explain the core idea (2-3 sentences max).
4. Provide Python 3 code with minimal comments - let the code speak for itself.
5. State time and space complexity.
6. Show a quick dry run with 1-2 examples if the algorithm isn't obvious.

Guidelines:
- Prioritize readability and clarity over clever tricks.
- Use simple loops and data structures first.
- Add comments only for non-obvious parts.
- Assume the user wants to learn from a working solution, not get the most optimized answer immediately.
- If tests fail, focus on fixing the bug, not optimization.
- Consider common edge cases: empty inputs, single elements, duplicates, boundary values.
- Use idiomatic Python when appropriate (list comprehensions, enumerate, etc.).

Response Format:
- Use clean Markdown.
- Keep explanations short and practical.
- Show a working example (dry run) if helpful.
"""
        elif mode == "hint":
            hint_guidance_map = {
                1: "Show a basic structure: imports, class definition, method signature, and main data structures. Leave the core logic as a simple TODO comment.",
                2: "Show the main loop or recursion structure. Fill in key data structures. Leave only the tricky comparison or calculation as TODO.",
                3: "Show a nearly complete solution. Leave only 1-2 lines blank (the key insight or edge case handling). Add brief comments where helpful, not everywhere."
            }
            
            prompt = f"""You are a helpful Python tutor. Provide progressive code hints to guide the user to a working solution.

{context_str}

Generate Hint Level {hint_level}:
{hint_guidance_map.get(hint_level, "")}

Rules:
1. Output only Python code, no explanations or markdown code fences.
2. Use TODO comments or simple comments to show what's missing - don't use ??? which breaks syntax.
3. Keep code syntactically valid - use pass or return "" for missing parts.
4. Add comments sparingly - only for key insights, not everywhere.
5. Make the hint build on previous hints if they exist.
6. Consider edge cases in your hints: empty inputs, single elements, duplicates, boundary values.
7. If user code exists and fails tests, help them fix the specific issue rather than starting over.

Example format for TODO:
    # TODO: implement core logic here
    or
    # HINT: check if value already exists

Output only the Python code (no ```python``` wrapper)."""
        else:  # chat mode
            if not question and conversation_history:
                question = conversation_history[-1].get("text", "")
            
            if not question:
                raise ValueError("Question required in chat mode")
            
            prompt = f"""You are a helpful Python tutor helping a user with a coding problem.

{context_str}

User Question: {question}

Task:
- Answer the question directly and helpfully.
- Adjust your response style based on what they're asking:
  * "Why does this fail?" → Analyze the bug, show what's wrong, suggest fix
  * "Help me start" → Suggest approach, show skeleton, explain first steps
  * "Explain this code" → Walk through line by line, show what each part does
  * "Can you optimize this?" → Suggest improvements, show before/after comparison
  * General question → Give clear explanation, keep it concise but complete
- If showing code, keep it short and relevant (5-10 lines max unless demonstrating full solution).
- If the algorithm is complex, show a quick dry run with 1-2 examples.
- Use Markdown for formatting.

Guidelines:
- Be direct and practical, not mysterious or overly "nudgey".
- If the user's code is failing, identify the specific issue clearly.
- If all tests pass, suggest optimizations or edge cases to consider.
- If no tests pass, start with basics - don't optimize broken code.
- Adjust depth based on conversation length: shorter answers early, more detailed if they keep asking.
- When discussing algorithms, mention edge cases: empty, single element, duplicates, boundaries.
- If test guidance mentions "no tests pass", focus on fundamental logic errors.
- If test guidance mentions "some tests fail", analyze the specific failing cases.
- If test guidance mentions "all tests pass", you can suggest alternatives or optimizations.

Response Format:
- Use clean Markdown.
"""
        
        return [{"role": "user", "content": prompt}]

    def get_ai_solution(self):
        """Generate AI solution - unified with chat system."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_json({"error": "No content"}, 400)
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        problem_title = data.get("problem_title", "")
        problem_description = data.get("problem_description", "")
        test_cases = data.get("test_cases", [])
        starter_code = data.get("starter_code", "")
        current_code = data.get("current_code", "")

        if not problem_title:
            self.send_json({"error": "Problem title required"}, 400)
            return

        # Build context for initial solution request
        problem_id = str(data.get("problem_id", ""))
        
        # Add conversation context if exists
        conversation_history = data.get("conversation_history", [])
        test_results = data.get("test_results", None)
        
        # Build unified chat message list with context
        messages = self._build_ai_messages(
            conversation_history=conversation_history,
            problem_title=problem_title,
            problem_description=problem_description,
            starter_code=starter_code,
            current_code=current_code,
            test_results=test_results,
            test_cases=test_cases,
            mode="solution"
        )

        # Log what we're sending
        print(f"[AI UNIFIED] Mode=solution, Problem={problem_title}")

        try:
            if not OPENROUTER_API_KEY:
                self.send_json({"error": "OpenRouter API key not configured"}, 500)
                return

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8888",
                    "X-Title": "LeetCode Helper"
                },
                json={
                    "model": AURORA_MODEL,
                    "messages": messages,
                    "max_tokens": 3500,
                },
                timeout=60
            )

            if response.status_code != 200:
                self.send_json({
                    "error": f"AI request failed: {response.status_code}",
                    "details": response.text
                }, 500)
                return

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Log solution for debugging
            print(f"[AI SOLUTION] Content type: {type(content).__name__}, Content preview: {content[:200]}")

            if not content:
                self.send_json({"error": "Empty response from AI"}, 500)
                return

            self.send_json({"solution": content.strip()})

        except requests.exceptions.Timeout:
            self.send_json({"error": "Request timed out. Please try again."}, 504)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def get_ai_explanation(self):
        """Explain a piece of code or answer a syntax question using AI - unified with chat system."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_json({"error": "No content"}, 400)
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        question = data.get("question", "")
        code_snippet = data.get("code_snippet", "")
        problem_title = data.get("problem_title", "")
        current_code = data.get("current_code", "")
        conversation_history = data.get("conversation_history", [])
        test_results = data.get("test_results", None)

        if not question:
            self.send_json({"error": "Question required"}, 400)
            return

        # Build unified messages using the new system
        messages = self._build_ai_messages(
            conversation_history=conversation_history,
            problem_title=problem_title,
            problem_description="",  # Chat doesn't need full problem description
            starter_code="",
            current_code=current_code,
            test_results=test_results,
            test_cases=[],
            mode="chat",
            question=question
        )

        # Log what we're sending
        print(f"[AI EXPLAIN] Mode=chat")

        try:
            if not OPENROUTER_API_KEY:
                self.send_json({"error": "OpenRouter API key not configured"}, 500)
                return

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8888",
                    "X-Title": "LeetCode Helper"
                },
                json={
                    "model": AURORA_MODEL,
                    "messages": messages,
                    "max_tokens": 1500,
                },
                timeout=45
            )

            if response.status_code != 200:
                self.send_json({"error": f"AI request failed: {response.status_code}"}, 500)
                return

            result = response.json()
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Log the answer type and content for debugging
            print(f"[CHAT] Answer type: {type(answer).__name__}, Answer value: {answer[:200] if answer else 'None'}")

            if not answer:
                self.send_json({"error": "Empty response from AI"}, 500)
                return

            self.send_json({"answer": answer.strip()})

        except requests.exceptions.Timeout:
            self.send_json({"error": "Request timed out. Please try again."}, 504)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def get_ai_explanation_stream(self):
        """Stream AI responses - unified with chat system."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_json({"error": "No content"}, 400)
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        question = data.get("question", "")
        code_snippet = data.get("code_snippet", "")
        problem_title = data.get("problem_title", "")
        current_code = data.get("current_code", "")
        conversation_history = data.get("conversation_history", [])
        test_results = data.get("test_results", None)

        if not question:
            self.send_json({"error": "Question required"}, 400)
            return

        # Build unified messages using the new system
        messages = self._build_ai_messages(
            conversation_history=conversation_history,
            problem_title=problem_title,
            problem_description="",  # Chat doesn't need full problem description
            starter_code="",
            current_code=current_code,
            test_results=test_results,
            test_cases=[],
            mode="chat",
            question=question
        )

        # Log what we're sending
        print(f"[AI EXPLAIN STREAM] Mode=chat")

        try:
            if not OPENROUTER_API_KEY:
                self.send_json({"error": "OpenRouter API key not configured"}, 500)
                return

            # Set up SSE streaming
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8888",
                    "X-Title": "LeetCode Helper"
                },
                json={
                    "model": AURORA_MODEL,
                    "messages": messages,
                    "max_tokens": 1500,
                    "stream": True,
                },
                timeout=60,
                stream=True
            )

            if response.status_code != 200:
                self.wfile.write(b"data: " + json.dumps({"error": f"AI request failed: {response.status_code}"}).encode() + b"\n\n")
                return

            # Stream the response
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                # Only send if content is a non-empty string
                                if content and isinstance(content, str) and content.strip():
                                    print(f"[STREAM] Sending content: {content[:100]}... (type: {type(content).__name__})")
                                    self.wfile.write(b"data: " + json.dumps({"content": content}).encode() + b"\n\n")
                                    self.wfile.flush()
                        except json.JSONDecodeError:
                            continue

            # Send done signal
            self.wfile.write(b"data: [DONE]\n\n")

        except requests.exceptions.Timeout:
            self.wfile.write(b"data: " + json.dumps({"error": "Request timed out. Please try again."}).encode() + b"\n\n")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.wfile.write(b"data: " + json.dumps({"error": str(e)}).encode() + b"\n\n")

    def get_hint(self):
        """Generate progressive hint - unified with chat system."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_json({"error": "No content"}, 400)
                return

            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
            except json.JSONDecodeError as e:
                self.send_json({"error": f"Invalid JSON: {str(e)}"}, 400)
                return

            problem_id = data.get("problem_id")
            hint_level = int(data.get("hint_level", 1))
            regenerate = data.get("regenerate", False)
            problem_title = data.get("problem_title", "")
            problem_description = data.get("problem_description", "")
            starter_code = data.get("starter_code", "")
            current_code = data.get("current_code", "")

            if not problem_id:
                self.send_json({"error": "Problem ID required"}, 400)
                return

            global progress
            progress.setdefault("hints", {})
            
            problem_id = str(problem_id)
            hint_data = progress["hints"].get(problem_id, {"hints": [], "revealed": 0})
            
            needs_generation = regenerate or not hint_data["hints"] or len(hint_data["hints"]) < hint_level
            
            if needs_generation and hint_level <= 3:
                # Build unified messages using the new system
                messages = self._build_ai_messages(
                    conversation_history=[],  # Hints don't need conversation history
                    problem_title=problem_title,
                    problem_description=problem_description,
                    starter_code=starter_code,
                    current_code=current_code,
                    test_results=None,  # Hints don't include test results
                    test_cases=[],
                    mode="hint",
                    hint_level=hint_level
                )

                # Log what we're sending
                print(f"[HINT] Mode=hint, Level={hint_level}, Messages={len(messages)}")

                if not OPENROUTER_API_KEY:
                    self.send_json({"error": "OpenRouter API key not configured"}, 500)
                    return

                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:8888",
                        "X-Title": "LeetCode Helper"
                    },
                    json={
                        "model": AURORA_MODEL,
                        "messages": messages,
                        "max_tokens": 1000,
                    },
                    timeout=60
                )

                if response.status_code != 200:
                    self.send_json({
                        "error": f"AI request failed: {response.status_code}",
                        "details": response.text[:500]
                    }, 500)
                    return

                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not content:
                    print(f"Empty AI response for hint level {hint_level}, problem {problem_id}")
                    self.send_json({"error": "AI returned empty response. Please try again."}, 500)
                    return

                content = content.strip()
                print(f"[HINT] Hint level {hint_level} content type: {type(content).__name__}, content preview: {content[:150]}")
                
                while len(hint_data["hints"]) < hint_level:
                    hint_data["hints"].append("")
                hint_data["hints"][hint_level - 1] = content
                
                progress["hints"][problem_id] = hint_data
                save_progress(progress)

                self.send_json({
                    "hint": content,
                    "hint_level": hint_level,
                    "total_hints": 3,
                    "is_new": True
                })

            else:
                if hint_data["hints"] and len(hint_data["hints"]) >= hint_level:
                    self.send_json({
                        "hint": hint_data["hints"][hint_level - 1],
                        "hint_level": hint_level,
                        "total_hints": 3,
                        "is_new": False
                    })
                else:
                    self.send_json({"error": "Hint not available"}, 404)

        except requests.exceptions.Timeout:
            self.send_json({"error": "Request timed out. Please try again."}, 504)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_json({"error": f"Server error: {str(e)}"}, 500)

    def build_hint_prompt(self, problem_title, problem_description, starter_code, hint_level, previous_hints, current_code):
        """Build a prompt to generate code hints that can be inserted into editor."""
        
        hint_guidance = {
            1: "Show the basic structure: imports, class definition, method signature, and main data structures. Leave the core logic as a simple TODO comment.",
            2: "Show the main loop or recursion structure. Fill in key data structures. Leave only the tricky comparison or calculation as TODO.",
            3: "Show a nearly complete solution. Leave only 1-2 lines blank (the key insight or edge case handling). Add brief comments where helpful, not everywhere."
        }
        
        user_code_context = ""
        if current_code and current_code.strip() != starter_code.strip():
            user_code_context = f"\n\nUser's current attempt:\n```python\n{current_code}\n```\nNotice where they might be stuck and help from there."
        
        previous_hints_text = ""
        if previous_hints:
            previous_hints_text = "\n\nPrevious hints (don't repeat):\n" + "\n".join([f"- {h[:200]}" for i, h in enumerate(previous_hints) if h])
        
        prompt = f"""You are a helpful Python tutor. Provide progressive code hints to guide the user to a working solution.

Problem: {problem_title}
Description: {problem_description}
Starter code (preserve exact signature):
```python
{starter_code}
```
{user_code_context}
{previous_hints_text}

Generate Hint Level {hint_level}:
{hint_guidance[hint_level]}

Rules:
1. Output only Python code, no explanations or markdown code fences.
2. Use TODO comments or simple comments to show what's missing - don't use ??? which breaks syntax.
3. Keep code syntactically valid - use pass or return "" for missing parts.
4. Add comments sparingly - only for key insights, not everywhere.
5. Make the hint build on previous hints if they exist.
6. Consider edge cases in your hints: empty inputs, single elements, duplicates, boundary values.
7. If user code exists and fails tests, help them fix the specific issue rather than starting over.

Example format for TODO:
    # TODO: implement core logic here
    or
    # HINT: check if value already exists

Output only the Python code (no ```python``` wrapper)."""
        
        return prompt

    def update_progress(self):
        """Update user progress."""
        global progress

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_json({"error": "No content"}, 400)
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        action = data.get("action")
        problem_id = data.get("problem_id")

        if action == "mark_solved":
            code = data.get("code", "")
            if problem_id:
                progress.setdefault("solved", {})[problem_id] = {
                    "code": code,
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "passed": True
                }
                save_progress(progress)
            self.send_json({"success": True, "progress": progress})

        elif action == "mark_unsolved":
            if problem_id and problem_id in progress.get("solved", {}):
                del progress["solved"][problem_id]
                save_progress(progress)
            self.send_json({"success": True, "progress": progress})

        elif action == "save_code":
            # Auto-save code without changing solved status
            code = data.get("code", "")
            if problem_id:
                # Only save if problem is already solved or has previous saved code
                if problem_id in progress.get("solved", {}):
                    progress["solved"][problem_id]["code"] = code
                    progress["solved"][problem_id]["timestamp"] = __import__("datetime").datetime.now().isoformat()
                    save_progress(progress)
            self.send_json({"success": True, "progress": progress})

        elif action == "save_submission":
            code = data.get("code")
            passed = data.get("passed", False)

            if problem_id:
                progress.setdefault("submissions", {})[problem_id] = {
                    "code": code,
                    "passed": passed,
                }
                save_progress(progress)

            self.send_json({"success": True, "progress": progress})

        else:
            self.send_json({"error": "Unknown action"}, 400)

    def get_roadmap_progress(self):
        """Get roadmap progress."""
        roadmap_progress = progress.get("roadmap", {
            "currentDay": 1,
            "currentPhase": 1,
            "completedDays": [],
            "unlockedPhases": [1]
        })
        self.send_json(roadmap_progress)

    def update_roadmap_progress(self):
        """Update roadmap progress."""
        global progress

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_json({"error": "No content"}, 400)
            return

        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        # Initialize roadmap progress if not exists
        if "roadmap" not in progress:
            progress["roadmap"] = {
                "currentDay": 1,
                "currentPhase": 1,
                "completedDays": [],
                "unlockedPhases": [1]
            }

        roadmap = progress["roadmap"]
        action = data.get("action")

        if action == "complete_day":
            day = data.get("day")
            if day is not None:
                if day not in roadmap["completedDays"]:
                    roadmap["completedDays"].append(day)
                    roadmap["completedDays"].sort()

                # Auto-advance current day
                if roadmap["currentDay"] == day:
                    roadmap["currentDay"] = day + 1

                    # Check if phase is complete and unlock next phase
                    if roadmap["currentDay"] > 15 and roadmap["currentPhase"] == 1:
                        roadmap["currentPhase"] = 2
                        if 2 not in roadmap["unlockedPhases"]:
                            roadmap["unlockedPhases"].append(2)
                    elif roadmap["currentDay"] > 30 and roadmap["currentPhase"] == 2:
                        roadmap["currentPhase"] = 3
                        if 3 not in roadmap["unlockedPhases"]:
                            roadmap["unlockedPhases"].append(3)
                    elif roadmap["currentDay"] > 45 and roadmap["currentPhase"] == 3:
                        roadmap["currentPhase"] = 4
                        if 4 not in roadmap["unlockedPhases"]:
                            roadmap["unlockedPhases"].append(4)

                save_progress(progress)
                self.send_json({"success": True, "progress": roadmap})
            else:
                self.send_json({"error": "Day not provided"}, 400)

        elif action == "set_day":
            day = data.get("day")
            if day is not None and 1 <= day <= 60:
                roadmap["currentDay"] = day

                # Update phase based on day
                if day <= 15:
                    roadmap["currentPhase"] = 1
                elif day <= 30:
                    roadmap["currentPhase"] = 2
                elif day <= 45:
                    roadmap["currentPhase"] = 3
                else:
                    roadmap["currentPhase"] = 4

                save_progress(progress)
                self.send_json({"success": True, "progress": roadmap})
            else:
                self.send_json({"error": "Invalid day"}, 400)

        else:
            self.send_json({"error": "Unknown action"}, 400)

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def main():
    """Start the server."""
    # Ensure directories exist
    DATA_DIR.mkdir(exist_ok=True)
    STATIC_DIR.mkdir(exist_ok=True)

    # Check for problems.json
    problems_file = DATA_DIR / "problems.json"
    if not problems_file.exists():
        print("Error: problems.json not found!")
        print("Run 'python merge_dataset.py' first to create the dataset.")
        sys.exit(1)

    # Check static files
    if not (STATIC_DIR / "index.html").exists():
        print("Error: static/index.html not found!")
        sys.exit(1)

    class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        """Threaded HTTP server for concurrent requests."""
        daemon_threads = True
        allow_reuse_address = True

    server = ThreadedHTTPServer(("", PORT), LeetCodeHandler)
    print(f"\n" + "=" * 50)
    print(f"  LeetCode Helper")
    print(f"=" * 50)
    print(f"  Server running at: http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print(f"=" * 50 + "\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()
