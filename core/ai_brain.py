import os
import random

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

FAQ = {
    "hola": "¡Hola! Soy el Asistente Médico. Preguntame sobre el simulador hospitalario o sobre Sistemas Operativos.",
    "deadlock": "El deadlock ocurre cuando dos o más procesos (pacientes) quedan bloqueados esperando recursos entre sí y ninguno puede avanzar. Usá el botón de 'resolver deadlock' para forzar la recuperación.",
    "farmacia": "La Farmacia simula el problema Productor–Consumidor: los farmacéuticos producen medicamentos, los enfermeros los consumen, y el buffer tiene capacidad limitada.",
    "recepcion": "La Recepción funciona como la terminal de comandos; desde ahí podés admitir pacientes, provocar deadlock, cambiar el scheduler, etc.",
    "proceso": "Un proceso está representado por cada paciente en el simulador, con estados como listo, ejecutando, bloqueado, etc.",
    "historia": "La Historia Clínica muestra todos los pacientes actuales y su estado.",
    "prioridad": "El sistema puede planificar por orden de llegada o por gravedad (prioridad/triage).",
    "bitacora": "La Bitácora muestra los eventos en tiempo real del sistema hospitalario.",
    "cpu": "La CPU atiende pacientes ejecutando sus instrucciones. Cada paciente tiene un burst de CPU.",
    "hola!": "¡Hola! ¿En qué puedo ayudarte?"
}

BASIC_MSGS = [
    "¡Hola! Preguntame sobre el simulador o sobre Sistemas Operativos.",
    "No tengo conexión con la IA, pero igual puedo responder preguntas básicas del simulador.",
    "Podés preguntarme sobre deadlock, farmacia, proceso, historia clínica, recepción, CPU, etc.",
    "Si querés respuestas más avanzadas, configurá tu API Key de Groq en el sistema."
]

class HospitalAI:
    def __init__(self, state):
        self.state = state
        self.memory = []
        self._client = None
        self._has_api = False

        # --- Intentar importar Groq solo si hay API key ---
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key and api_key.startswith("gsk_"):
            try:
                from groq import Groq
                self._client = Groq(api_key=api_key)
                self._has_api = True
            except Exception:
                self._client = None
                self._has_api = False
        else:
            self._client = None
            self._has_api = False

    def think(self, question: str) -> str:
        q = question.strip().lower()
        if not q:
            return "Decime algo y te respondo."

        # --- Si hay IA ---
        if self._has_api and self._client:
            self.memory.append({"role": "user", "content": question})
            try:
                response = self._client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    max_tokens=512,
                    messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + self.memory,
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"Error al conectar con Groq: {e}"
            self.memory.append({"role": "assistant", "content": answer})
            return answer

        # --- Respuestas básicas (sin IA) ---
        for key, val in FAQ.items():
            if key in q:
                return val
        # Si no encontró coincidencias, responde una genérica
        return random.choice(BASIC_MSGS)