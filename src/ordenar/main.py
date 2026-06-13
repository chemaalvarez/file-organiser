"""
CLI entry point — `ordenar`

Commands:
  run    — organise a root folder (default: ~/Downloads)
  log    — display log of a past run
  undo   — revert a past run
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text

from .bootstrap import bootstrap
from .config import load_config
from .executor import Executor
from .hierarchy import build_plan
from .logger import RunLogger, find_latest_log, read_log
from .models import ItemType

app = typer.Typer(
    name="ordenar",
    help="Organizador inteligente de archivos — clasifica Downloads en Trabajo y Personal.",
    add_completion=False,
)
console = Console()


# ── run ───────────────────────────────────────────────────────────────────────

@app.command()
def run(
    root: Optional[Path] = typer.Option(
        None, "--root", "-r",
        help="Carpeta raíz a organizar. Por defecto: ~/Downloads",
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Ruta al fichero config.yaml",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n",
        help="Muestra el plan sin mover nada.",
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i",
        help="Pregunta antes de mover cada elemento ambiguo.",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Confirma automáticamente el plan sin preguntar.",
    ),
) -> None:
    """Organiza la carpeta raíz in-place siguiendo la taxonomía Trabajo/Personal."""

    cfg = load_config(config_path, root)
    root_path = root.expanduser().resolve() if root else cfg.root_path

    if not root_path.is_dir():
        rprint(f"[red]Error:[/red] La carpeta [bold]{root_path}[/bold] no existe.")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold cyan]ordenar[/bold cyan]  •  "
        f"{'[yellow]DRY-RUN[/yellow]  •  ' if dry_run else ''}"
        f"Raíz: [green]{root_path}[/green]",
        expand=False,
    ))

    # ── Phase 0: Bootstrap ────────────────────────────────────────────────────
    with console.status("[bold]Analizando estructura existente…"):
        ctx = bootstrap(root_path, cfg.companies)

    _print_context_summary(ctx)

    # ── Phase 1: Build plan (top-down classification) ─────────────────────────
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Clasificando archivos y carpetas…", total=None)
        decisions = build_plan(root_path, cfg, ctx)

    if not decisions:
        rprint("[green]✓ Todo está ya ordenado. No hay nada que mover.[/green]")
        raise typer.Exit(0)

    # ── Phase 2: Show plan ────────────────────────────────────────────────────
    _print_plan(decisions, root_path)

    if dry_run:
        rprint(f"\n[yellow]Dry-run:[/yellow] {len(decisions)} movimiento(s) planificados. "
               "Usa [bold]ordenar run[/bold] para ejecutar.")
        raise typer.Exit(0)

    # ── Confirmation ──────────────────────────────────────────────────────────
    if not yes:
        confirmed = typer.confirm(
            f"\n¿Ejecutar {len(decisions)} movimiento(s)?", default=True
        )
        if not confirmed:
            rprint("[yellow]Cancelado.[/yellow]")
            raise typer.Exit(0)

    # ── Phase 3: Execute ──────────────────────────────────────────────────────
    run_id = uuid.uuid4().hex[:8]
    logger = RunLogger(root_path, run_id, dry_run=False)
    executor = Executor(
        root=root_path,
        logger=logger,
        on_duplicate=cfg.on_duplicate,
        dry_run=False,
    )

    from .models import ActionType as _AT, RunSummary as _RS
    summary = _RS(run_id=run_id, root=root_path, dry_run=False, total_scanned=len(decisions))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Moviendo…", total=len(decisions))
        for decision in decisions:
            result = executor._execute_one(decision)
            logger.log_result(result)
            if result.action == _AT.MOVE:
                summary.moved += 1
            elif result.action == _AT.SKIP:
                summary.skipped += 1
            elif result.action == _AT.ERROR:
                summary.errors += 1
            if decision.category == "_SinClasificar":
                summary.unclassified += 1
            progress.advance(task)

    log_path = logger.finalize(summary)

    # ── Phase 4: Report ───────────────────────────────────────────────────────
    _print_summary(len(decisions), log_path)


# ── log ───────────────────────────────────────────────────────────────────────

@app.command()
def log(
    root: Optional[Path] = typer.Option(None, "--root", "-r"),
    last: bool = typer.Option(False, "--last", help="Muestra el último run."),
    run_id: Optional[str] = typer.Option(None, "--run", help="ID de run específico."),
    filter_action: Optional[str] = typer.Option(
        None, "--filter", help="Filtra por action (error, skip, move…)"
    ),
    fmt: str = typer.Option("table", "--format", help="table | json | csv | md"),
) -> None:
    """Muestra el log de un run."""
    cfg = load_config(root=root)
    root_path = root.expanduser().resolve() if root else cfg.root_path
    log_path = find_latest_log(root_path)

    if log_path is None:
        rprint("[yellow]No se encontró ningún log en .ordenar/[/yellow]")
        raise typer.Exit(1)

    entries = read_log(log_path)
    if filter_action:
        entries = [e for e in entries if e.get("action") == filter_action]

    if fmt == "json":
        import json
        print(json.dumps(entries, indent=2, ensure_ascii=False))
    elif fmt == "csv":
        _print_csv(entries)
    elif fmt == "md":
        _print_markdown(entries)
    else:
        _print_log_table(entries, log_path)


# ── undo ─────────────────────────────────────────────────────────────────────

@app.command()
def undo(
    root: Optional[Path] = typer.Option(None, "--root", "-r"),
    last: bool = typer.Option(False, "--last", help="Revierte el último run."),
    run_id: Optional[str] = typer.Option(None, "--run", help="ID del run a revertir."),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Revierte todos los movimientos de un run usando el log."""
    cfg = load_config(root=root)
    root_path = root.expanduser().resolve() if root else cfg.root_path
    log_path = find_latest_log(root_path)

    if log_path is None:
        rprint("[yellow]No se encontró ningún log.[/yellow]")
        raise typer.Exit(1)

    entries = [e for e in read_log(log_path) if e.get("action") == "move"]

    if not entries:
        rprint("[green]Nada que deshacer.[/green]")
        raise typer.Exit(0)

    rprint(f"[bold]Se revertirán {len(entries)} movimiento(s).[/bold]")
    if not yes:
        if not typer.confirm("¿Continuar?", default=False):
            raise typer.Exit(0)

    import shutil
    errors = 0
    for entry in reversed(entries):
        src = Path(entry["dst"])
        dst = Path(entry["src"])
        try:
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                rprint(f"  [dim]← {src.name}[/dim]")
            else:
                rprint(f"  [yellow]⚠ No existe: {src}[/yellow]")
        except Exception as exc:
            rprint(f"  [red]✗ {exc}[/red]")
            errors += 1

    if errors:
        rprint(f"[red]{errors} error(s) durante el undo.[/red]")
    else:
        rprint("[green]✓ Run revertido correctamente.[/green]")


