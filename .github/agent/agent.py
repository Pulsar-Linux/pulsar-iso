#!/usr/bin/env python3
"""SLM microagent for Pulsar Linux ISO repo.

Reviews PKGBUILDs, shell scripts, configs for bugs and auto-fixes them.
Uses a small GGUF model (Qwen2.5-1.5B-Instruct) via llama-cpp-python.
Can search docs via DuckDuckGo.
"""

import os
import json
import subprocess
import glob

MODEL_URL = os.environ.get(
    "MODEL_URL",
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
)
MODEL_PATH = os.environ.get("MODEL_PATH", "/tmp/model.gguf")
REPO_PATH = "/__w/pulsar-iso/pulsar-iso"

tools = []

def tool(fn):
    tools.append(fn)
    return fn

@tool
def read_file(path: str) -> str:
    """Read a file from the repository."""
    full = os.path.join(REPO_PATH, path.lstrip("/"))
    if not os.path.exists(full):
        return f"ERROR: file not found: {full}"
    with open(full) as f:
        return f.read()

@tool
def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string."""
    full = os.path.join(REPO_PATH, path.lstrip("/"))
    if not os.path.exists(full):
        return f"ERROR: file not found: {full}"
    with open(full) as f:
        content = f.read()
    if old_string not in content:
        return f"ERROR: old_string not found in {path}"
    content = content.replace(old_string, new_string, 1)
    with open(full, "w") as f:
        f.write(content)
    return f"OK: edited {path}"

@tool
def search_web(query: str) -> str:
    """Search DuckDuckGo for documentation or answers."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found."
        return "\n\n".join(
            f"{r['title']}\n{r['href']}\n{r['body']}" for r in results
        )
    except Exception as e:
        return f"Search error: {e}"

@tool
def run_shell(command: str) -> str:
    """Run a shell command (read-only or safe operations)."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        out = result.stdout[-2000:] if result.stdout else ""
        err = result.stderr[-1000:] if result.stderr else ""
        return f"exit code: {result.returncode}\nstdout:\n{out}\nstderr:\n{err}"
    except Exception as e:
        return f"ERROR: {e}"

@tool
def list_files(pattern: str) -> str:
    """List files matching a glob pattern (e.g. '**/*.sh', 'packages/*/PKGBUILD')."""
    files = glob.glob(os.path.join(REPO_PATH, pattern), recursive=True)
    rel = [os.path.relpath(f, REPO_PATH) for f in files]
    return "\n".join(sorted(rel))

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": t.__name__,
            "description": t.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    p: {"type": "string"}
                    for p in list(t.__code__.co_varnames[:t.__code__.co_argcount])
                },
                "required": list(t.__code__.co_varnames[:t.__code__.co_argcount]),
            },
        },
    }
    for t in tools
]

TOOL_MAP = {t.__name__: t for t in tools}

def download_model():
    if os.path.exists(MODEL_PATH):
        return
    print("[agent] downloading model...")
    subprocess.run(
        ["wget", "-q", "--show-progress", "-O", MODEL_PATH, MODEL_URL],
        check=True
    )
    print("[agent] model downloaded")

def load_llm():
    from llama_cpp import Llama
    print("[agent] loading model...")
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_threads=4,
        n_gpu_layers=0,
        verbose=False,
    )
    return llm

def ask_llm(llm, prompt: str) -> dict:
    """Ask the SLM to review something. Returns parsed tool calls or text."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a code review agent for Pulsar Linux ISO repository. "
                "You review PKGBUILDs, bash scripts, and config files for bugs. "
                "Use the available tools to read files, search documentation, "
                "and fix issues. Focus on:\n"
                "- PKGBUILD syntax errors or missing fields\n"
                "- Shell script bugs (unquoted variables, missing error handling)\n"
                "- Config file issues\n"
                "- Arch Linux packaging best practices\n\n"
                "When you find a bug, explain what's wrong and fix it using edit_file.\n"
                "Use search_web to look up Arch Wiki or packaging docs when unsure.\n"
                "Use run_shell for shellcheck, namcap, or syntax checks."
            )
        },
        {"role": "user", "content": prompt},
    ]
    response = llm.create_chat_completion(
        messages=messages,
        tools=TOOL_DEFS,
        tool_choice="auto",
        temperature=0.1,
        max_tokens=2048,
    )
    return response["choices"][0]["message"]

def process_file(llm, rel_path: str):
    """Have the SLM review a single file."""
    print(f"[agent] reviewing: {rel_path}")
    full = os.path.join(REPO_PATH, rel_path)
    if not os.path.exists(full):
        return
    # Read file content
    with open(full) as f:
        content = f.read()
    if len(content) > 6000:
        content = content[:3000] + "\n... (truncated)\n" + content[-3000:]

    prompt = (
        f"Review this file for bugs:\n\n"
        f"File: {rel_path}\n"
        f"```\n{content}\n```\n\n"
        "Check for syntax errors, missing variables, bad practices, or potential runtime issues. "
        "If you find a bug, use the edit_file tool to fix it. "
        "Use run_shell to run syntax checks (bash -n for .sh, namcap for PKGBUILD). "
        "If unsure, use search_web to look up documentation."
    )

    for attempt in range(5):
        msg = ask_llm(llm, prompt)
        if "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                fn = TOOL_MAP.get(name)
                if fn:
                    print(f"[agent]  → tool: {name}({json.dumps(args)[:100]})")
                    result = fn(**args)
                    print(f"[agent]  ← {result[:200]}")
                    prompt += f"\n\nTool result from {name}: {result[:1500]}"
            continue  # let model see results and decide next action
        else:
            print(f"[agent]  → {msg.get('content', '(no content)')[:200]}")
            break

def setup_git_auth():
    """Set git remote to include GITHUB_TOKEN for push auth."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True, cwd=REPO_PATH
    )
    url = result.stdout.strip()
    if url.startswith("https://"):
        authed = url.replace("https://", f"https://github-actions[bot]:{token}@")
        subprocess.run(
            ["git", "remote", "set-url", "origin", authed],
            cwd=REPO_PATH
        )

def main():
    download_model()
    llm = load_llm()
    os.chdir(REPO_PATH)
    setup_git_auth()

    # Files to review
    targets = (
        list_files("packages/*/PKGBUILD").split("\n")
        + list_files("*.sh").split("\n")
        + list_files("airootfs/**/*.sh").split("\n")
        + list_files("*.conf").split("\n")
        + list_files("profiledef.sh").split("\n")
    )
    targets = sorted(set(t for t in targets if t.strip()))

    print(f"[agent] {len(targets)} files to review")

    for t in targets:
        try:
            process_file(llm, t)
        except Exception as e:
            print(f"[agent] ERROR reviewing {t}: {e}")

    # Check if there are changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_PATH
    )
    if result.stdout.strip():
        print("[agent] changes detected, committing...")
        subprocess.run(["git", "add", "-A"], cwd=REPO_PATH)
        subprocess.run(
            ["git", "commit", "-m", f"[microagent] auto-fix {os.environ.get('GITHUB_SHA', '')[:7]}"],
            cwd=REPO_PATH
        )
        subprocess.run(["git", "push"], cwd=REPO_PATH)
    else:
        print("[agent] no changes")

if __name__ == "__main__":
    main()
