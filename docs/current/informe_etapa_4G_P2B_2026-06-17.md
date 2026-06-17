# Informe de Sesión — Etapa 4G (P2-B)
## G1 Deterministic Safety Runtime
**Fecha:** 2026-06-17
**Estado al cierre:**
- **4G-P2-B ✅ CERRADA (PASS parcial con hallazgo arquitectónico)** — ruta directa observer→recovery reproducible N=10, 100% PASS. Ruta gobernada bloqueada por contrato event_type — deuda TX-011.

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla
**Referencia previa:** `informe_etapa_4G_parcial_2026-06-17.md` (P0+P1+P2-A)
**Commits de sesión:**
- `497f0a4` — 4G-P2-B: RUN_WINDOW_S 30→90 para capturar FALL_TRIGGER it=450
- `86a32c6` — 4G-P2-B: Terminal E safety_orchestrator_g1 en launcher + verif nodos/topics ruta gobernada

**Repositorio:** `~/g1-deterministic-safety-runtime` | `origin/main` synced `86a32c6`
**Contenedor:** `boring_noether` activo, `/ws` → repo nuevo

---

## 0. Resumen Ejecutivo

Esta sesión ejecutó la microfase 4G-P2-B: reproducibilidad de caída inducida con cadena safety completa.

**Hallazgo principal:** la ruta directa `observer → /safety_events → recovery` funciona de forma reproducible (N=10, 100% PASS, latencia 1–156ms). La ruta gobernada `observer → orchestrator → /system_state → recovery` no opera porque el orchestrator no tiene transición para el contrato `SECONDARY + CONDITION_DETECTED`. Esto es deuda arquitectónica formal, no bug de infraestructura.

**Proceso de la sesión:**
1. Diagnóstico del tiempo de caída: it=450 a t=54.67s desde baseline, medido en logs históricos.
2. Ajuste de `RUN_WINDOW_S` de 30→90 para capturar la caída en ventana.
3. Piloto P2-B inicial (sin orchestrator): caída detectada, recovery reaccionó por FREEZE del watchdog (14s después). Cadena incompleta.
4. Adición de Terminal E (orchestrator) al launcher: 4 nodos + 8 topics verificados.
5. Piloto P2-B extendido: observer detecta caída CRITICAL, recovery reacciona directo (3-59ms). Orchestrator silencioso.
6. Diagnóstico del orchestrator: mismatch doble — `event_type=CONDITION_DETECTED` vs TX esperan `STABILITY_ANOMALY`; `source_authority=SECONDARY` vs TX-001 exige `PRIMARY_IMU/PRIMARY_JOINT_STATES`.
7. Decisión: no parchear. Opción C — ruta directa válida, deuda TX-011 documentada formalmente.
8. N=10 corridas formales: 100% PASS. 4 corridas INVALID/INFRA por timeout de nodos ROS2 (contenedor 7h+ activo) — resuelto reiniciando `boring_noether`.

---

## 1. Dimensionamiento de Ventana

### 1.1 Evidencia histórica
Log `~/runs/4d3c2b/p4g_A_falltest.log`:
```
it=1   → t=0.00s
it=449 → t=54.55s
it=450 → t=54.67s  ← FALL TRIGGER
```
Tasa: ~8.2 it/s, lineal y estable. Caída determinista por iteración y por tiempo.

### 1.2 Cálculo
- Launcher entra a ventana ~13s después del marker SET (t_bcd)
- Caída ocurre a ~42s dentro de la ventana
- Margen post-evento (latch + recovery + secundarios): +35s
- **`RUN_WINDOW_S = 90`** — cubre todo con holgura

---

## 2. Arquitectura del Launcher P2-B

### 2.1 Cambios respecto a P2-A
| Parámetro | P2-A | P2-B |
|---|---|---|
| `RUN_WINDOW_S` | 30s | 90s |
| Terminal E orchestrator | ❌ | ✅ |
| Nodos verificados | 3 | 4 |
| Topics verificados | 6 | 8 |

### 2.2 Nuevos topics verificados
- `/system_state` — publicado por orchestrator
- `/safety_actions` — publicado por orchestrator

### 2.3 Nodos verificados
- `/cross_consistency_observer`
- `/watchdog_g1`
- `/recovery_g1`
- `/safety_orchestrator_g1` ← nuevo

---

## 3. Diagnóstico del Orchestrator — Hallazgo Arquitectónico

