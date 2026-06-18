#!/usr/bin/env python3
"""
4G-P2-A — Analizador de corridas del pipeline G1 Safety Runtime
Lee logs de ~/runs/4G/<timestamp>/ y extrae métricas de reproducibilidad.
Uso: python3 analyze_runs.py [--runs-dir ~/runs/4G] [--output markdown|csv]
"""

import os
import re
import sys
import argparse
import statistics
import datetime

# ─── PATRONES DE BÚSQUEDA ────────────────────────────────────────────────────

# launcher.log
RE_LAUNCHER_START   = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] Run directory:')
RE_ISAAC_LAUNCHED   = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] Isaac PID:')
RE_MARKER_DETECTED  = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] Isaac vivo tras marker')
RE_BCD_LAUNCHED     = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] Lanzando observer\.\.\.')
RE_NODES_OK         = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] === VERIFICACIÓN DE NODOS ===')
RE_TOPICS_OK        = re.compile(r'\[(\d{2}:\d{2}:\d{2})\]   TOPIC OK: /recovery_events')
RE_LAUNCHER_PASS    = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] LAUNCHER (PASS|FAIL)')
RE_POST_WINDOW      = re.compile(r'\[(\d{2}:\d{2}:\d{2})\] === VERIFICACIÓN POST-VENTANA ===')
RE_TEARDOWN_CLEAN   = re.compile(r'terminado limpio \(exit=0\)')
RE_ISAAC_OK_POST    = re.compile(r'Isaac vivo post-ventana OK')

# observer y watchdog — SafetyEvent
RE_SAFETY_EVENT_OBS = re.compile(r'SafetyEvent|4F-P1', re.IGNORECASE)
RE_SAFETY_EVENT_WDG = re.compile(r'SafetyEvent|4F-P2-', re.IGNORECASE)
RE_RECOVERY_REACT   = re.compile(r'executing|intervención|RECOVERY_ACTION|recovery_action', re.IGNORECASE)

RE_FALL_MARKER      = re.compile(r'=== G1_FALL_MARKER ({.*?}) ===')
RE_OBS_EVENT_TIME   = re.compile(r'=== G1_OBSERVER_EVENT_TIME ({.*?}) ===')

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def to_seconds(t_str):
    """HH:MM:SS → segundos desde medianoche."""
    h, m, s = map(int, t_str.split(':'))
    return h * 3600 + m * 60 + s

def diff_s(t1, t2):
    """Diferencia en segundos entre dos HH:MM:SS (t2 - t1)."""
    return to_seconds(t2) - to_seconds(t1)

def read(path):
    try:
        return open(path).read()
    except:
        return ""

def count_safety_events(log_text, pattern):
    """Cuenta líneas que contienen SafetyEvent real (no solo warnings de init)."""
    count = 0
    for line in log_text.splitlines():
        if pattern.search(line):
            # Excluir líneas de inicialización/configuración
            if any(x in line for x in ['iniciado', 'startup', 'Threshold', 'STARTUP', 'grace', 'warmup', 'rate_warmup']):
                continue
            count += 1
    return count

def percentile(data, p):
    if not data:
        return None
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)

# ─── ANÁLISIS POR CORRIDA ────────────────────────────────────────────────────

