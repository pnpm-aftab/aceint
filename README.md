# Aceint (LeetCode Helper)

Aceint is a powerful, locally-hosted web application designed to help you master LeetCode problems through a structured, pedagogical approach. It combines a massive offline problem set with AI-driven tutoring and a comprehensive 60-day roadmap.

## 🚀 Key Features

- **3,700+ Problems:** Full offline access to a massive library of LeetCode problems, complete with descriptions, test cases, and starter code.
- **Pedagogical Quizzing:** Before writing code, test your understanding with AI-generated, scaffolded quizzes that follow a strict learning pipeline:
  1. **Understanding:** Clarify I/O and problem constraints.
  2. **Pattern:** Identify the correct algorithmic strategy.
  3. **Invariant:** Pinpoint the core logic that remains true during execution.
  4. **Implementation:** Structure the code flow.
  5. **Edge Cases:** Anticipate tricky inputs.
- **AI-Powered Tutoring:** Integrated with OpenRouter (defaulting to `openrouter/healer-alpha`) to provide:
  - **Progressive Hints:** Get guidance without spoiling the answer.
  - **Code Explanations:** Deep dives into logic and time/space complexity.
  - **Chat Interface:** Ask specific questions about your current approach.
- **60-Day Roadmap:** A structured path from "Foundations" to "Advanced Algorithms," organized into 4 phases (15 days each) with daily focus topics and curated problems.
- **Integrated Editor:** A clean, dark-themed coding environment with Python syntax highlighting and integrated test case runner.
- **Progress Tracking:** Automatically track your solved problems, save your best solutions, and monitor your roadmap progress.

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python (`http.server`), `requests`, `python-dotenv` |
| **Frontend** | Vanilla HTML5/CSS3/JS, Lucide Icons, Marked.js |
| **AI** | OpenRouter API (`openrouter/healer-alpha`) |
| **Data** | JSON-based storage for problems, progress, and quizzes |

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd leetcode-helper
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Key:**
   - Create a `.env` file in the root directory.
   - Add your OpenRouter API key: `OPENROUTER_API_KEY=your_key_here`
   - *Alternatively*, you can set this directly in the app's Settings modal.

4. **Launch the app:**
   ```bash
   python server.py
   ```

5. **Open in your browser:**
   Navigate to `http://localhost:8888`

## 📖 Usage Guide

### 1. The Problems Tab
Browse and filter the massive problem set by difficulty, status, or tags. Click a problem to load it into the editor.

### 2. The Quiz Bridge
Before you code, use the **Quiz tab**. It's designed to ensure you actually *understand* the problem before you start fighting the compiler. If you fail a specific stage (like "Invariant"), you can regenerate just that stage to refine your mental model.

### 3. Solving & Testing
Write your Python code in the editor. Use the **Run** button to execute it against the problem's example test cases. The console will show you exactly where your logic succeeded or failed.

### 4. Roadmap Navigation
Use the **Roadmap tab** to follow a structured path. Each day provides a specific focus area and a set of problems to tackle. Mark days as complete to unlock the next phase of your journey.

---

*Aceint: Bridge the gap from concept to code.*
