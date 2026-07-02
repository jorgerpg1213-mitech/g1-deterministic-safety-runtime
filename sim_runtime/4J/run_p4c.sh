#!/bin/bash
# G1 Deterministic Safety Runtime — 4J-P4-C Positive Controls Launcher
# Timing pattern tomado de run_p4b.sh:
#   harness arranca DENTRO de STARTUP_GRACE_S=15s para que publishers
#   estén vivos antes de que watchdog evalúe por primera vez.

set -euo pipefail

CASE="${1:-}"
RUN_ID="${2:-1}"
DRY_FLAG="${3:-}"
CONTAINER="boring_noether"
WS="/ws"
SOURCE="source /opt/ros/humble/setup.bash && source ${WS}/install/setup.bash"
EVIDENCE_BASE="${WS}/evidence/4J/P4_THRESHOLDS/positive_controls"
LOG_DIR="/tmp/p4c_logs"
TS=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/p4c_${CASE}_run${RUN_ID}_${TS}.log"

VALID="stale freeze naninf timestamp fallen rate"
if [[ -z "${CASE}" ]] || ! echo "${VALID}" | grep -qw "${CASE}"; then
    echo "[run_p4c] ERROR: caso requerido. Válidos: ${VALID}"
    echo "Uso: bash run_p4c.sh <case> <run_id> [--dry-run]"
    exit 1
fi

mkdir -p "${LOG_DIR}"

# ---- TRAP cleanup EXIT ----
cleanup() {
    echo "[run_p4c] cleanup: killing runtime nodes"
    docker exec "${CONTAINER}" bash -c \
        "pkill -f 'ros2 launch' 2>/dev/null || true; \
         pkill -f 'ros2 run'    2>/dev/null || true" || true
    sleep 2
    REMAINING=$(docker exec "${CONTAINER}" bash -c \
        "${SOURCE} && ros2 node list 2>/dev/null | grep -v '<defunct>' | wc -l" \
        2>/dev/null || echo "0")
    if [[ "${REMAINING}" -gt 0 ]]; then
        echo "[run_p4c] POSTFLIGHT WARN: ${REMAINING} nodo(s) residual(es)"
    else
        echo "[run_p4c] postflight OK — 0 residual nodes"
    fi
}
trap cleanup EXIT

echo "============================================================"
echo "[run_p4c] 4J-P4-C Positive Controls"
echo "[run_p4c] case=${CASE}  run_id=${RUN_ID}  ts=${TS}"
[[ "${DRY_FLAG}" == "--dry-run" ]] && echo "[run_p4c] MODE: DRY-RUN"
echo "============================================================"

# ---- STEP 1: docker restart ----
echo ""
echo "[run_p4c] STEP 1: docker restart ${CONTAINER}"
docker restart "${CONTAINER}"
sleep 4

# ---- STEP 2: Preflight ----
echo ""
echo "[run_p4c] STEP 2: preflight — residual node check"
RESIDUAL=$(docker exec "${CONTAINER}" bash -c \
    "${SOURCE} && ros2 node list 2>/dev/null | grep -v '<defunct>' | wc -l" \
    2>/dev/null || echo "0")
if [[ "${RESIDUAL}" -gt 0 ]]; then
    echo "[run_p4c] INVALID: ${RESIDUAL} residual nodes"
    exit 2
fi
echo "[run_p4c] preflight OK — 0 residual nodes"

# ---- STEP 3: Launch 4 nodos (watchdog último — patrón P4-B) ----
echo ""
echo "[run_p4c] STEP 3: launching runtime nodes"

docker exec "${CONTAINER}" bash -c \
    "${SOURCE} && cd ${WS} && ros2 launch recovery_g1 recovery_g1.launch.py" \
    > /tmp/p4c_recovery_${TS}.log 2>&1 &

