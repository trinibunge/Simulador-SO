import os

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class CatacumbaAI:
    def __init__(self, state):
        self.state = state
        self.memory = []

        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None

    def think(self, question: str):
        q = question.strip()
        if not q:
            return "Decime algo y te respondo."

        # siempre guardar conversación
        self.memory.append({"role": "user", "content": q})

        # si hay API externa, usarla sí o sí como primera opción
        if self.client is not None:
            answer = self.ask_openai()
            if answer:
                self.memory.append({"role": "assistant", "content": answer})
                return answer

        # fallback solo si la API no está disponible
        answer = self.local_fallback(q)
        self.memory.append({"role": "assistant", "content": answer})
        return answer

    def ask_openai(self):
        system_prompt = """
Sos Oracle, una IA conversacional general y útil.

OBJETIVO:
- Responder cualquier pregunta del usuario de forma natural, clara y útil.
- No limitarte al juego.
- No responder con frases genéricas de fallback si podés contestar mejor.
- Si la pregunta es ambigua, interpretala de la forma más probable y respondé algo útil.
- Si no sabés algo, decilo con honestidad y sugerí cómo seguir.

TONO:
- en español
- amigable
- directo
- conversacional
- sin listas innecesarias salvo que aporten claridad

Si el usuario pregunta sobre La Catacumba, el juego o la interfaz, respondé también con contexto del proyecto.
"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.memory[-12:])

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AI] Error OpenAI: {e}")
            return None

    def local_fallback(self, q: str):
        # fallback general, no tan rígido
        return (
            "No pude conectar con la IA externa en este momento. "
            "Probá de nuevo en un rato o revisá la API key."
        )