def analyze_run(run_dir):
    result = {
        "run_dir":                    os.path.basename(run_dir),
        "pass_fail":                  "UNKNOWN",
        "t_isaac_marker_s":           None,
        "t_bcd_ready_s":              None,
        "t_total_pass_s":             None,
        "post_window_alive":          False,
        "teardown_clean":             False,
        "observer_fp_count":          0,
        "watchdog_fp_count":          0,
        "recovery_reaction_count":    0,
        "false_positive_count_total": 0,
        "invalid_reason":             None,
        "t0_ns":                      None,
        "t1_ns":                      None,
        "t0_to_t1_ms":                None,
        "t0_t1_error":                None,
    }

    launcher = read(os.path.join(run_dir, "launcher.log"))
    isaac_log = read(os.path.join(run_dir, "A_isaac.log"))
    observer = read(os.path.join(run_dir, "B_observer.log"))
    watchdog = read(os.path.join(run_dir, "C_watchdog.log"))
    recovery = read(os.path.join(run_dir, "D_recovery.log"))

    if not launcher:
        result["pass_fail"] = "INVALID"
        result["invalid_reason"] = "launcher.log vacío o ausente"
        # t0→t1 latencia física→SafetyEvent (P3-B)
    import json as _json
    m_fall = RE_FALL_MARKER.search(isaac_log)
    m_obs  = RE_OBS_EVENT_TIME.search(observer)
    if m_fall and m_obs:
        try:
            t0 = _json.loads(m_fall.group(1))
            t1 = _json.loads(m_obs.group(1))
            if t0.get("schema") == "g1_fall_marker_v1" and t1.get("schema") == "g1_observer_event_time_v1":
                result["t0_ns"]       = t0["host_time_ns"]
                result["t1_ns"]       = t1["host_time_ns"]
                result["t0_to_t1_ms"] = (t1["host_time_ns"] - t0["host_time_ns"]) / 1e6
            else:
                result["t0_t1_error"] = f"schema mismatch: fall={t0.get('schema')} obs={t1.get('schema')}"
        except Exception as e:
            result["t0_t1_error"] = f"{type(e).__name__}: {e}"
    elif not m_fall:
        result["t0_t1_error"] = "G1_FALL_MARKER ausente en A_isaac.log"
    elif not m_obs:
        result["t0_t1_error"] = "G1_OBSERVER_EVENT_TIME ausente en B_observer.log"
    return result

    # Extraer timestamps
    t_start   = RE_LAUNCHER_START.search(launcher)
    t_isaac   = RE_ISAAC_LAUNCHED.search(launcher)
    t_marker  = RE_MARKER_DETECTED.search(launcher)
    t_bcd     = RE_BCD_LAUNCHED.search(launcher)
    t_topics  = RE_TOPICS_OK.search(launcher)
    t_pass    = RE_LAUNCHER_PASS.search(launcher)
    t_post    = RE_POST_WINDOW.search(launcher)

    # t_isaac_marker: Isaac lanzado → marker detectado
    if t_isaac and t_marker:
        result["t_isaac_marker_s"] = diff_s(t_isaac.group(1), t_marker.group(1))

    # t_bcd_ready: BCD lanzado → topics OK
    if t_bcd and t_topics:
        result["t_bcd_ready_s"] = diff_s(t_bcd.group(1), t_topics.group(1))

    # t_total_pass: inicio → PASS
    if t_start and t_pass:
        result["t_total_pass_s"] = diff_s(t_start.group(1), t_pass.group(1))

    # PASS/FAIL
    if t_pass:
        result["pass_fail"] = t_pass.group(2)
    else:
        result["pass_fail"] = "FAIL"
        result["invalid_reason"] = "No se encontró declaración PASS/FAIL"

    # post_window_alive
    result["post_window_alive"] = bool(RE_ISAAC_OK_POST.search(launcher))

    # teardown_clean
    teardown_matches = RE_TEARDOWN_CLEAN.findall(launcher)
    result["teardown_clean"] = len(teardown_matches) >= 4  # isaac + observer + watchdog + recovery

    # Falsos positivos
    result["observer_fp_count"]       = count_safety_events(observer, RE_SAFETY_EVENT_OBS)
    result["watchdog_fp_count"]       = count_safety_events(watchdog, RE_SAFETY_EVENT_WDG)
    result["recovery_reaction_count"] = count_safety_events(recovery, RE_RECOVERY_REACT)
    result["false_positive_count_total"] = result["observer_fp_count"] + result["watchdog_fp_count"]

    # Invalidar si hay SafetyEvent en observer o watchdog durante baseline
    if result["false_positive_count_total"] > 0 and result["pass_fail"] == "PASS":
        result["pass_fail"] = "INVALID"
        result["invalid_reason"] = (
            f"SafetyEvent durante baseline sano: "
            f"observer={result['observer_fp_count']} "
            f"watchdog={result['watchdog_fp_count']}"
        )
    # Segunda barrera: recovery reaccionó en baseline
    if result["recovery_reaction_count"] > 0 and result["pass_fail"] == "PASS":
        result["pass_fail"] = "INVALID"
        result["invalid_reason"] = (
            f"Recovery reaccionó durante baseline sano "
            f"({result['recovery_reaction_count']} eventos)"
        )

    return result