# ── Rich helpers ──────────────────────────────────────────────────────────────

def _print_context_summary(ctx) -> None:
    parts = []
    if ctx.companies:
        parts.append(f"[cyan]{len(ctx.companies)}[/cyan] empresa(s): "
                     + ", ".join(f"[bold]{c}[/bold]" for c in ctx.companies[:5])
                     + ("…" if len(ctx.companies) > 5 else ""))
    if ctx.personal_categories:
        parts.append(f"[cyan]{len(ctx.personal_categories)}[/cyan] categoría(s) personal")
    if parts:
        console.print("  Contexto detectado: " + " · ".join(parts))


def _print_plan(decisions, root_path: Path) -> None:
    table = Table(title=f"Plan — {len(decisions)} movimiento(s)", show_lines=False)
    table.add_column("Tipo", style="dim", width=5)
    table.add_column("Origen", style="white", no_wrap=True, max_width=50)
    table.add_column("Destino", style="green", no_wrap=True, max_width=55)
    table.add_column("Regla", style="dim cyan", max_width=25)
    table.add_column("Conf.", style="dim", width=6)

    for d in decisions[:50]:  # preview first 50
        icon = "📁" if d.item_type == ItemType.FOLDER else "📄"
        src_rel = _rel(d.src, root_path)
        dst_rel = _rel(d.dst, root_path)
        conf_color = "green" if d.confidence >= 0.85 else ("yellow" if d.confidence >= 0.6 else "red")
        table.add_row(
            icon,
            str(src_rel),
            str(dst_rel),
            d.rule[:25],
            f"[{conf_color}]{d.confidence:.0%}[/{conf_color}]",
        )

    if len(decisions) > 50:
        table.add_row("…", f"… y {len(decisions) - 50} más", "", "", "")

    console.print(table)


def _print_summary(total: int, log_path: Path) -> None:
    rprint(f"\n[green]✓ {total} elemento(s) procesados.[/green]")
    rprint(f"  Log: [dim]{log_path}[/dim]")
    rprint("  Para ver el log: [bold]ordenar log --last[/bold]")
    rprint("  Para deshacer:  [bold]ordenar undo --last[/bold]")


def _print_log_table(entries: list[dict], log_path: Path) -> None:
    move_entries = [e for e in entries if e.get("action") == "move"]
    summary = next((e for e in entries if e.get("action") == "summary"), None)

    console.print(Panel(f"[bold]Log:[/bold] {log_path}", expand=False))

    table = Table(show_lines=False)
    table.add_column("Acción", width=6)
    table.add_column("Tipo", width=5)
    table.add_column("Origen", max_width=50, no_wrap=True)
    table.add_column("Destino", max_width=55, no_wrap=True)
    table.add_column("Regla", max_width=25)

    action_styles = {"move": "green", "skip": "yellow", "error": "red"}
    for e in move_entries[:100]:
        action = e.get("action", "?")
        style = action_styles.get(action, "white")
        table.add_row(
            f"[{style}]{action}[/{style}]",
            e.get("item_type", "?"),
            Path(e.get("src", "")).name,
            Path(e.get("dst", "")).name,
            e.get("rule", "")[:25],
        )

    console.print(table)

    if summary:
        rprint(
            f"\n  Total: {summary.get('total_scanned',0)} · "
            f"Movidos: [green]{summary.get('moved',0)}[/green] · "
            f"Omitidos: [yellow]{summary.get('skipped',0)}[/yellow] · "
            f"Errores: [red]{summary.get('errors',0)}[/red] · "
            f"Sin clasificar: {summary.get('unclassified',0)} · "
            f"{summary.get('duration_seconds',0):.1f}s"
        )


def _print_csv(entries: list[dict]) -> None:
    import csv, sys
    keys = ["ts", "action", "item_type", "src", "dst", "category", "rule", "confidence"]
    w = csv.DictWriter(sys.stdout, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(entries)


def _print_markdown(entries: list[dict]) -> None:
    print("| Acción | Tipo | Origen | Destino | Regla | Confianza |")
    print("|--------|------|--------|---------|-------|-----------|")
    for e in entries:
        if e.get("action") not in ("move", "skip", "error"):
            continue
        print(
            f"| {e.get('action','')} | {e.get('item_type','')} "
            f"| {Path(e.get('src','')).name} | {Path(e.get('dst','')).name} "
            f"| {e.get('rule','')} | {e.get('confidence','')} |"
        )


def _rel(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
