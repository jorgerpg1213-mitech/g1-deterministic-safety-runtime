# Etapa 4I — Formalización del Modelo de Seguridad G1
## Análisis y Desglose de Microfases
**Preparado:** 2026-06-19 | Post-cierre 4H

---

## Por qué existe 4I

Hasta 4H el proyecto construyó y endureció el runtime con disciplina experimental:

- **4E:** baseline sano del G1 en Isaac Sim.
- **4F:** observer, watchdog, orchestrator y recovery enriquecidos; TX-001→TX-011 trazadas.
- **4G:** pipeline reproducible, launcher unificado, teardown activo, latencias medidas, rutas gobernadas validadas.
- **4H:** recovery inteligente por causa; política causal mínima con bypass terminal.

Lo que existe al cierre de 4H es un sistema que **funciona y está demostrado por logs**. Lo que aún no existe es un sistema cuyo **contrato de seguridad esté declarado explícitamente**, con estados, transiciones, evidencias y límites formalizados en un único documento auditable.

4I cierra ese gap. No agrega comportamiento nuevo. Convierte lo validado en un modelo defendible.

---

## La pregunta técnica de 4I

> ¿El modelo de seguridad declarado coincide con el código real, las transiciones TX-001→TX-011 y la evidencia validada 4E→4H?

Esta es la puerta de entrada correcta. Antes de paper prep, antes de assurance case, antes de fault injection extendida — el contrato debe existir por escrito y ser coherente con el sistema real.

---

## Qué NO hace 4I

4I es una etapa de formalización documental auditada contra código y evidencia; no es una etapa de experimentación ni de comportamiento nuevo. Está **prohibido** en 4I:

- Tocar PD control o thresholds reales.
- Correr N formal por causa.
- Modificar watchdog internals, mensajes ROS2 o launcher.
- Abrir Isaac o hacer corridas físicas.
- Resolver DT-4G-004B (zombies PID1).
- Calibración experimental de FREEZE IMU false positive.
- Rediseñar recovery o orchestrator.

Si la auditoría de 4I-P1 encuentra un gap de código pequeño (no de formalización), se declara como deuda y se cierra en microfase separada con aprobación del PM — no se desvía 4I.

---

## Arquitectura de Responsabilidades — Contrato a Formalizar en 4I

Este es el modelo conceptual central que 4I debe dejar escrito como contrato explícito. No es nuevo — ya existe en el código. 4I lo saca del código y lo convierte en documento auditable.

### Separación semántica de componentes

| Componente | Dominio | Aplica cuando… | Ejemplo |
|---|---|---|---|
| `cross_consistency_observer` | Coherencia física | El estado físico del robot no cuadra — caída, pérdida de soporte, IMU/contactos inconsistentes | caída → `abs(q.w) < 0.80` sostenida |
| `watchdog_g1` | Salud de señales | Una señal se rompe, congela, corrompe o desaparece | IMU STALE, joints NaN, timestamp regresivo, FREEZE |
| `safety_orchestrator_g1` | Transición de estado safety | Convierte SafetyEvent en SafetyAction gobernada — decide TX | TX-011 para caída gobernada |
| `recovery_g1` | Acción correctiva | Ejecuta la respuesta según la causa que le llegó — no decide la verdad del fault | `stabilization_mode`, `wait_for_primary_restore`, `operator_intervention` |

**Regla clave:** `recovery_g1` no decide qué pasó — ejecuta política según lo que recibió. La fuente de verdad es el componente que detectó el fault (`observer` o `watchdog`).

### Dos familias de faults — dos rutas

**Familia 1 — Falla física / caída** (ruta gobernada — "ruta fuerte"):
```
cross_consistency_observer
  → SafetyEvent (CONDITION_DETECTED / SECONDARY)
    → orchestrator / TX-011
      → SafetyAction (/safety_actions)
        → recovery_g1 _on_safety_action()
          → stabilization_mode
```

**Familia 2 — Falla de señal / sistema trabado** (ruta directa):
```
watchdog_g1
  → SafetyEvent (CONDITION_DETECTED / rule_id=4F-P2-*)
    → recovery_g1 _on_safety_event()
      → _dispatch_recovery() por rule_id
        → wait_for_primary_restore (STALE)
        → operator_intervention (FREEZE / NANINF / TIMESTAMP)
```

### Tabla de política completa — fault → detector → recovery

| Fault | Detector | Ruta | Recovery | Validado |
|---|---|---|---|---|
| Caída física | `cross_consistency_observer` | gobernada TX-011 | `stabilization_mode` | 4G-P2-C N=13, 4G-P4-D N=10, 4H-P1 |
| Caída fallback directa | `cross_consistency_observer` | directa (sin TX-011) | `wait_for_primary_restore` | 4H-P1 (semánticamente débil — declarado) |
| STALE | `watchdog_g1` | directa | `wait_for_primary_restore` | 4H-P1 harness |
| FREEZE | `watchdog_g1` | directa — bypass terminal | `operator_intervention` | 4H-P2 focal |
| NANINF | `watchdog_g1` | directa — bypass terminal | `operator_intervention` | 4H-P1 harness |
| TIMESTAMP | `watchdog_g1` | directa — bypass terminal | `operator_intervention` | 4H-P1 harness |
| RATE bajo | `watchdog_g1` | directa | SafetyEvent según política actual; recovery route pendiente de formalización — declarar como limitación DT-4F-001 | no formal |

