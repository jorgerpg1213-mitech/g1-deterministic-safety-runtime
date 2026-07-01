# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 27 — Actualizada 2026-06-25 (4J-P4-A y P4-B CERRADAS)

> **Cambios v27 vs v26:**
> - **4J-P4-A CERRADA**: Threshold Inventory. 20+ constantes extraídas. H1–H5 documentados. `docs/audit/4J_THRESHOLD_CHARACTERIZATION.md` commitado.
> - **4J-P4-B CERRADA**: Negative Control PASS. 0 critical SafetyEvents, 0 terminal RecoveryEvents, 60s observación formal. Commit `04d3983`.
> - **Topología IMU dual confirmada**: watchdog_g1 suscribe `/g1/imu`; observer suscribe `/imu`. Harnesses deben publicar en ambos.
> - **run_p4b.sh**: launcher controlado con preflight, trap cleanup, time guard, cleanliness gate, postflight.
> - **DT-4G-004B confirmada**: postflight residual nodes — mitigation: `docker restart` antes de batería formal.
> - HEAD: `04d3983` — CI Build ✅ CI Audit ✅

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         ✅ CERRADA
Etapa 4H  — Recovery Inteligente                       ✅ CERRADA
Etapa 4I  — Formalización                              ✅ CERRADA
Etapa 4J  — Paper Prep                                 🔄 EN PROGRESO
  4J-P0 Runtime Alignment / cierre DT-4I-001           ✅ CERRADA
  4J-P1 Causal Traceability (minimum)                  ✅ CERRADA
  4J-P2-prep Direct path traceability                  ✅ CERRADA
  4J-P2-A Extended Fault Injection Matrix               ✅ CERRADA
  4J-P3 Timing Traceability Report                     ✅ CERRADA
  4J-P4-A Threshold Inventory                          ✅ CERRADA
  4J-P4-B Negative Control                             ✅ CERRADA
  4J-P4-C Positive Controls                            🔲 PENDIENTE
  4J-P4-D/E/F Boundary / False Positive / Report       🔲 PENDIENTE
  4J-P5 Assurance Case + Paper Package                 🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**HEAD:** `04d3983` (post-4J-P4-B) — CI Build ✅ CI Audit ✅
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4J-P4-B ✅. Próximo: 4J-P4-C — Positive Controls.**

**Acción inmediata al inicio de P4-C:**
1. Leer documento PM para P4-C antes de diseñar nada
2. No tocar runtime
3. No asumir scope — esperar documento PM

---

# HALLAZGOS CLAVE P4-A (Threshold Inventory)

| Familia | Constante | Valor | Línea | Evidence |
|---|---|---|---|---|
| F1 Observer CRITICAL | FALLEN_W_CRITICAL | 0.80 | L80 | E3 |
| F1 Observer WARN | FALLEN_W_WARN | 0.85 | L81 | E1 |
| F2 debounce | FALLEN_CONSECUTIVE_N | 3 samples | L82 | E3 |
| F2 freshness | FRESH_MAX_AGE_S | 0.5s | L78 | E1 |
| F3 STALE onset | STALE_TIMEOUT_S | 1.0s | L39 | E4 |
| F3 STALE critical | STALE_CRITICAL_S | 3.0s | L40 | E3 |
| F3 grace | STARTUP_GRACE_S | 15.0s | L45 | E1 |
| F4 FREEZE | FREEZE_N | 5 samples | L41 | E4 |
| F7 RATE | MIN_RATE_HZ | 3.0 Hz | L42 | E2 |
| Recovery retry | MAX_AUTO_RETRIES | 3 | L50 | E4 |
| Recovery cooldown | RETRY_COOLDOWN_S | 5.0s | L51 | E4 |

**Hallazgos estructurales:**
- H1: WARN/INFO del observer nunca publican SafetyEvent (solo CRITICAL con N≥3 consecutivos)
- H2: FALLEN_CONSECUTIVE_N=3 es gate de debounce exclusivo de CRITICAL
- H3: Observer emite STABILITY_RISK+NONE hardcodeados — severidad interna no se propaga
- H4: STALE tiene dos caminos de severidad con evidencia asimétrica (E4 vs E3)
- H5: WAIT_FOR_PRIMARY_MAX_S=30s nunca alcanzado experimentalmente (E1)