docker exec "${CONTAINER}" bash -c \
    "${SOURCE} && cd ${WS} && ros2 launch safety_orchestrator_g1 safety_orchestrator_g1.launch.py" \
    > /tmp/p4c_orchestrator_${TS}.log 2>&1 &

docker exec "${CONTAINER}" bash -c \
    "${SOURCE} && cd ${WS} && ros2 launch cross_consistency_observer cross_consistency_observer.launch.py" \
    > /tmp/p4c_observer_${TS}.log 2>&1 &

# Watchdog último — timestamp para time guard
docker exec "${CONTAINER}" bash -c \
    "${SOURCE} && cd ${WS} && ros2 launch watchdog_g1 watchdog_g1.launch.py" \
    > /tmp/p4c_watchdog_${TS}.log 2>&1 &

WATCHDOG_LAUNCH_TS=$(date +%s)
echo "[run_p4c] watchdog launched at ${WATCHDOG_LAUNCH_TS}"

# Settle dentro de grace window — NO esperar hasta que expire
echo "[run_p4c] waiting 8s (settle inside STARTUP_GRACE_S=15)"
sleep 8

# ---- STEP 4: Topology check ----
echo ""
echo "[run_p4c] STEP 4: topology check"
NODES=$(docker exec "${CONTAINER}" bash -c \
    "${SOURCE} && ros2 node list 2>/dev/null" || echo "")

REQUIRED="watchdog_g1 cross_consistency_observer safety_orchestrator_g1 recovery_g1"
TOPO_OK=1
for node in ${REQUIRED}; do
    if echo "${NODES}" | grep -q "${node}"; then
        echo "[run_p4c]   ✓ ${node}"
    else
        echo "[run_p4c]   ✗ ${node} NOT FOUND"
        TOPO_OK=0
    fi
done

if [[ "${TOPO_OK}" -eq 0 ]]; then
    echo "[run_p4c] INVALID: topology incomplete — abort"
    exit 2
fi
echo "[run_p4c] topology OK"

# ---- STEP 5: Time guard (patrón P4-B) ----
echo ""
ELAPSED=$(( $(date +%s) - WATCHDOG_LAUNCH_TS ))
echo "[run_p4c] tiempo desde watchdog launch: ${ELAPSED}s (grace=15s, límite=12s)"
if [[ "${ELAPSED}" -ge 12 ]]; then
    echo "[run_p4c] INVALID: harness arrancaría demasiado tarde (${ELAPSED}s >= 12s)"
    echo "[run_p4c] Posible lag Docker. Correr docker restart y reintentar."
    exit 2
fi
echo "[run_p4c] time guard OK — harness arranca dentro de grace window"

# ---- STEP 6: Run harness ----
echo ""
echo "[run_p4c] STEP 6: harness case=${CASE} run_id=${RUN_ID}"
CMD="${SOURCE} && cd ${WS} && \
     python3 sim_runtime/4J/harness_4J_P4C_positive_controls.py \
         --case ${CASE} --run-id ${RUN_ID} \
         --output-dir ${EVIDENCE_BASE}"
[[ "${DRY_FLAG}" == "--dry-run" ]] && CMD="${CMD} --dry-run"

docker exec "${CONTAINER}" bash -c "${CMD}" 2>&1 | tee "${LOG_FILE}"

# ---- STEP 7: Summary ----
echo ""
SUMMARY="${EVIDENCE_BASE}/${CASE}/p4c_${CASE}_run${RUN_ID}.json"
if docker exec "${CONTAINER}" test -f "${SUMMARY}" 2>/dev/null; then
    echo "[run_p4c] summary:"
    docker exec "${CONTAINER}" cat "${SUMMARY}"
else
    echo "[run_p4c] WARNING: summary not found at ${SUMMARY}"
fi

echo ""
echo "============================================================"
echo "[run_p4c] DONE  case=${CASE}  run_id=${RUN_ID}"
echo "============================================================"
# trap cleanup se ejecuta aquí automáticamente
