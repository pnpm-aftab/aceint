"""LeetCode Helper - Pure Python HTTP server."""
import http.server
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
                    # and parse it
                    expected_val = ast.literal_eval(expected_output.strip())
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

    def get_ai_solution(self):
        """Generate AI solution using OpenRouter free models."""
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

        if not problem_title:
            self.send_json({"error": "Problem title required"}, 400)
            return

        # Format test cases for the prompt - handle both string and dict formats
        test_cases_str = ""
        for tc in test_cases[:3]:
            if isinstance(tc, list):
                # List of arguments
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

        # Build the prompt with starter code
        signature_block = f"""
Starter code (use EXACT class and method signature):
```python
{starter_code}
```""" if starter_code else ""

        prompt = f"""You are a Python tutor helping a beginner who struggles with syntax. Solve this LeetCode problem.

Problem: {problem_title}
Description: {problem_description[:2000]}

Test Cases:
{test_cases_str}
{signature_block}

RETURN A JSON OBJECT (no markdown, no prose, just raw JSON) in this exact format:
{{
  "code": "<full Python solution with comments on every line>",
  "walkthrough": [
    "Step 1: <plain English explanation of the first key part>",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "data_structures": [
    {{"name": "<Data Structure Name>", "why": "<Why this data structure is optimal here>"}}
  ],
  "key_syntax": [
    {{"snippet": "<short code snippet>", "meaning": "<what it means in plain English>"}}
  ]
}}

Rules for the code:
- Keep exact class/method signature from starter code
- Add a # comment on EVERY line explaining what it does
- Use simple variable names (seen, result, current)
- Add Time/Space complexity as a comment at the top

Rules for walkthrough: 3-5 steps, plain English, no jargon.
Rules for data_structures: Detail 1-2 core data structures used.
Rules for key_syntax: pick 3-5 Python syntax patterns used (dict, enumerate, zip, etc.) and explain them simply.

Output ONLY the raw JSON. No markdown fences. No text before or after."""

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
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 2500,
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

            if not content:
                self.send_json({"error": "Empty response from AI"}, 500)
                return

            # Try to parse as JSON; fall back to returning raw solution string
            content = content.strip()
            # Strip markdown fences if present
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()
            elif content.startswith("```"):
                content = content.split("\n", 1)[-1].rstrip("`").rstrip()
            
            if content.startswith("json"):
                content = content[4:].strip()
                
            try:
                parsed = json.loads(content)
                self.send_json({"solution": parsed})
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e}. Content was: {content[:200]}...")
                # Fall back: treat the whole content as code
                self.send_json({"solution": {"code": content, "walkthrough": [], "data_structures": [], "key_syntax": []}})

        except requests.exceptions.Timeout:
            self.send_json({"error": "Request timed out. Please try again."}, 504)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def get_ai_explanation(self):
        """Explain a piece of code or answer a syntax question using AI."""
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

        if not question:
            self.send_json({"error": "Question required"}, 400)
            return

        context_block = ""
        if code_snippet:
            context_block = f"\n\nCode in question:\n```python\n{code_snippet}\n```"
        if problem_title:
            context_block = f"Problem: {problem_title}{context_block}"

        prompt = f"""You are a patient Python teacher helping a beginner who struggles with coding interview syntax.

Their question: {question}
{context_block}

Answer in plain, friendly English. Rules:
- No jargon without explanation
- If explaining syntax, give a tiny standalone example
- Keep it short (3-6 sentences max unless a code example is needed)
- If showing code, wrap it in ```python ... ``` fences
- Focus on WHAT it does and WHY it's used, not just how"""

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
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                },
                timeout=45
            )

            if response.status_code != 200:
                self.send_json({"error": f"AI request failed: {response.status_code}"}, 500)
                return

            result = response.json()
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not answer:
                self.send_json({"error": "Empty response from AI"}, 500)
                return

            self.send_json({"answer": answer.strip()})

        except requests.exceptions.Timeout:
            self.send_json({"error": "Request timed out. Please try again."}, 504)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def get_hint(self):
        """Generate a progressive hint using Aurora Alpha."""
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

            if not problem_id:
                self.send_json({"error": "Problem ID required"}, 400)
                return

            global progress
            progress.setdefault("hints", {})
            
            problem_id = str(problem_id)
            hint_data = progress["hints"].get(problem_id, {"hints": [], "revealed": 0})
            
            needs_generation = regenerate or not hint_data["hints"] or len(hint_data["hints"]) < hint_level
            
            if needs_generation and hint_level <= 3:
                hint_prompt = self.build_hint_prompt(
                    problem_title, 
                    problem_description, 
                    starter_code, 
                    hint_level,
                    hint_data["hints"] if hint_data["hints"] and not regenerate else []
                )
                
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
                        "messages": [
                            {
                                "role": "user",
                                "content": hint_prompt
                            }
                        ],
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

    def build_hint_prompt(self, problem_title, problem_description, starter_code, hint_level, previous_hints):
        """Build a prompt to generate code hints that can be inserted into the editor."""
        
        hint_guidance = {
            1: "Show a MINIMAL code snippet (5-8 lines) that demonstrates the core concept. Add a comment on EVERY line explaining what it does. Leave the main logic as '???' with a hint comment. Example: '# Loop through each number in the list\\nfor num in nums:\\n    # TODO: check something about num\\n    pass'",
            
            2: "Show a PARTIAL solution (10-15 lines) with the structure filled in. Add detailed comments explaining each part. Mark 2-3 key parts with '???' and hint comments like '# ??? = what do we need to find?'",
            
            3: "Show a NEAR-COMPLETE solution with ONLY 1-2 small parts marked as '???'. Every line must have a comment explaining it. The comments should teach the person WHY each step is needed."
        }
        
        previous_hints_text = ""
        if previous_hints:
            previous_hints_text = "\n\nPrevious hints already given (build on these):\n" + "\n".join([f"Hint {i+1}" for i, h in enumerate(previous_hints) if h])
        
        prompt = f"""You are a coding tutor helping a beginner who struggles with Python syntax. Generate a code hint that will be INSERTED DIRECTLY INTO THEIR CODE EDITOR.

Problem: {problem_title}
Description: {problem_description}
Starter code (use this EXACT signature):
```python
{starter_code}
```
{previous_hints_text}

CRITICAL RULES:
1. Output ONLY Python code - no explanations outside the code
2. Add a comment on EVERY SINGLE LINE explaining what it does
3. Use '???' for parts they need to figure out
4. Add hint comments next to '???' like: '??? # HINT: calculate target - num'
5. Use simple variable names (seen, result, current, etc.)
6. Keep comments SHORT but HELPFUL
7. The code should be COPY-PASTE READY into the editor
8. Match the EXACT function signature from starter code

{hint_guidance[hint_level]}

Output ONLY the Python code with comments. No markdown blocks. No explanations. Just the code."""
        
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