### 3.1 Investigación
| Hipótesis | Verificación | Resultado |
|---|---|---|
| QoS mismatch | Sub usa `reliable_qos` igual que publisher | ❌ Descartada |
| Filtro por authority | Callback no filtra — solo descarta `SELF_SOURCE` | ❌ Descartada |
| No loguea a stdout | ACK va a `/safety_events` (topic), no a logger | ✅ Confirmada (caso C) |
| Mismatch event_type | Observer emite `CONDITION_DETECTED`; TX-001 espera `STABILITY_ANOMALY` | ✅ Confirmada |
| Mismatch source_authority | Observer emite `SECONDARY`; TX-001 exige `PRIMARY_IMU/PRIMARY_JOINT_STATES` | ✅ Confirmada |

### 3.2 Contrato real
```python
# Observer emite (línea 370):
msg.event_type = 'CONDITION_DETECTED'
msg.source_authority = 'SECONDARY'

# TX-001 requiere:
event_type in ('STABILITY_ANOMALY', 'JOINT_OSCILLATION', 'IMU_OUT_OF_RANGE')
source_authority in ('PRIMARY_IMU', 'PRIMARY_JOINT_STATES')
```
Doble mismatch → evaluador retorna None → no hay transición → no hay `/system_state` → no hay escalación gobernada.

### 3.3 El orchestrator SÍ funciona
- Recibe el evento (reliable QoS, sin filtro)
- Publica ACK `SCHEDULED` a `/safety_events`
- El ACK no aparece en stdout — por eso `E_orchestrator.log` parecía mudo

### 3.4 Opciones evaluadas
| Opción | Descripción | Decisión |
|---|---|---|
| A | Elevar observer a `PRIMARY_IMU` | ❌ Semánticamente incorrecto |
| B | Nueva TX-011 para `SECONDARY + STABILITY_ANOMALY/fallen` | 🔲 Deuda formal — 4G-P2-C |
| C | Ruta directa válida, ruta gobernada como deuda | ✅ Aprobado para N≥10 |

---

## 4. Resultados N=10 — Corridas Formales P2-B

### 4.1 Tabla de corridas
| # | Corrida | FALL | OBS | REC | Válida |
|---|---|---|---|---|---|
| 1 | 20260617_145141 | ✅ | ✅ | ✅ | ✅ PASS |
| 2 | 20260617_151111 | ✅ | ✅ | ✅ | ✅ PASS |
| 3 | 20260617_154157 | ✅ | ✅ | ✅ | ✅ PASS |
| 4 | 20260617_154658 | ✅ | ✅ | ✅ | ✅ PASS |
| 5 | 20260617_154946 | ✅ | ✅ | ✅ | ✅ PASS |
| 6 | 20260617_155409 | ✅ | ✅ | ✅ | ✅ PASS |
| — | 20260617_155741 | ✅ | ❌ | ❌ | ❌ INVALID/INFRA |
| — | 20260617_160003 | ✅ | ❌ | ❌ | ❌ INVALID/INFRA |
| — | 20260617_160310 | ✅ | ❌ | ❌ | ❌ INVALID/INFRA |
| — | 20260617_160556 | ✅ | ❌ | ❌ | ❌ INVALID/INFRA |
| 7 | 20260617_161221 | ✅ | ✅ | ✅ | ✅ PASS |
| 8 | 20260617_161545 | ✅ | ✅ | ✅ | ✅ PASS |
| 9 | 20260617_161834 | ✅ | ✅ | ✅ | ✅ PASS |
| 10 | 20260617_162117 | ✅ | ✅ | ✅ | ✅ PASS |

**INVALID/INFRA:** 4 corridas con timeout de verificación de nodos ROS2 — contenedor activo 7h+ causó lentitud de registro. Resuelto reiniciando `boring_noether`. No son fallas de detección.

### 4.2 Estadística de latencia t1→t2 (ruta directa, `source=cross_consistency_observer`)
```
Rango observado: 1.3 – 156ms
Valores típicos: 3 – 60ms
Fuente: D_recovery.log, campo LATENCY t1→t2
Nota: t1 = timestamp ROS SafetyEvent REAL del observer
      t2 = timestamp ROS de recepción en recovery
      Correlación: por source, no por uuid (contrato uuid no trazable end-to-end)
```

### 4.3 Criterio PASS P2-B — cumplido
- N=10 corridas formales ✅
- FALL_TRIGGER it=450 en todas ✅
- Observer detecta caída en todas ✅
- Recovery reacciona por `source=cross_consistency_observer` en todas ✅
- PASS rate formal: 100% ✅
- Logs A/B/C/D/E + metadata preservados ✅
- Corridas INVALID/INFRA documentadas y excluidas con criterio explícito ✅

---

## 5. Qué Está Validado vs NO Validado

