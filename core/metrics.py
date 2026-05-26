"""
Métricas del scheduler — TODAS calculadas desde acumuladores REALES.

No inventamos nada: cada Paciente lleva ready_acc, running_acc y blocked_acc
que se llenan en cada transición vía HospitalState._set_state(). Acá solo
tomamos snapshots y promediamos.

Definiciones (consistentes con cualquier libro de SO):
  - waiting_time  = tiempo total en READY antes de ser atendido (= ready_acc)
  - cpu_time      = tiempo total en RUNNING (= running_acc)
  - response_time = first_run_at - admitted_at
  - turnaround    = completed_at - admitted_at
  - throughput    = procesos_completados / wall_clock
  - CPU util      = tiempo total de CPU usado / (wall_clock * num_cpus)

Invariante matemática verificada en tests:
  waiting_time + cpu_time + blocked_time ≈ turnaround_time
"""

import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ProcessMetrics:
    pid: int
    name: str
    kind: str               # "patient" | "app"
    priority: int
    state: str              # "READY" | "RUNNING" | "BLOCKED" | "COMPLETED"
    is_completed: bool
    admitted_at: float
    completed_at: Optional[float]
    waiting_time: float     # segundos en READY
    response_time: float    # primera vez que tocó CPU
    turnaround_time: float  # admisión → alta
    cpu_time: float         # tiempo total de CPU consumido


@dataclass
class SchedulerMetrics:
    now: float
    wall_clock_total: float
    n_alive: int
    n_alive_patients: int
    n_alive_apps: int
    n_completed: int             # total terminados (pacientes + apps)
    n_completed_patients: int    # solo pacientes terminados (por si la UI lo quiere)
    n_completed_apps: int        # solo apps cerradas
    avg_waiting_time: float
    avg_response_time: float
    avg_turnaround_time: float
    avg_cpu_time: float
    cpu_utilization: float       # 0.0 a 1.0
    throughput: float            # procesos / segundo
    scheduler_mode: str


def snapshot_process(paciente, now: Optional[float] = None) -> ProcessMetrics:
    """
    Devuelve un ProcessMetrics, sumando el tiempo PARCIAL del estado actual
    a los acumuladores (sin tocar el paciente original).

    Por ejemplo: si un paciente está RUNNING desde hace 0.15s, su running_acc
    todavía no incluye esos 0.15s — los sumamos acá para el snapshot.
    """
    if now is None:
        now = time.time()

    ready_acc = paciente.ready_acc
    running_acc = paciente.running_acc
    blocked_acc = paciente.blocked_acc

    # Si el paciente sigue vivo, sumar el tiempo desde la última transición
    if paciente.completed_at is None:
        pending = max(0.0, now - paciente.last_state_change)
        if paciente.state == "READY":
            ready_acc += pending
        elif paciente.state == "RUNNING":
            running_acc += pending
        elif paciente.state == "BLOCKED":
            blocked_acc += pending

    is_completed = paciente.completed_at is not None

    if is_completed:
        turnaround = max(0.0, paciente.completed_at - paciente.admitted_at)
    else:
        turnaround = max(0.0, now - paciente.admitted_at)

    if paciente.first_run_at is not None:
        response = max(0.0, paciente.first_run_at - paciente.admitted_at)
    else:
        response = 0.0

    return ProcessMetrics(
        pid=paciente.pid,
        name=paciente.name,
        kind=paciente.kind,
        priority=paciente.priority,
        state="COMPLETED" if is_completed else paciente.state,
        is_completed=is_completed,
        admitted_at=paciente.admitted_at,
        completed_at=paciente.completed_at,
        waiting_time=ready_acc,
        response_time=response,
        turnaround_time=turnaround,
        cpu_time=running_acc,
    )


def compute_metrics(state) -> SchedulerMetrics:
    """
    Toma un snapshot completo bajo state.lock.

    Decisiones de diseño:
    - TODOS los procesos del sistema (pacientes + apps) cuentan para las
      métricas: CPU utilization, throughput y los promedios de
      waiting/response/turnaround. Una app cerrada consumió CPU real y
      esperó turnos reales — es parte legítima de la carga del sistema.
    - Si querés el desglose por tipo, n_completed_patients y
      n_completed_apps lo traen.
    """
    now = time.time()
    wall = max(0.001, now - state.simulation_start)

    with state.lock:
        vivos = list(state.pacientes.values())
        terminados = list(state.completed_history)
        mode = state.scheduler_mode
        num_cpus = state.num_cpus

    snaps_vivos = [snapshot_process(p, now) for p in vivos]
    snaps_term = [snapshot_process(p, now) for p in terminados]

    n_alive_patients = sum(1 for s in snaps_vivos if s.kind == "patient")
    n_alive_apps = sum(1 for s in snaps_vivos if s.kind == "app")

    n_completed_patients = sum(1 for s in snaps_term if s.kind == "patient")
    n_completed_apps = sum(1 for s in snaps_term if s.kind == "app")

    # Promedios sobre TODOS los procesos terminados (pacientes y apps)
    if snaps_term:
        n = len(snaps_term)
        avg_wait = sum(s.waiting_time for s in snaps_term) / n
        avg_resp = sum(s.response_time for s in snaps_term) / n
        avg_turn = sum(s.turnaround_time for s in snaps_term) / n
        avg_cpu = sum(s.cpu_time for s in snaps_term) / n
    else:
        avg_wait = avg_resp = avg_turn = avg_cpu = 0.0

    # CPU utilization: todo el tiempo de CPU consumido (vivos + terminados,
    # pacientes Y apps) sobre el tiempo total disponible
    total_cpu = sum(s.cpu_time for s in snaps_vivos) + sum(s.cpu_time for s in snaps_term)
    cpu_util = min(1.0, total_cpu / (wall * num_cpus))

    throughput = len(snaps_term) / wall

    return SchedulerMetrics(
        now=now,
        wall_clock_total=wall,
        n_alive=len(snaps_vivos),
        n_alive_patients=n_alive_patients,
        n_alive_apps=n_alive_apps,
        n_completed=len(snaps_term),
        n_completed_patients=n_completed_patients,
        n_completed_apps=n_completed_apps,
        avg_waiting_time=avg_wait,
        avg_response_time=avg_resp,
        avg_turnaround_time=avg_turn,
        avg_cpu_time=avg_cpu,
        cpu_utilization=cpu_util,
        throughput=throughput,
        scheduler_mode=mode,
    )


def list_alive(state) -> List[ProcessMetrics]:
    """Snapshot de todos los procesos vivos, ordenados por PID."""
    now = time.time()
    with state.lock:
        snaps = [snapshot_process(p, now) for p in state.pacientes.values()]
    snaps.sort(key=lambda s: s.pid)
    return snaps


def list_recent_completed(state, limit: int = 8) -> List[ProcessMetrics]:
    """Los últimos `limit` procesos terminados (pacientes + apps), los más recientes primero."""
    now = time.time()
    with state.lock:
        recent = list(state.completed_history)[-limit:]
    snaps = [snapshot_process(p, now) for p in recent]
    snaps.reverse()
    return snaps