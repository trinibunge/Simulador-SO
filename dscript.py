class DungScriptInterpreter:
    def __init__(self, state):
        self.state = state

    def execute(self, raw: str):
        line = raw.strip()
        if not line:
            return ""

        parts = line.split()
        cmd = parts[0].upper()

        try:
            if cmd == "SPAWN":
                name = parts[1]
                priority = 5
                if len(parts) >= 4 and parts[2].upper() == "PRIORITY":
                    priority = int(parts[3])
                self.state.add_hero(name, priority)
                return f"OK: {name} creado"

            if cmd == "KILL":
                self.state.kill_hero(parts[1])
                return "OK: proceso eliminado"

            if cmd == "SCHEDULE":
                if self.state.set_mode(parts[1]):
                    return f"OK: {parts[1].upper()}"
                return "Modo inválido"

            if cmd == "MEMDUMP":
                heroes = self.state.get_heroes()
                if not heroes:
                    return "RAM vacía"
                return "\n".join(f"{h.pid} {h.name} PRI={h.priority} {h.state}" for h in heroes)

            if cmd == "CHAOS":
                self.state.chaos_mode = not self.state.chaos_mode
                self.state.log("CHAOS", f"Chaos {'ON' if self.state.chaos_mode else 'OFF'}")
                return "Chaos toggled"

            if cmd == "DEADLOCK":
                self.state.deadlock_demo = True
                return "Deadlock demo activada"

            if cmd == "EASTER":
                return "EASTER unlocked"

            return f"Comando desconocido: {cmd}"
        except Exception as e:
            return f"Error: {e}"