**Validado (con evidencia):**
- Caída inducida it=450: determinista, reproducible ✅
- Observer detecta caída CRITICAL (abs_w < 0.80, L/R False): 100% corridas ✅
- Ruta directa observer→recovery: latencia 1–156ms, reproducible ✅
- Orchestrator vivo y conectado: recibe eventos, publica ACK ✅
- Launcher 5 terminales: arranque ordenado, 4 nodos + 8 topics verificados ✅

**NO validado:**
- Ruta gobernada observer→orchestrator→recovery (TX-011 pendiente) ❌
- t0→t1 latencia física→observer (4G-P3 pendiente) ❌
- Correlación uuid t1→t2 (contrato no trazable aún) ❌
- Thresholds definitivos ❌

---

## 6. Adversidades y Correcciones

| # | Adversidad | Corrección |
|---|---|---|
| 1 | `RUN_WINDOW_S=30` no capturaba FALL_TRIGGER it=450 | Medir t=54.67s en logs históricos → `RUN_WINDOW_S=90` |
| 2 | Piloto sin orchestrator: recovery reaccionó por FREEZE 14s tarde | Añadir Terminal E al launcher |
| 3 | `E_orchestrator.log` mudo — parecía no procesar | ACK va al topic, no stdout — confirmado en código |
| 4 | Mismatch doble event_type + source_authority | No parchear — deuda TX-011 documentada |
| 5 | 4 corridas INVALID/INFRA por timeout nodos ROS2 | Reiniciar `boring_noether` |
| 6 | Cambio `CONDITION_DETECTED→STABILITY_ANOMALY` propuesto y revertido | TX-001 también exige PRIMARY — cambio incompleto, revertido limpio |

---

## 7. Deuda Técnica Activa

| ID | Deuda | Prioridad |
|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta |
| DT-4E-006 | Control PD diferido | Alta |
| DT-4F-001 | Thresholds pragmáticos | Media |
| DT-4F-002 | TX-006b/c sin test explícito | Media |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media |
| DT-4F-005 | t0→t1 no medido | Alta |
| **DT-4G-001** | **TX-011: escalación gobernada SECONDARY/fallen pendiente** | **Alta** |

---

## 8. Estado de la VM al Cierre

```
Repo activo    → ~/g1-deterministic-safety-runtime (main, origin synced 86a32c6)
Contenedor     → boring_noether activo (reiniciado al final de sesión)
Logs 4G        → ~/runs/4G/ (corridas P2-A + P2-B)
Launcher       → sim_runtime/4G/launch_pipeline.py (RUN_WINDOW_S=90, Terminal E)
CI             → Build ✅ Audit ✅
```

---

## 9. Próximos Pasos

1. **4G-P2-C** — TX-011: escalación gobernada para SECONDARY/fallen. Diseño antes de implementar.
2. **4G-P3** — t0→t1 clock sync Isaac↔ROS2.
3. **4H-P1** — Recovery inteligente.
4. **4I-P1** — Recrear SAFETY_MODEL_G1.md (DT-4E-001).

---

## LLAVE DEL SIGUIENTE CHAT

```
4G-P2-B ✅ CERRADA (PASS parcial):
  Ruta directa observer→recovery: N=10, 100% PASS, latencia 1–156ms.
  Ruta gobernada: BLOQUEADA — mismatch doble:
    observer: event_type=CONDITION_DETECTED, source_authority=SECONDARY
    TX-001 exige: STABILITY_ANOMALY + PRIMARY_IMU/PRIMARY_JOINT_STATES
  Deuda formal: DT-4G-001 / TX-011.

REPO: ~/g1-deterministic-safety-runtime (main, 86a32c6)
CONTENEDOR: boring_noether activo (reiniciado)
LAUNCHER: sim_runtime/4G/launch_pipeline.py
  RUN_WINDOW_S=90, Terminal E orchestrator, 4 nodos, 8 topics
CORRIDAS FORMALES: ~/runs/4G/ (145141–162117, N=10 PASS)
INVALID/INFRA: 155741, 160003, 160310, 160556 (timeout nodos, no falla detección)

PRÓXIMO: 4G-P2-C — TX-011 diseño antes de implementar
         Opciones: B (nueva TX para SECONDARY/STABILITY_ANOMALY/fallen)
         No tocar observer/orchestrator sin diseño aprobado por PM

DEUDAS CLAVE: DT-4G-001 (TX-011), DT-4E-001, DT-4E-006, DT-4F-005
```

---

*G1 Deterministic Safety Runtime — Informe Cierre 4G-P2-B*
*Generado: 2026-06-17*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
