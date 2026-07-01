#!/bin/bash
# run_p4b.sh — P4-B controlled launcher
# Orden garantizado:
#   1. Preflight: verificar entorno limpio
#   2. Arrancar los 4 nodos runtime en background
#   3. Sleep 8s — DDS settle + nodos suscritos a topics
#   4. Lanzar harness (publica desde tick=0; watchdog grace=15s aún activo)
#   5. trap cleanup EXIT — limpieza garantizada aunque harness falle
#
# Uso: cd ~/g1-deterministic-safety-runtime && bash sim_runtime/4J/run_p4b.sh
# Logs nodos: /tmp/p4b_*.log  |  Harness: /tmp/p4b_harness.log

set -euo pipefail

SOURCE="source /opt/ros/humble/setup.bash && source /ws/install/setup.bash"
WS=/ws
SETTLE_S=8   # tiempo para que DDS resuelva suscripciones antes de lanzar harness

# ── Cleanup garantizado al salir (EXIT, error, Ctrl+C) ─────────────────────
cleanup() {
    echo "[run_p4b] cleanup — deteniendo nodos background..."
    kill "${PID_REC:-}" "${PID_ORC:-}" "${PID_OBS:-}" "${PID_WDG:-}" 2>/dev/null || true
    wait "${PID_REC:-}" "${PID_ORC:-}" "${PID_OBS:-}" "${PID_WDG:-}" 2>/dev/null || true
    # Container-side cleanup: kill ROS2 child processes that survive host-side kill
    docker exec boring_noether bash -c         "pkill -f 'ros2 launch' 2>/dev/null || true; pkill -f 'ros2 run' 2>/dev/null || true" || true
    sleep 2
    echo "[run_p4b] cleanup done."
    # Postflight: verificar que no quedaron nodos vivos
    sleep 2
    REMAINING=$(docker exec boring_noether bash -c \
        "$SOURCE && ros2 node list 2>/dev/null" 2>/dev/null | wc -l || echo "0")
    if [ "$REMAINING" -gt 0 ]; then
        echo "[run_p4b] POSTFLIGHT WARN: $REMAINING nodo(s) residual(es) detectado(s)."
        echo "[run_p4b] Entorno contaminado — ejecutar: docker restart boring_noether antes del siguiente run."
    else
        echo "[run_p4b] POSTFLIGHT OK — entorno limpio."
    fi
}
trap cleanup EXIT

# ── Preflight: verificar entorno limpio ────────────────────────────────────
echo "[run_p4b] === PREFLIGHT ==="
NODE_COUNT=$(docker exec boring_noether bash -c \
    "$SOURCE && ros2 node list 2>/dev/null" | wc -l)
if [ "$NODE_COUNT" -gt 0 ]; then
    echo "[run_p4b] PREFLIGHT FAIL: $NODE_COUNT nodos activos. Ejecuta: docker restart boring_noether"
    exit 1
fi
echo "[run_p4b] PREFLIGHT OK — contenedor limpio."

# ── Limpiar logs previos ───────────────────────────────────────────────────
rm -f /tmp/p4b_recovery.log /tmp/p4b_watchdog.log \
      /tmp/p4b_observer.log /tmp/p4b_orchestrator.log /tmp/p4b_harness.log

# ── Paso 1: arrancar nodos runtime en background ──────────────────────────
echo "[run_p4b] Paso 1: lanzando recovery_g1..."
docker exec boring_noether bash -c \
    "$SOURCE && cd $WS && ros2 launch recovery_g1 recovery_g1.launch.py" \
    > /tmp/p4b_recovery.log 2>&1 &
PID_REC=$!

echo "[run_p4b] Paso 2: lanzando safety_orchestrator_g1..."
docker exec boring_noether bash -c \
    "$SOURCE && cd $WS && ros2 launch safety_orchestrator_g1 safety_orchestrator_g1.launch.py" \
    > /tmp/p4b_orchestrator.log 2>&1 &
PID_ORC=$!

echo "[run_p4b] Paso 3: lanzando cross_consistency_observer..."
docker exec boring_noether bash -c \
    "$SOURCE && cd $WS && ros2 launch cross_consistency_observer cross_consistency_observer.launch.py" \
    > /tmp/p4b_observer.log 2>&1 &
PID_OBS=$!

echo "[run_p4b] Paso 4: lanzando watchdog_g1 (grace=15s)..."
WATCHDOG_START=$SECONDS
docker exec boring_noether bash -c \
    "$SOURCE && cd $WS && ros2 launch watchdog_g1 watchdog_g1.launch.py" \
    > /tmp/p4b_watchdog.log 2>&1 &
PID_WDG=$!

# ── Paso 5: esperar DDS settle antes de lanzar harness ────────────────────
echo "[run_p4b] Paso 5: DDS settle ${SETTLE_S}s (nodos suscritos a topics; harness debe arrancar antes de 12s desde watchdog)"
sleep $SETTLE_S

# ── Guard: harness debe arrancar bien dentro del grace period ─────────────
ELAPSED=$(( SECONDS - WATCHDOG_START ))
echo "[run_p4b] Tiempo desde watchdog launch: ${ELAPSED}s (grace=15s, límite=12s)"
if [ "$ELAPSED" -ge 12 ]; then
    echo "[run_p4b] FAIL: harness arrancaría demasiado tarde en grace window (${ELAPSED}s >= 12s)."
    echo "[run_p4b] Posible lag Docker. Abortando — correr docker restart y reintentar."
    exit 1
fi

# ── Paso 6: lanzar harness (foreground, tee a log) ────────────────────────
# Harness publica desde tick=0 → watchdog grace=15s aún activo
# check_topology a t=settle+3s → todos los nodos ya suscritos
echo "[run_p4b] Paso 6: lanzando harness P4-B..."
echo "[run_p4b] Grace watchdog=15s | Settle=${SETTLE_S}s | Harness startup ya dentro de grace."
docker exec boring_noether bash -c \
    "$SOURCE && cd $WS && python3 sim_runtime/4J/harness_4J_P4B_negative_control.py" \
    2>&1 | tee /tmp/p4b_harness.log

echo "[run_p4b] === P4-B run complete. Logs en /tmp/p4b_*.log ==="
