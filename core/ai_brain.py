import os
from groq import Groq

_SYSTEM_PROMPT = """Sos el Asistente Médico de un simulador de Sistema Operativo con temática hospitalaria.
El simulador modela conceptos de SO (procesos, scheduling, deadlock, mutex, semáforos, productor-consumidor) usando pacientes y recursos médicos.

Contexto del simulador:
- Los pacientes representan procesos del SO (tienen PID, prioridad, estado, burst de CPU).
- El scheduler puede usar FCFS (orden de llegada) o Priority Scheduling (por gravedad/triage).
- Existe un módulo de deadlock: dos pacientes pueden quedar bloqueados esperando recursos del otro.
- La Farmacia modela el patrón Productor-Consumidor con un buffer acotado.
- La Bitácora muestra logs del sistema en tiempo real.
- La Recepción es la terminal de comandos (admitir pacientes, provocar/resolver deadlock, etc).
- La Historia Clínica muestra todos los pacientes con su estado actual.

Respondé en español, de forma clara y concisa. Si la pregunta no tiene relación con el simulador ni con Sistemas Operativos, igual podés responder brevemente."""


class HospitalAI:
    def __init__(self, state):
        self.state = state
        self.memory = []
        self._client = None

    def _get_client(self):
        if self._client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Falta la variable de entorno GROQ_API_KEY. "
                    "Obtené una gratis en console.groq.com y configurala."
                )
            self._client = Groq(api_key=api_key)
        return self._client

    def think(self, question: str) -> str:
        q = question.strip()
        if not q:
            return "Decime algo y te respondo."

        self.memory.append({"role": "user", "content": q})

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                max_tokens=512,
                messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + self.memory,
            )
            answer = response.choices[0].message.content
        except RuntimeError as e:
            answer = str(e)
        except Exception as e:
            answer = f"Error al conectar con Groq: {e}"

        self.memory.append({"role": "assistant", "content": answer})
        return answer
