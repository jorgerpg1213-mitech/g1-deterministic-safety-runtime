#!/usr/bin/env python3
"""
4G-P1 — Launcher Unificado del Pipeline G1 Safety Runtime
Corre desde la VM host. boring_noether debe estar corriendo antes.
Uso: python3 launch_pipeline.py [--allow-dirty]
"""

import subprocess
import os
import sys
import time
import datetime
import argparse

# ─── CONSTANTES CANÓNICAS ────────────────────────────────────────────────────

REPO          = os.path.expanduser("~/g1-deterministic-safety-runtime")
RUNS_BASE     = os.path.expanduser("~/runs/4G")
CONTAINER     = "boring_noether"
ISAAC_IMAGE   = "nvcr.io/nvidia/isaac-sim:4.5.0"
ISAAC_SIGNAL  = "P2+z0.720 SET"
ISAAC_TIMEOUT_S   = 300
NODE_VERIFY_WAIT  = 10
RUN_WINDOW_S      = 30
TEARDOWN_TIMEOUT  = 10

EXPECTED_NODES = [
    "/cross_consistency_observer",
    "/watchdog_g1",
    "/recovery_g1",
]

EXPECTED_TOPICS = [
    "/g1/imu",
    "/g1/contact/left",
    "/g1/contact/right",
    "/joint_states",
    "/safety_events",
    "/recovery_events",
]

REQUIRED_PATHS = [
    os.path.join(REPO, "sim_runtime/common/fastdds_udp.xml"),
    os.path.join(REPO, "sim_runtime/4F/combo_single.kit"),
    os.path.join(REPO, "sim_runtime/4F/g1ext_combo"),
    os.path.join(REPO, "install/g1_msgs"),
]

# ─── LOGGER DUAL (consola + archivo) ─────────────────────────────────────────

_logfile = None

def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if _logfile:
        _logfile.write(line + "\n")
        _logfile.flush()