# ─── ESTADÍSTICA AGREGADA ────────────────────────────────────────────────────

def aggregate(results):
    valid = [r for r in results if r["pass_fail"] == "PASS"]
    n_total = len(results)
    n_pass  = len(valid)
    n_fail  = len([r for r in results if r["pass_fail"] == "FAIL"])
    n_inv   = len([r for r in results if r["pass_fail"] == "INVALID"])

    def stats(key):
        vals = [r[key] for r in valid if r[key] is not None]
        if not vals:
            return {"n": 0, "min": None, "mean": None, "std": None, "max": None, "p95": None}
        return {
            "n":    len(vals),
            "min":  min(vals),
            "mean": statistics.mean(vals),
            "std":  statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "max":  max(vals),
            "p95":  percentile(vals, 95),
        }

    return {
        "n_total": n_total,
        "n_pass":  n_pass,
        "n_fail":  n_fail,
        "n_invalid": n_inv,
        "pass_rate": f"{100*n_pass/n_total:.1f}%" if n_total else "N/A",
        "t_isaac_marker_s": stats("t_isaac_marker_s"),
        "t_bcd_ready_s":    stats("t_bcd_ready_s"),
        "t_total_pass_s":   stats("t_total_pass_s"),
        "total_fp":         sum(r["false_positive_count_total"] for r in results),
        "observer_fp":      sum(r["observer_fp_count"] for r in results),
        "watchdog_fp":      sum(r["watchdog_fp_count"] for r in results),
        "recovery_react":   sum(r["recovery_reaction_count"] for r in results),
        "t0_to_t1_ms":      stats("t0_to_t1_ms"),
    }

# ─── OUTPUT ──────────────────────────────────────────────────────────────────

