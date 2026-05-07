"""Static generator for Event / Message Flow Diagram (flowchart LR)."""

from __future__ import annotations

from pathlib import Path

from spartastruct.analyzer.base import AnalysisResult, FunctionInfo, MethodInfo

_TASK_DECORATORS = frozenset({
    "task", "shared_task", "celery_task", "app.task", "huey.task",
    "dramatiq.actor", "rq.job",
})
_EVENT_CALL_NAMES = frozenset({
    "emit", "publish", "dispatch", "send", "send_task", "delay",
    "apply_async", "trigger", "broadcast", "notify",
})


def _is_task(fn: FunctionInfo | MethodInfo) -> bool:
    return any(
        any(td in dec.lower() for td in _TASK_DECORATORS)
        for dec in fn.decorators
    )


def _emits_events(fn: FunctionInfo | MethodInfo) -> bool:
    return any(call in _EVENT_CALL_NAMES for call in fn.calls)


def generate(result: AnalysisResult) -> str:
    """Generate a Mermaid flowchart LR showing event/message dispatch patterns.

    Identifies Celery tasks, event emitters (emit/publish/dispatch), and
    async functions. Shows which components produce and consume messages.
    Falls back to an async call graph when no event patterns are found.

    Args:
        result: The full analysis result.

    Returns:
        A Mermaid flowchart LR string (without fences).
    """
    lines = ['%%{init: {"maxTextSize": 200000} }%%', "flowchart LR"]
    lines.append("    classDef producer fill:#fff3cd,stroke:#ff9800")
    lines.append("    classDef consumer fill:#d4edda,stroke:#28a745")
    lines.append("    classDef queue fill:#e8f4fd,stroke:#2196f3")
    lines.append("    classDef async_ fill:#e8f4fd,stroke:#2196f3")

    has_celery = "Celery" in result.frameworks
    has_socket = "Socket.IO" in result.frameworks

    task_fns: list[tuple[str, FunctionInfo | MethodInfo]] = []
    emitter_fns: list[tuple[str, FunctionInfo | MethodInfo]] = []
    async_fns: list[tuple[str, FunctionInfo]] = []

    for fr in result.files_analyzed:
        module = Path(fr.path).stem
        for fn in fr.functions:
            if _is_task(fn):
                task_fns.append((module, fn))
            elif _emits_events(fn):
                emitter_fns.append((module, fn))
            elif fn.is_async:
                async_fns.append((module, fn))
        for cls in fr.classes:
            for method in cls.methods:
                if _is_task(method):
                    task_fns.append((f"{module}.{cls.name}", method))
                elif _emits_events(method):
                    emitter_fns.append((f"{module}.{cls.name}", method))

    if not task_fns and not emitter_fns:
        if has_celery or has_socket:
            lines.append('    Producer["Producer"]:::producer')
            if has_celery:
                lines.append('    Queue[("Task Queue\\n(Celery)")]:::queue')
                lines.append('    Worker["Worker"]:::consumer')
                lines.append("    Producer -->|send_task()| Queue")
                lines.append("    Queue -->|execute| Worker")
            if has_socket:
                lines.append('    SocketServer["Socket.IO Server"]:::queue')
                lines.append('    SocketClient["Socket.IO Client"]:::consumer')
                lines.append("    Producer -->|emit()| SocketServer")
                lines.append("    SocketServer -->|broadcast| SocketClient")
        elif async_fns:
            lines.append('    Dispatcher["Async Dispatcher"]:::producer')
            for i, (module, fn) in enumerate(async_fns[:6]):
                node_id = f"af{i}"
                lines.append(f'    {node_id}["async {fn.name}()\\n{module}"]:::async_')
                lines.append(f"    Dispatcher --> {node_id}")
        else:
            lines.append('    noevent["No event/task patterns detected"]')
        return "\n".join(lines)

    if task_fns:
        lines.append('    subgraph tasks["Async Tasks"]')
        for i, (module, fn) in enumerate(task_fns[:8]):
            lines.append(f'        task{i}["{fn.name}()\\n{module}"]:::consumer')
        lines.append("    end")

    if emitter_fns:
        lines.append('    subgraph emitters["Event Emitters"]')
        for i, (module, fn) in enumerate(emitter_fns[:8]):
            lines.append(f'        emit{i}["{fn.name}()\\n{module}"]:::producer')
        lines.append("    end")

    if has_celery:
        lines.append('    Broker[("Message Broker")]:::queue')
        for i in range(min(len(emitter_fns), 8)):
            lines.append(f"    emit{i} -->|publish| Broker")
        for i in range(min(len(task_fns), 8)):
            lines.append(f"    Broker -->|consume| task{i}")
    elif emitter_fns and task_fns:
        lines.append('    Bus[("Event Bus")]:::queue')
        for i in range(min(len(emitter_fns), 8)):
            lines.append(f"    emit{i} -->|emit| Bus")
        for i in range(min(len(task_fns), 8)):
            lines.append(f"    Bus -->|handle| task{i}")

    return "\n".join(lines)
