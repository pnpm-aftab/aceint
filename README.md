# LeetCode Helper

A minimal, dark-themed web app for solving LeetCode problems locally.

## Features

| Feature | Description |
| ------- | ----------- |
| Problems | 3,700+ LeetCode problems with test cases |
| Editor | Python syntax highlighting with tab support |
| Progress | Track solved/unsolved status |
| Search | Filter by difficulty, status, tags |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Web Interface

```bash
python server.py
```

Open http://localhost:8888

### CLI Workflow

```bash
# Initialize a problem
python -m leetcode_helper.cli init 1
```

## Project Structure

```
leetcode-helper/
├── data/
│   ├── problems.json         # Problem data
│   ├── problems_index.json   # Fast-loading index
│   └── progress.json         # User progress
├── static/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── roadmap.json          # 60-day learning roadmap
├── leetcode_helper/          # CLI package
├── solutions/                # Solution files
├── server.py                 # Web server
└── tray_app.py               # System tray app
```

## Tech Stack

| Component | Technology |
| --------- | ---------- |
| Backend | Python stdlib (`http.server`, `json`) |
| Frontend | Vanilla HTML/CSS/JS |
| Storage | JSON files |

## Keyboard Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `Tab` | Insert 4 spaces |
| `Ctrl+C` | Stop server |