def set_logfile(path):
    global _logfile
    _logfile = open(path, "w")

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def run_get(cmd, shell=False):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def teardown_proc(name, proc):
    if proc is None:
        return
    if proc.poll() is not None:
        log(f"  {name} ya había muerto (exit={proc.returncode})")
        return
    proc.terminate()
    try:
        proc.wait(timeout=TEARDOWN_TIMEOUT)
        log(f"  {name} terminado limpio (exit={proc.returncode})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        log(f"  {name} killed forzado (exit={proc.returncode})")

def tail_file_for_signal(filepath, signal, timeout_s):
    deadline = time.time() + timeout_s
    offset = 0
    while time.time() < deadline:
        if os.path.exists(filepath):
            with open(filepath) as f:
                f.seek(offset)
                chunk = f.read()
                offset += len(chunk)
                if signal in chunk:
                    return True
        time.sleep(2)
    return False

# ─── COMANDOS ────────────────────────────────────────────────────────────────

def isaac_cmd():
    return [
        "docker", "run", "--rm", "--gpus", "all", "--network=host",
        "-e", "ACCEPT_EULA=Y",
        "-e", "PRIVACY_CONSENT=Y",
        "-e", "OMNI_KIT_ALLOW_ROOT=1",
        "-e", "RMW_IMPLEMENTATION=rmw_fastrtps_cpp",
        "-e", "FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml",
        "-e", "PYTHONPATH=/g1msgs/local/lib/python3.10/dist-packages",
        "-e", "LD_LIBRARY_PATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/lib:/g1msgs/lib",
        "-v", f"{REPO}/sim_runtime/common/fastdds_udp.xml:/fastdds_udp.xml:ro",
        "-v", f"{REPO}/install/g1_msgs:/g1msgs:ro",
        "-v", os.path.expanduser("~/docker/isaac-sim/cache/kit") + ":/isaac-sim/kit/cache:rw",
        "-v", os.path.expanduser("~/docker/isaac-sim/cache/ov") + ":/root/.cache/ov:rw",
        "-v", os.path.expanduser("~/docker/isaac-sim/cache/pip") + ":/root/.cache/pip:rw",
        "-v", os.path.expanduser("~/docker/isaac-sim/cache/glcache") + ":/root/.cache/nvidia/GLCache:rw",
        "-v", os.path.expanduser("~/docker/isaac-sim/cache/computecache") + ":/root/.nv/ComputeCache:rw",
        "-v", f"{REPO}/sim_runtime/4F/combo_single.kit:/isaac-sim/apps/combo_single.kit:ro",
        "-v", f"{REPO}/sim_runtime/4F/g1ext_combo:/g1ext:ro",
        "--entrypoint", "/isaac-sim/kit/kit",
        ISAAC_IMAGE,
        "/isaac-sim/apps/combo_single.kit",
        "--no-window", "--allow-root",
        "--ext-folder", "/isaac-sim/apps",
        "--ext-folder", "/g1ext",
    ]

def ros2_env():
    return (
        "source /opt/ros/humble/setup.bash && "
        "source /ws/install/setup.bash && "
        "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && "
        "export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml"
    )

def launch_ros2(name, cmd_str, log_path):
    log(f"Lanzando {name}...")
    with open(log_path, "w") as lf:
        p = subprocess.Popen(
            ["docker", "exec", CONTAINER, "bash", "-c", cmd_str],
            stdout=lf, stderr=lf
        )
    return p

# ─── PREFLIGHT ───────────────────────────────────────────────────────────────

def preflight(allow_dirty):
    log("=== PREFLIGHT ===")
    ok = True

    # Repo existe
    if not os.path.isdir(REPO):
        log(f"FAIL preflight: REPO no existe: {REPO}")
        return False

    # Paths requeridos
    for path in REQUIRED_PATHS:
        if os.path.exists(path):
            log(f"  PATH OK: {path}")
        else:
            log(f"  PATH FALTANTE: {path}")
            ok = False

    # Repo limpio
    git_status = run_get(["git", "-C", REPO, "status", "--short"])
    if git_status and git_status != "ERROR":
        if allow_dirty:
            log(f"  WARN: repo sucio (--allow-dirty activo): {git_status}")
        else:
            log(f"  FAIL preflight: repo sucio. Usa --allow-dirty para forzar.\n  {git_status}")
            ok = False
    else:
        log("  GIT STATUS: limpio")

    # boring_noether corriendo
    docker_ps = run_get(["docker", "ps", "--filter", f"name={CONTAINER}",
                         "--format", "{{.Names}} {{.Status}}"])
    if CONTAINER in docker_ps:
        log(f"  CONTAINER OK: {docker_ps}")
    else:
        log(f"  FAIL preflight: {CONTAINER} no está corriendo")
        ok = False

    # /ws/install/setup.bash dentro del contenedor
    ws_check = run_get(
        f"docker exec {CONTAINER} bash -c 'test -f /ws/install/setup.bash && echo OK || echo MISSING'",
        shell=True
    )
    if "OK" in ws_check:
        log("  /ws/install/setup.bash: OK")
    else:
        log("  FAIL preflight: /ws/install/setup.bash no existe en contenedor")
        ok = False

    return ok

# ─── METADATA ────────────────────────────────────────────────────────────────

def save_metadata(run_dir, allow_dirty):
    log("=== METADATA ===")
    meta = {}
    meta["timestamp"]      = datetime.datetime.now().isoformat()
    meta["hostname"]       = run_get("hostname", shell=True)
    meta["python_version"] = run_get("python3 --version", shell=True)
    meta["date_iso"]       = run_get("date --iso-8601=seconds", shell=True)
    meta["commit_short"]   = run_get(["git", "-C", REPO, "rev-parse", "--short", "HEAD"])
    meta["commit_full"]    = run_get(["git", "-C", REPO, "rev-parse", "HEAD"])
    meta["git_status"]     = run_get(["git", "-C", REPO, "status", "--short"]) or "limpio"
    meta["git_remote"]     = run_get(["git", "-C", REPO, "remote", "-v"])
    meta["allow_dirty"]    = str(allow_dirty)
    meta["isaac_image"]    = ISAAC_IMAGE
    meta["isaac_image_id"] = run_get(
        f"docker image inspect {ISAAC_IMAGE} --format '{{{{.Id}}}}'", shell=True)
    meta["container"]      = CONTAINER
    meta["container_inspect"] = run_get(
        f"docker inspect {CONTAINER} --format "
        f"'image={{{{.Config.Image}}}} network={{{{.HostConfig.NetworkMode}}}} "
        f"mounts={{{{range .Mounts}}}}{{{{.Source}}}}->{{{{.Destination}}}} {{{{end}}}}'",
        shell=True)
    meta["repo"]           = REPO

    with open(os.path.join(run_dir, "metadata.txt"), "w") as f:
        for k, v in meta.items():
            f.write(f"{k}: {v}\n")
    for k, v in meta.items():
        log(f"  {k}: {v}")

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-dirty", action="store_true",
                        help="Permite correr con repo sucio (WARN, no FAIL)")
    args = parser.parse_args()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(RUNS_BASE, ts)
    os.makedirs(run_dir, exist_ok=True)

    set_logfile(os.path.join(run_dir, "launcher.log"))
    log(f"Run directory: {run_dir}")

    # ── Preflight ─────────────────────────────────────────────────────────────
    if not preflight(args.allow_dirty):
        log("FAIL: preflight no pasó. Abortando antes de lanzar Isaac.")
        sys.exit(1)

    # ── Metadata ──────────────────────────────────────────────────────────────
    save_metadata(run_dir, args.allow_dirty)

    # ── Lanzar Isaac ──────────────────────────────────────────────────────────
    isaac_log = os.path.join(run_dir, "A_isaac.log")
    log("=== LANZANDO ISAAC (Terminal A) ===")
    with open(isaac_log, "w") as lf:
        isaac_proc = subprocess.Popen(isaac_cmd(), stdout=lf, stderr=lf)
    log(f"Isaac PID: {isaac_proc.pid}")

    # ── Esperar señal objetiva ────────────────────────────────────────────────
    log(f"Esperando '{ISAAC_SIGNAL}' (timeout {ISAAC_TIMEOUT_S}s)...")
    found = tail_file_for_signal(isaac_log, ISAAC_SIGNAL, ISAAC_TIMEOUT_S)

    if not found:
        log(f"FAIL: señal no apareció en {ISAAC_TIMEOUT_S}s.")
        teardown_proc("isaac", isaac_proc)
        sys.exit(1)

    # Isaac alive check inmediato tras marker
    if isaac_proc.poll() is not None:
        log(f"FAIL: Isaac murió tras emitir marker (exit={isaac_proc.returncode}).")
        sys.exit(1)
    log("Isaac vivo tras marker. Lanzando B/C/D...")

    # ── Lanzar B/C/D ─────────────────────────────────────────────────────────
    log("=== LANZANDO B/C/D ===")
    procs = {}
    procs["observer"] = launch_ros2(
        "observer",
        f"{ros2_env()} && ros2 run cross_consistency_observer cross_consistency_observer --ros-args -r /imu:=/g1/imu",
        os.path.join(run_dir, "B_observer.log"))
    procs["watchdog"] = launch_ros2(
        "watchdog",
        f"{ros2_env()} && ros2 run watchdog_g1 watchdog_g1",
        os.path.join(run_dir, "C_watchdog.log"))
    procs["recovery"] = launch_ros2(
        "recovery",
        f"{ros2_env()} && ros2 run recovery_g1 recovery_g1",
        os.path.join(run_dir, "D_recovery.log"))

    # ── Esperar startup y verificar ───────────────────────────────────────────
    log(f"Esperando {NODE_VERIFY_WAIT}s para startup de nodos...")
    time.sleep(NODE_VERIFY_WAIT)

    # Isaac sigue vivo tras lanzar B/C/D
    if isaac_proc.poll() is not None:
        log(f"FAIL: Isaac murió durante startup de B/C/D (exit={isaac_proc.returncode}).")
        for n, p in procs.items():
            teardown_proc(n, p)
        sys.exit(1)

    # Verificar nodos
    log("=== VERIFICACIÓN DE NODOS ===")
    node_list = run_get(
        f"docker exec {CONTAINER} bash -c "
        f"'{ros2_env()} && ros2 node list 2>/dev/null'",
        shell=True
    )
    nodes_ok = True
    for node in EXPECTED_NODES:
        if node in node_list:
            log(f"  NODO OK: {node}")
        else:
            log(f"  NODO FALTANTE: {node}")
            nodes_ok = False

    # Verificar topics
    log("=== VERIFICACIÓN DE TOPICS ===")
    topic_list = run_get(
        f"docker exec {CONTAINER} bash -c "
        f"'{ros2_env()} && ros2 topic list 2>/dev/null'",
        shell=True
    )
    topics_ok = True
    for topic in EXPECTED_TOPICS:
        if topic in topic_list:
            log(f"  TOPIC OK: {topic}")
        else:
            log(f"  TOPIC FALTANTE: {topic}")
            topics_ok = False

    # Verificar procesos vivos
    log("=== VERIFICACIÓN DE PROCESOS ===")
    procs_ok = True
    for name, p in procs.items():
        if p.poll() is not None:
            log(f"  PROCESO MUERTO: {name} (exit={p.returncode})")
            procs_ok = False
        else:
            log(f"  PROCESO VIVO: {name}")

    # ── Resultado y ventana de corrida ────────────────────────────────────────
    isaac_ok = isaac_proc.poll() is None
    if not isaac_ok:
        log(f"  ISAAC MUERTO antes de declarar PASS (exit={isaac_proc.returncode})")
    launcher_pass = nodes_ok and topics_ok and procs_ok and isaac_ok
    log(f"\n{'='*50}")
    log(f"LAUNCHER {'PASS' if launcher_pass else 'FAIL'}")
    log(f"  nodos_ok={nodes_ok} topics_ok={topics_ok} procs_ok={procs_ok}")
    log(f"{'='*50}")

    if launcher_pass:
        log(f"Manteniendo pipeline activo {RUN_WINDOW_S}s...")
        time.sleep(RUN_WINDOW_S)
        # Verificar que nadie murió durante la ventana
        log("=== VERIFICACIÓN POST-VENTANA ===")
        if isaac_proc.poll() is not None:
            log(f"  FAIL: Isaac murió durante ventana (exit={isaac_proc.returncode})")
            launcher_pass = False
        else:
            log("  Isaac vivo post-ventana OK")
        for name, p in procs.items():
            if p.poll() is not None:
                log(f"  FAIL: {name} murió durante ventana (exit={p.returncode})")
                launcher_pass = False
            else:
                log(f"  {name} vivo post-ventana OK")

    # ── Teardown robusto ──────────────────────────────────────────────────────
    log("=== TEARDOWN ===")
    for name, p in procs.items():
        teardown_proc(name, p)
    teardown_proc("isaac", isaac_proc)

    log(f"Logs en: {run_dir}")
    sys.exit(0 if launcher_pass else 1)

if __name__ == "__main__":
    main()
