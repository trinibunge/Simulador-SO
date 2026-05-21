import os

try:
    import anthropic
except Exception:
    anthropic = None


SYSTEM_PROMPT = """
Sos el "Asistente Médico" del Hospital MS, una interfaz conversacional
del simulador de Sistemas Operativos.

ROL:
- Respondés cualquier consulta del usuario de forma clara y útil.
- Conocés el simulador: pacientes = procesos, doctores = CPUs (semáforos),
  quirófano y cirujano = recursos compartidos (locks), triage por gravedad
  o por orden de llegada = scheduling. Si te preguntan sobre el sistema o
  algún concepto de SO, explicalo usando la metáfora del hospital cuando
  ayude a la comprensión.
- También respondés cualquier otra cosa que te pregunten (programación,
  cultura general, ayuda con el trabajo, etc.) de forma natural.

TONO:
- En español, cálido pero profesional.
- Directo, sin disclaimers innecesarios.
- Si no sabés algo, decilo y proponé cómo seguir.
"""


class HospitalAI:
    def __init__(self, state):
        self.state = state
        self.memory = []
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if (anthropic and api_key) else None

    def think(self, question: str):
        q = question.strip()
        if not q:
            return "Decime algo y te respondo."

        self.memory.append({"role": "user", "content": q})

        if self.client is not None:
            answer = self.ask_claude()
            if answer:
                self.memory.append({"role": "assistant", "content": answer})
                return answer

        answer = self.local_fallback(q)
        self.memory.append({"role": "assistant", "content": answer})
        return answer

    def ask_claude(self):
        messages = list(self.memory[-12:])
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"[AI] Error Anthropic: {e}")
            return None

    def local_fallback(self, q: str):
        q_low = q.lower()
        if any(w in q_low for w in ("proceso", "paciente", "scheduling", "triage", "planificaci")):
            return ("En este simulador, los pacientes son procesos del sistema operativo. "
                    "El triage decide el orden de atención: LLEGADA = Round Robin, "
                    "GRAVEDAD = Priority Scheduling. Los doctores son las CPUs disponibles.")
        if any(w in q_low for w in ("deadlock", "bloqueo", "recurso", "quirofano", "cirujano")):
            return ("Un deadlock ocurre cuando dos pacientes se esperan mutuamente: "
                    "A tiene el Quirófano y espera al Cirujano, mientras B tiene al Cirujano "
                    "y espera el Quirófano. Ninguno puede avanzar. "
                    "La solución: derivar al paciente menos crítico.")
        if any(w in q_low for w in ("farmacia", "buffer", "productor", "consumidor")):
            return ("La farmacia implementa el patrón Productor-Consumidor con un buffer acotado "
                    "de 8 medicamentos. Los farmacéuticos producen y los enfermeros consumen. "
                    "Si el buffer está lleno, los productores se bloquean; si está vacío, los consumidores esperan.")
        if any(w in q_low for w in ("semaforo", "semáforo", "mutex", "lock", "sincronizaci")):
            return ("Los semáforos controlan el acceso a recursos compartidos. "
                    "Un mutex (como el Quirófano) solo permite un proceso a la vez. "
                    "Un semáforo de conteo (como cpu_sem) permite N procesos simultáneos, "
                    "donde N es la cantidad de doctores/CPUs.")
        return ("Para usar el Asistente con IA real, configurá la variable de entorno "
                "ANTHROPIC_API_KEY. Por ahora puedo responder consultas básicas sobre "
                "scheduling, deadlock, sincronización y el simulador.")