---

# RESULTADO P4-B (Negative Control)

```
verdict:  PASS
topology: /g1/imu→watchdog ✓ | /imu→observer ✓ | /safety_events ✓ | /recovery_events ✓
Phase 3:  60s observación formal
critical_risk SafetyEvents:  0
terminal RecoveryEvents:     0
Limitación: postflight residual nodes → DT-4G-004B
            frozen-sensor FREEZE false positive → diferido a P4-E
```

---

# TOPOLOGÍA IMU DUAL — CRÍTICO PARA HARNESSES FUTUROS

```
watchdog_g1               suscribe /g1/imu
cross_consistency_observer suscribe /imu  (NO /g1/imu)
```

Todo harness que quiera alimentar ambos nodos DEBE publicar en `/g1/imu` Y `/imu`.
El mismo mensaje puede enviarse a ambos topics (mismo estado físico).

---

# CAMINO OPERATIVO CONFIRMADO

## Launcher unificado P4-B
```bash
docker restart boring_noether && sleep 3 && \
cd ~/g1-deterministic-safety-runtime && bash sim_runtime/4J/run_p4b.sh
```

## Launcher unificado general (con Isaac)
```bash
cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py 2>&1 | tee /tmp/<fase>_run.log
```

---

# Contenedor boring_noether — estado confirmado

```
Imagen:       g1-ros-phase-b:humble
Network:      host
/ws mount:    ~/g1-deterministic-safety-runtime
fastdds:      sim_runtime/common/fastdds_udp.xml
Build:        sin --symlink-install
Estado:       activo
Paquetes:     cross_consistency_observer, g1_msgs, recovery_g1,
              safety_orchestrator_g1, watchdog_g1 — todos operativos
```

**NOTA DT-4G-004B:** postflight residual nodes confirmado en P4-B. Mitigation: `docker restart boring_noether` antes de cada batería formal.
**NOTA anti-pattern #83:** harnesses deben publicar en `/g1/imu` Y `/imu` — watchdog y observer suscriben a topics distintos.

---

# Deuda Técnica Activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Partially characterized — P4-A inventory; boundary sweep pendiente P4-D |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Characterized (P4-A); diferido a P4-E |
| DT-4G-002 | t1→t2 UUID paper-grade | Media | Parcial — 4J-P1 |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta, confirmada en P4-B |
| DT-4J-001 | Full native traceability | Media | Abierta |

---

# Anti-Patterns Acumulados (selección)

| # | Anti-pattern | Corrección |
|---|---|---|
| 54 | Reconstruir docker run de memoria | Usar comando confirmado en bootstrap |
| 63 | No verificar sintaxis antes de copiar al contenedor | ast.parse antes de docker cp |
| 74 | Correr harness antes de que subscriber esté activo | Topology check con NAME_SETTLE_S |
| 78 | Correr harness contra nodo con uptime largo sin verificar retry state | docker restart antes de batería formal |
| 79 | Asignar método logger dinámicamente en ROS2 | if/else explícito en callbacks |
| 80 | Asumir campo de mensaje sin verificar .msg file | cat g1_msgs/msg/RecoveryEvent.msg primero |
| 81 | kill $PID no mata procesos dentro del contenedor | docker exec pkill -f 'ros2 launch' |
| 82 | clear_observation() no resetea estado del runtime | Gate de limpieza pre-Phase-3 |
| 83 | Publicar solo /g1/imu asumiendo que observer también lo recibe | Publicar en /g1/imu Y /imu |

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v27*
*Actualizado: 2026-06-25*
*4E ✅ | 4F ✅ | 4G ✅ | 4H ✅ | 4I ✅ | 4J 🔄 (P0✅ P1✅ P2-prep✅ P2-A✅ P3✅ P4-A✅ P4-B✅) | 5A 🔒*