def print_markdown(results, agg):
    print(f"\n# 4G-P2-A — Reproducibilidad Baseline Sano")
    print(f"Generado: {datetime.datetime.now().isoformat()}\n")

    print(f"## Resumen")
    print(f"| Métrica | Valor |")
    print(f"|---|---|")
    print(f"| N total | {agg['n_total']} |")
    print(f"| PASS | {agg['n_pass']} |")
    print(f"| FAIL | {agg['n_fail']} |")
    print(f"| INVALID | {agg['n_invalid']} |")
    print(f"| PASS rate | {agg['pass_rate']} |")
    print(f"| Falsos positivos totales | {agg['total_fp']} |")
    print(f"| Observer FP | {agg['observer_fp']} |")
    print(f"| Watchdog FP | {agg['watchdog_fp']} |")
    print(f"| Recovery reacciones | {agg['recovery_react']} |")
    print(f"| t0→t1 ms (media) | {agg['t0_to_t1_ms']['mean']:.2f} ms |" if agg["t0_to_t1_ms"]["n"] else "| t0→t1 ms | N/A |")
    print(f"| t0→t1 ms (min/max) | {agg['t0_to_t1_ms']['min']:.2f} / {agg['t0_to_t1_ms']['max']:.2f} ms |" if agg["t0_to_t1_ms"]["n"] else "")

    print(f"\n## Estadística de tiempos (corridas PASS)")
    for key, label in [
        ("t_isaac_marker_s", "t Isaac→marker (s)"),
        ("t_bcd_ready_s",    "t marker→B/C/D ready (s)"),
        ("t_total_pass_s",   "t total→PASS (s)"),
    ]:
        s = agg[key]
        if s["n"] == 0:
            print(f"| {label} | N/A |")
            continue
        print(f"\n### {label}")
        print(f"| N | min | media | std | max | p95 |")
        print(f"|---|---|---|---|---|---|")
        print(f"| {s['n']} | {s['min']:.1f} | {s['mean']:.1f} | {s['std']:.1f} | {s['max']:.1f} | {s['p95']:.1f} |")

    print(f"\n## Detalle por corrida")
    print(f"| Corrida | PASS/FAIL | t_marker(s) | t_bcd(s) | t_total(s) | FP_obs | FP_wdg | post_window | teardown | nota |")
    print(f"|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        nota = r["invalid_reason"] or ""
        print(f"| {r['run_dir']} | {r['pass_fail']} | "
              f"{r['t_isaac_marker_s'] or 'N/A'} | "
              f"{r['t_bcd_ready_s'] or 'N/A'} | "
              f"{r['t_total_pass_s'] or 'N/A'} | "
              f"{r['observer_fp_count']} | "
              f"{r['watchdog_fp_count']} | "
              f"{'✅' if r['post_window_alive'] else '❌'} | "
              f"{'✅' if r['teardown_clean'] else '❌'} | "
              f"{nota} |")

def print_csv(results, agg):
    print("run_dir,pass_fail,t_isaac_marker_s,t_bcd_ready_s,t_total_pass_s,"
          "observer_fp,watchdog_fp,recovery_react,post_window,teardown,t0_to_t1_ms,t0_t1_error,nota")
    for r in results:
        print(f"{r['run_dir']},{r['pass_fail']},"
              f"{r['t_isaac_marker_s'] or ''},"
              f"{r['t_bcd_ready_s'] or ''},"
              f"{r['t_total_pass_s'] or ''},"
              f"{r['observer_fp_count']},"
              f"{r['watchdog_fp_count']},"
              f"{r['recovery_reaction_count']},"
              f"{r['post_window_alive']},"
              f"{r['teardown_clean']},"
              f"{r['t0_to_t1_ms'] or ''},"
              f"{r['t0_t1_error'] or ''},"
              f"{r['invalid_reason'] or ''}")

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", default=os.path.expanduser("~/runs/4G"),
                        help="Directorio raíz de corridas")
    parser.add_argument("--output", choices=["markdown", "csv"], default="markdown")
    parser.add_argument("--since", default=None,
                        help="Filtrar corridas desde este timestamp YYYYMMDD_HHMMSS (inclusive)")
    args = parser.parse_args()

    runs_dir = os.path.expanduser(args.runs_dir)
    if not os.path.isdir(runs_dir):
        print(f"ERROR: {runs_dir} no existe", file=sys.stderr)
        sys.exit(1)

    # Descubrir corridas (subdirectorios con launcher.log)
    run_dirs = sorted([
        os.path.join(runs_dir, d)
        for d in os.listdir(runs_dir)
        if os.path.isdir(os.path.join(runs_dir, d)) and
           os.path.exists(os.path.join(runs_dir, d, "launcher.log"))
    ])

    if not run_dirs:
        print(f"No se encontraron corridas con launcher.log en {runs_dir}", file=sys.stderr)
        sys.exit(1)

    total_found = len(run_dirs)
    ignored = 0
    if args.since:
        filtered = [d for d in run_dirs if os.path.basename(d) >= args.since]
        ignored = total_found - len(filtered)
        run_dirs = filtered

    print(f"runs_dir:  {runs_dir}", file=sys.stderr)
    print(f"since:     {args.since or 'sin filtro'}", file=sys.stderr)
    print(f"encontradas: {total_found}", file=sys.stderr)
    print(f"ignoradas:   {ignored}", file=sys.stderr)
    print(f"analizadas:  {len(run_dirs)}", file=sys.stderr)

    if not run_dirs:
        print("No quedan corridas tras aplicar --since", file=sys.stderr)
        sys.exit(1)

    results = [analyze_run(d) for d in run_dirs]
    agg = aggregate(results)

    if args.output == "markdown":
        print_markdown(results, agg)
    else:
        print_csv(results, agg)

if __name__ == "__main__":
    main()