Esta tabla es el núcleo de 4I-P2. Si una fila no tiene evidencia citada, se abre prueba focal mínima — no batería.

---

## Microfases

### 4I-P1 — Recrear SAFETY_MODEL_G1.md

**Deuda que cierra:** DT-4E-001 (ausente desde Stage 3A).

**Pregunta técnica:** ¿Qué garantiza exactamente el runtime G1, bajo qué condiciones, con qué evidencia?

**Método:** auditoría documental del código + evidencia validada. No se inventa — se extrae de lo que existe en el repo.

**Contenido obligatorio del documento:**

| Bloque | Descripción |
|---|---|
| Safety objective | Qué intenta garantizar el runtime — en términos observables |
| Scope | Qué cubre (sim, x86, ROS2) y qué no (hardware real, PD activo, Isaac Lab) |
| Fault/threat model | Caída física, STALE, FREEZE, NANINF, TIMESTAMP, RATE — definición y condición de disparo |
| Compound state model | SAFE / CAUTION / DANGER / STABILITY_RISK / FAULT_CRITICAL — transiciones permitidas |
| Restriction levels | NONE / R1 / R2 / R3 / R4-halt / R4-sit / R5 — semántica y uso actual |
| Transition model | TX-001→TX-011 — tipo, condición, estado origen/destino, evidencia |
| Observer contract | Qué publica `cross_consistency_observer`, bajo qué condición, con qué QoS |
| Watchdog contract | Qué publica `watchdog_g1` por fault type, con qué `rule_id` en `notes` |
| Orchestrator contract | Cómo convierte SafetyEvent → SafetyAction, qué transiciones dispara |
| Recovery contract | Qué hace `recovery_g1` por causa y por ruta (gobernada vs directa) |
| Timing model | t0→t1 (mean=2474ms), t1→t2 gobernada (mean=1.19ms), t1→t2 directa: evidencia focal ~0.7–0.9ms en 4H-P2; no paper-grade/N formal |
| Known limitations | PD diferido, thresholds pragmáticos, FREEZE false positive potencial, zombies, no UUID paper-grade |
| Evidence map | Logs/tests/docs que respaldan cada afirmación — nada sin evidencia |

**Criterio de cierre:** documento existe, es coherente con el código real (verificado por auditoría), y no contiene afirmaciones sin respaldo.

