class DungScriptInterpreter:
    """
    Lenguaje de comandos de la Recepción del Hospital.

    Comandos:
      ADMITIR nombre [GRAVEDAD n] [TIEMPO n]
      ALTA nombre|pid
      TRIAGE LLEGADA|GRAVEDAD
      OPERAR pid recurso
      LIBERAR pid recurso
      RECURSOS
      LISTA
      DEADLOCK
      AYUDA
      EASTER

    Recursos válidos: QUIROFANO, CIRUJANO
    """

    def __init__(self, state):
        self.state = state

    def execute(self, raw: str) -> str:
        line = raw.strip()
        if not line:
            return ""

        parts = line.split()
        cmd = parts[0].upper()

        try:
            if cmd in ("AYUDA", "HELP"):
                return ("Comandos:\n"
                        "  ADMITIR <nombre> [GRAVEDAD n] [TIEMPO n]\n"
                        "  ALTA <nombre|pid>\n"
                        "  TRIAGE LLEGADA|GRAVEDAD\n"
                        "  OPERAR <pid> <QUIROFANO|CIRUJANO>\n"
                        "  LIBERAR <pid> <QUIROFANO|CIRUJANO>\n"
                        "  RECURSOS · LISTA · DEADLOCK · EASTER")

            if cmd in ("ADMITIR", "SPAWN"):
                if len(parts) < 2:
                    return "Uso: ADMITIR nombre [GRAVEDAD n] [TIEMPO n]"
                name = parts[1]
                priority = 5
                burst = 8
                i = 2
                while i < len(parts):
                    kw = parts[i].upper()
                    if kw in ("GRAVEDAD", "PRIORITY") and i + 1 < len(parts):
                        priority = int(parts[i + 1]); i += 2
                    elif kw in ("TIEMPO", "BURST") and i + 1 < len(parts):
                        burst = int(parts[i + 1]); i += 2
                    else:
                        i += 1
                h = self.state.add_hero(name, priority, burst)
                return f"OK: {name} admitido con PID={h.pid}" if h else "ERROR: sala llena"

            if cmd in ("ALTA", "KILL"):
                if len(parts) < 2:
                    return "Uso: ALTA nombre|pid"
                return ("OK: alta dada" if self.state.kill_hero(parts[1])
                        else "No existe ese paciente")

            if cmd in ("TRIAGE", "SCHEDULE"):
                if len(parts) < 2:
                    return "Uso: TRIAGE LLEGADA|GRAVEDAD"
                arg = parts[1].upper()
                mode = "ROUNDROBIN" if arg in ("LLEGADA", "FIFO", "ROUNDROBIN") else "PRIORITY"
                self.state.set_mode(mode)
                return f"OK: triage = {arg}"

            if cmd == "DEADLOCK":
                self.state.deadlock_demo = True
                return "Demo de deadlock disparada"

            if cmd in ("LISTA", "MEMDUMP"):
                heroes = self.state.get_heroes()
                if not heroes:
                    return "(no hay pacientes)"
                lines = ["PID  PACIENTE        GRAV  ESTADO     ATENCIÓN  RECURSOS"]
                for h in heroes:
                    held = ",".join(h.holding) or "-"
                    estado = {
                        "READY":   "sala-esp",
                        "RUNNING": "atendido",
                        "BLOCKED": "bloqueado",
                    }.get(h.state, h.state)
                    lines.append(f"{h.pid:<4} {h.name:<15} {h.priority:<4} "
                                 f"{estado:<9} {h.cpu_used}/{h.burst:<7} {held}")
                return "\n".join(lines)

            if cmd in ("OPERAR", "REQUEST"):
                if len(parts) < 3:
                    return "Uso: OPERAR <pid> <QUIROFANO|CIRUJANO>"
                pid = int(parts[1])
                res = parts[2].upper()
                ok = self.state.request_resource(pid, res, timeout=0.5)
                return f"{'OK: recurso asignado' if ok else 'BLOQUEADO: recurso ocupado'}"

            if cmd in ("LIBERAR", "RELEASE"):
                if len(parts) < 3:
                    return "Uso: LIBERAR <pid> <QUIROFANO|CIRUJANO>"
                pid = int(parts[1])
                res = parts[2].upper()
                self.state.release_resource(pid, res)
                return f"OK: {res} liberado"

            if cmd == "RECURSOS":
                lines = ["RECURSO      EN USO POR    EN COLA"]
                with self.state.lock:
                    for r, owner in self.state.resource_owner.items():
                        ws = ",".join(str(p) for p in self.state.resource_waiters[r]) or "-"
                        owner_s = str(owner) if owner is not None else "libre"
                        lines.append(f"{r:<12} {owner_s:<13} {ws}")
                return "\n".join(lines)

            if cmd == "EASTER":
                return "EASTER unlocked"

            return f"Comando desconocido: {cmd}. Probá AYUDA."
        except Exception as e:
            return f"Error: {e}"