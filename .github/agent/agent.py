#!/usr/bin/env python3
"""SLM microagent for Pulsar Linux ISO repo.

Reviews PKGBUILDs, shell scripts, configs for bugs and auto-fixes them.
Uses Qwen2.5-1.5B-Instruct via llama-cpp-python + DuckDuckGo search.
"""

import os
import json
import subprocess
import glob
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box

console = Console()

MODEL_URL = os.environ.get(
    "MODEL_URL",
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
)
MODEL_PATH = os.environ.get("MODEL_PATH", "/tmp/model.gguf")
REPO_PATH = "/__w/pulsar-iso/pulsar-iso"

tools = []
tool_calls_made = 0
files_fixed = 0

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
    global files_fixed
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
    files_fixed += 1
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
SYS_MSG = (
    "You are a code review agent for Pulsar Linux ISO repository. "
    "Review PKGBUILDs, bash scripts, and config files for bugs. "
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

def step(msg: str, style: str = "cyan"):
    console.print(f"  {msg}", style=style)

def ok(msg: str):
    console.print(f"  [green]✓ {msg}[/green]")

def warn(msg: str):
    console.print(f"  [yellow]⚠ {msg}[/yellow]")

def err(msg: str):
    console.print(f"  [red]✗ {msg}[/red]")

def download_model():
    if os.path.exists(MODEL_PATH):
        return
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("downloading model (~1GB Qwen2.5-1.5B)...", total=None)
        subprocess.run(
            ["wget", "-q", "-O", MODEL_PATH, MODEL_URL],
            check=True
        )

def load_llm():
    from llama_cpp import Llama
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("loading model into memory...", total=None)
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=32768,
            n_threads=4,
            n_gpu_layers=0,
            verbose=False,
        )
    return llm

def ask_llm(llm, messages: list) -> dict:
    response = llm.create_chat_completion(
        messages=messages,
        tools=TOOL_DEFS,
        tool_choice="auto",
        temperature=0.1,
        max_tokens=2048,
    )
    return response["choices"][0]["message"]

def review_file(llm, rel_path: str, progress_desc: str):
    global tool_calls_made
    messages = [
        {"role": "system", "content": SYS_MSG},
    ]

    full = os.path.join(REPO_PATH, rel_path)
    if not os.path.exists(full):
        warn(f"skipped (not found)")
        return False

    with open(full) as f:
        content = f.read()

    content_trunc = content
    if len(content_trunc) > 6000:
        content_trunc = content_trunc[:3000] + "\n... (truncated)\n" + content_trunc[-3000:]

    messages.append({
        "role": "user",
        "content": (
            f"Review this file for bugs:\n\n"
            f"File: {rel_path}\n"
            f"```\n{content_trunc}\n```\n\n"
            "Check for syntax errors, missing variables, bad practices, or potential runtime issues. "
            "If you find a bug, use the edit_file tool to fix it. "
            "Use run_shell to run syntax checks (bash -n for .sh, namcap for PKGBUILD). "
            "If unsure, use search_web to look up documentation."
        )
    })

    console.print()
    console.print(Panel(
        Syntax(content[:1500] if len(content) > 1500 else content, "bash" if rel_path.endswith(".sh") else "ini", theme="monokai", line_numbers=True),
        title=f"[bold]{rel_path}[/bold]",
        subtitle=f"{len(content)} bytes",
        border_style="blue",
        box=box.ROUNDED,
    ))

    for attempt in range(5):
        msg = ask_llm(llm, messages)
        if "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                fn = TOOL_MAP.get(name)
                if fn:
                    tool_calls_made += 1
                    args_preview = json.dumps(args)
                    if len(args_preview) > 120:
                        args_preview = args_preview[:120] + '...'
                    step(f"🛠 {name}({args_preview})", style="bold yellow")
                    result = fn(**args)
                    if result.startswith("OK:"):
                        ok(result)
                    elif result.startswith("ERROR:"):
                        err(result)
                    else:
                        result_trunc = result[:300] + ('...' if len(result) > 300 else '')
                        console.print(Panel(
                            result_trunc,
                            title=f"result: {name}",
                            border_style="green",
                            box=box.SIMPLE,
                            padding=(0, 1),
                        ))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result[:2000]
                    })
            continue
        else:
            text = msg.get("content", "").strip()
            if text:
                md = Markdown(text[:500])
                console.print(Panel(md, border_style="magenta", box=box.SIMPLE, padding=(0, 1)))
            break

    return files_fixed > 0

def print_header():
    console.print()
    console.print(Panel(
        "[bold cyan]PULSAR LINUX MICROAGENT[/bold cyan]\n"
        "[dim]SLM-powered code reviewer • Qwen2.5-1.5B • DuckDuckGo search[/dim]",
        subtitle=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        box=box.DOUBLE,
    ))

def print_summary(targets: list, fixed: int):
    table = Table(title="Review Summary", box=box.ROUNDED)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Files reviewed", str(len(targets)))
    table.add_row("Tool calls", str(tool_calls_made))
    table.add_row("Files fixed", str(fixed))
    table.add_row("SHA", os.environ.get("GITHUB_SHA", "N/A")[:7])
    if fixed > 0:
        table.add_row("Result", "[green]Fixes committed ✓[/green]")
    else:
        table.add_row("Result", "[dim]No issues found[/dim]")
    console.print()
    console.print(table)
    console.print()

def setup_git_auth():
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
    global files_fixed
    print_header()

    download_model()
    llm = load_llm()
    os.chdir(REPO_PATH)
    setup_git_auth()

    targets = sorted(set(
        t.strip() for t in (
            list_files("packages/*/PKGBUILD").split("\n")
            + list_files("*.sh").split("\n")
            + list_files("airootfs/**/*.sh").split("\n")
            + list_files("*.conf").split("\n")
            + list_files("profiledef.sh").split("\n")
        ) if t.strip()
    ))

    console.print(f"\n  [dim]found {len(targets)} files to review[/dim]")

    with Progress(
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TextColumn("[bold]{task.fields[name]}"),
        transient=False,
    ) as progress:
        task = progress.add_task("", total=len(targets), name="")
        for t in targets:
            progress.update(task, name=f"[blue]{t}[/blue]")
            try:
                review_file(llm, t)
            except Exception as e:
                console.print(f"  [red]ERROR reviewing {t}: {e}[/red]")
            progress.advance(task)

    print_summary(targets, files_fixed)

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_PATH
    )
    if result.stdout.strip():
        console.print("[bold green]Committing fixes...[/bold green]")
        subprocess.run(["git", "add", "-A"], cwd=REPO_PATH)
        subprocess.run(
            ["git", "commit", "-m", f"[microagent] auto-fix {os.environ.get('GITHUB_SHA', '')[:7]}"],
            cwd=REPO_PATH
        )
        subprocess.run(["git", "push"], cwd=REPO_PATH)
        console.print("[bold green]Pushed ✓[/bold green]")
    else:
        console.print("[dim]No changes to commit[/dim]")

if __name__ == "__main__":
    main()