**Anti-pattern a evitar:** no escribir el modelo desde los informes — auditarlo desde el código fuente. (anti-pattern #66)

---

### 4I-P2 — Traceability Matrix

**Pregunta técnica:** ¿Cada fault tiene una ruta completa y trazable desde detección hasta acción con evidencia?

**Método — tres series en orden de costo:**

**Serie A — Auditoría de rutas (sin correr robot)**
Revisar código y documentar la matriz fault → detector → evento → ruta → recovery. Esta es la principal de 4I. Si la ruta está clara en código y tiene evidencia existente, se cita — no se repite el experimento.

**Serie B — Pruebas focales si hay duda**
Solo si una ruta no queda clara en código o no tiene evidencia citada. Prueba focal mínima — una variable, un observable. Varios casos ya están cubiertos en 4H-P1/4H-P2 y se citan directamente.

| Caso | Evidencia existente | Acción en 4I |
|---|---|---|
| Caída → TX-011 gobernada | 4G-P2-C N=13, 4G-P4-D N=10, 4H-P1 | citar |
| STALE → wait_for_primary_restore | 4H-P1 harness | citar |
| FREEZE → operator_intervention (bypass) | 4H-P2 focal | citar |
| NANINF → operator_intervention | 4H-P1 harness | citar |
| TIMESTAMP → operator_intervention | 4H-P1 harness | citar |
| RATE → política | sin evidencia formal | declarar como limitación |

**Serie C — Tabla de política consolidada**
La tabla fault → detector → recovery de la sección anterior. Es el entregable principal de 4I-P2.

**Criterio de cierre:** todas las rutas activas en código tienen fila en la matriz. Filas sin evidencia formal quedan declaradas explícitamente como no validadas.

---

### 4I-P3 — Policy Clarification

**Pregunta técnica:** ¿Las políticas operacionales del runtime están declaradas como contrato, no solo como comportamiento observado?

**Qué aclarar:**

| Política | Estado actual | Acción 4I-P3 |
|---|---|---|
| TX-009 POLICY_GATED condición exacta | DT-4F-003 abierta | documentar condición real desde código |
| Recovery single-flight | first accepted event wins — documentado en 4H-P2 | formalizar como contrato explícito |
| Direct fallback vs governed path | auditado en 4H-P1 — fallback es semánticamente débil | declarar alcance y limitación |
| Terminal manual causes | bypass validado 4H-P2 | incluir en SAFETY_MODEL_G1.md |
| Cooldown/escalation recuperables | RETRY_COOLDOWN_S=5s, MAX_AUTO_RETRIES=3 | declarar como política, no como constante hardcoded |

**Nota:** si la aclaración de TX-009 revela un gap de código, se declara deuda nueva — no se toca el runtime en 4I.

**Nota:** puede cerrarse DT-4F-003 en 4I-P3 si TX-009 POLICY_GATED queda extraída del código y documentada sin ambigüedad. Si hay ambigüedad real, se mantiene como deuda.

**Criterio de cierre:** cada política tiene una declaración escrita en SAFETY_MODEL_G1.md o en documento asociado.

---

### 4I-P4 — Limitations & Assumptions

**Pregunta técnica:** ¿Los límites del sistema están declarados con la misma prominencia que los resultados positivos?

**Declaraciones obligatorias:**

| Limitación | Origen | Estado |
|---|---|---|
| Thresholds son pragmáticos (FALLEN_W_CRITICAL=0.80, tiempos watchdog) | DT-4F-001 | no calibrados experimentalmente |
| PD control diferido — G1 no se sostiene activamente | DT-4E-006 | fuera de 4I |
| FREEZE IMU puede false-positive con robot inmóvil | DT-4F-004 | no resuelto |
| Zombies `<defunct>` por PID1 en `boring_noether` | DT-4G-004B | no bloqueante, no resuelto |
| No hay UUID/event_id paper-grade para correlación t1→t2 | DT-4G-002 | diferido a 4J |
| Isaac Lab bloqueado por GPU (necesita RTX 4080+) | — | fuera de T4 critical path |
| Hardware G1 real — sin Unitree SDK integration | — | fuera de scope |
| No certificación formal (no ISO 26262, no IEC 61508) | — | declarado explícitamente |
| direct fallback recovery (`wait_for_primary_restore`) semánticamente débil para caída física | 4H-P1 limitación declarada | auditado, no corregido |

**Criterio de cierre:** cada limitación está en SAFETY_MODEL_G1.md como sección explícita — no enterrada en notas.

---

### 4I-P5 — Readiness Gate hacia 4J

**Pregunta técnica:** ¿El sistema está listo para paper preparation?

**Checklist de gate:**

```
□ SAFETY_MODEL_G1.md existe y es coherente con código (4I-P1)
□ Cada ruta fault→recovery tiene evidencia citada (4I-P2)
□ Políticas operacionales están escritas como contrato (4I-P3)
□ Limitaciones declaradas con prominencia equivalente a resultados (4I-P4)
□ README apunta a SAFETY_MODEL_G1.md como documento maestro
□ Tesis v25+ refleja 4I cerrada
□ CI Build ✅ CI Audit ✅
□ No hay deudas Alta prioridad sin declaración explícita
□ No se introdujo comportamiento runtime nuevo durante 4I
```

Si el gate pasa: abrir 4J (fault injection matrix extendida, runtime verification properties, paper draft).

Si el gate falla: identificar qué falta, abrir microfase de cierre, repetir gate.

---

## Dependencias entre microfases

```
4I-P1 (SAFETY_MODEL_G1.md)
  └─→ 4I-P2 (Traceability Matrix)  ← depende del modelo de estados/transiciones de P1
        └─→ 4I-P3 (Policy Clarification)  ← depende de rutas documentadas en P2
              └─→ 4I-P4 (Limitations)  ← depende de scope definido en P1+P2
                    └─→ 4I-P5 (Gate)  ← valida coherencia de P1→P4
```

P1 es el bloqueante. Si P1 no está bien, P2→P5 no tienen base sólida.

---

## Deudas que 4I cierra (semánticamente)

| Deuda | Microfase |
|---|---|
| DT-4E-001 — SAFETY_MODEL_G1.md ausente | 4I-P1 |
| DT-4F-003 — TX-009 POLICY_GATED condición exacta | 4I-P3 |

## Deudas que 4I declara pero NO resuelve

| Deuda | Por qué no en 4I |
|---|---|
| DT-4E-006 — PD control | requiere fase propia de control físico/actuación → 5.x o etapa futura dedicada |
| DT-4F-001 — Thresholds | requiere calibración experimental → 4J |
| DT-4F-004 — FREEZE false positive | requiere experimento → 4J |
| DT-4G-002 — UUID traceability | paper-grade → 4J |
| DT-4G-004B — Zombies PID1 | operacional, no semántico → diferido |

---

## Lo que 4I produce

Al terminar 4I debe ser posible decir:

> *El G1 Deterministic Safety Runtime tiene un contrato formal de seguridad documentado: estados, transiciones, eventos, acciones, recovery, límites, evidencia y deudas activas. No es solo una colección de pruebas — es una arquitectura de safety trazable y auditable.*

Eso es lo que habilita 4J y eventualmente el paper.

---

*G1 Deterministic Safety Runtime — Análisis Etapa 4I*
*Preparado: 2026-06-19*
*PM: ChatGPT | Auditor: Claude | Operador: Jorge Padilla*
