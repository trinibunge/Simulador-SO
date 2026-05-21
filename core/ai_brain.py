class HospitalAI:
    def __init__(self, state):
        self.state = state
        self.memory = []

        self.faq = [
            (
                "que es un proceso",
                "En el simulador, un proceso es un paciente. Cada paciente tiene un PID, una prioridad, un estado y tiempo de CPU necesario."
            ),
            (
                "que es scheduling",
                "Scheduling es la forma en que el sistema decide a qué paciente atender primero. En el simulador podés usar orden de llegada o gravedad."
            ),
            (
                "que es round robin",
                "Round Robin atiende a los pacientes por turnos, de manera más o menos equitativa."
            ),
            (
                "que es priority scheduling",
                "Priority Scheduling atiende primero a los pacientes con mayor prioridad, o sea los más graves."
            ),
            (
                "que es deadlock",
                "Deadlock es cuando dos pacientes quedan bloqueados esperando recursos entre sí. Ninguno puede avanzar porque cada uno necesita algo que tiene el otro."
            ),
            (
                "cuando pasa un deadlock",
                "Pasa cuando un paciente toma un recurso, otro toma otro recurso, y después ambos piden el recurso que tiene el otro."
            ),
            (
                "que es un mutex",
                "Un mutex es un candado que permite que un solo proceso use un recurso a la vez."
            ),
            (
                "que es un semaforo",
                "Un semáforo controla cuántos procesos pueden entrar a un recurso o sección crítica al mismo tiempo."
            ),
            (
                "que es productor consumidor",
                "Productor-Consumidor es un patrón donde unos generan elementos y otros los consumen, usando un buffer intermedio."
            ),
            (
                "que hace la farmacia",
                "La farmacia muestra el patrón Productor-Consumidor: farmacéuticos producen medicamentos y enfermeros los consumen desde un buffer acotado."
            ),
            (
                "que hace la bitacora",
                "La bitácora muestra los eventos del sistema en vivo: admisiones, atenciones, recursos, deadlocks y más."
            ),
            (
                "que hace la recepcion",
                "La recepción es la terminal de comandos del simulador. Desde ahí podés admitir pacientes, cambiar triage, pedir recursos y provocar deadlock."
            ),
            (
                "que es la historia clinica",
                "La Historia Clínica muestra todos los pacientes del sistema con su PID, prioridad, estado, CPU usada y recursos tomados."
            ),
            (
                "como provoco deadlock",
                "Podés usar el botón 'Provocar deadlock' en Hospital o el comando DEADLOCK en la recepción."
            ),
            (
                "como resuelvo deadlock",
                "Podés usar el botón 'Resolver deadlock'. El sistema deriva al paciente menos grave para liberar recursos."
            ),
            (
                "que hace el asistente",
                "Este asistente responde preguntas sobre el simulador y sobre conceptos de Sistemas Operativos."
            ),
        ]

    def think(self, question: str):
        q = question.strip()
        if not q:
            return "Decime algo y te respondo."

        self.memory.append({"role": "user", "content": q})

        answer = self.local_fallback(q)

        self.memory.append({"role": "assistant", "content": answer})
        return answer

    def local_fallback(self, q: str):
        q_low = q.lower().strip()
        q_clean = (
            q_low.replace("¿", "")
                 .replace("?", "")
                 .replace("¡", "")
                 .replace("!", "")
                 .replace("á", "a")
                 .replace("é", "e")
                 .replace("í", "i")
                 .replace("ó", "o")
                 .replace("ú", "u")
        )

        for key, answer in self.faq:
            if key in q_clean:
                return answer

        if "proceso" in q_clean or "paciente" in q_clean:
            return (
                "En el simulador, los pacientes representan procesos del sistema operativo. "
                "Tienen prioridad, estado y tiempo de CPU."
            )

        if "deadlock" in q_clean or "bloqueo" in q_clean:
            return (
                "Deadlock es un bloqueo mutuo entre procesos. Cada uno espera un recurso que tiene el otro, "
                "y ninguno puede continuar."
            )

        if "scheduler" in q_clean or "triage" in q_clean or "planific" in q_clean:
            return (
                "El scheduler decide qué paciente atender primero. En tu simulador podés usar orden de llegada "
                "o prioridad por gravedad."
            )

        if "farmacia" in q_clean or "buffer" in q_clean or "productor" in q_clean or "consumidor" in q_clean:
            return (
                "La farmacia modela el patrón Productor-Consumidor con un buffer acotado. "
                "Los productores agregan medicamentos y los consumidores los retiran."
            )

        if "mutex" in q_clean or "semaforo" in q_clean or "lock" in q_clean:
            return (
                "Las primitivas de sincronización sirven para evitar carreras de datos y coordinar el acceso a recursos compartidos."
            )

        return (
            "Puedo responder sobre el simulador y sobre Sistemas Operativos. "
            "Probá preguntarme por proceso, scheduling, deadlock, mutex, semáforos o farmacia."
        )