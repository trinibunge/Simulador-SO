# Hospital MS — Simulador de Sistemas Operativos

[![Maximiliano López](https://img.shields.io/badge/GitHub-Maximiliano_López-B7E3FF?logo=github&logoColor=black)](https://github.com/maaxilopp)
[![Trinidad Bunge](https://img.shields.io/badge/GitHub-Trinidad_Bunge-FFD966?logo=github&logoColor=black)](https://github.com/trinibun)

##  ¿Qué es esto?

Un SO ficticio con interfaz gráfica (estilo "escritorio con apps") que demuestra los conceptos clásicos de la materia **funcionando de verdad** bajo el capó:

| Concepto SO | Cómo se ve en el simulador |
|---|---|
| Proceso | Paciente con PID y nombre |
| CPU (Semaphore) | Doctor de guardia atendiendo |
| Estado READY | En sala de espera |
| Estado RUNNING | Siendo atendido en consultorio |
| Estado BLOCKED | Esperando un recurso médico |
| Prioridad | Triage (1 = crítico, 10 = leve) |
| Burst time | Tiempo de atención necesario |
| Recurso compartido (Lock) | Quirófano · Cirujano |
| Round Robin | Atención por orden de llegada |
| Priority Scheduling | Atención por gravedad |
| Deadlock | Dos pacientes se traban por Quirófano + Cirujano |
| Productor-Consumidor | Farmacéuticos producen, enfermeros consumen |

---

##  Cómo correrlo

### Requisitos

- **Python 3.10 o superior** (probado con 3.14)
- Dependencias:
  ```bash
  pip install pillow anthropic
  ```

### Ejecutar

```bash
python main.py
```

### IA opcional (Asistente Médico)

Si querés que el asistente de IA funcione con respuestas reales de Claude, configurá tu API key como variable de entorno:

```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python main.py
```

```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."
python main.py
```

Sin la API key, el asistente sigue funcionando con respuestas pre-armadas sobre conceptos del simulador.

---

##  Las apps del sistema

Cuando arranca el simulador, ves un escritorio con un dock abajo. Cada ícono abre una app. Pasá el mouse por encima de los íconos para ver qué hace cada uno.

### 🏥 Hospital (panel principal)

El panel central de operaciones. Tiene 3 columnas y una sección inferior.

- **Sala de espera (READY):** pacientes esperando un doctor libre.
- **Consultorios (RUNNING):** doctores atendiendo. Cada consultorio = una CPU.
- **Esperando recurso (BLOCKED):** pacientes que pidieron un recurso ocupado.
- **Recursos compartidos:** quién tiene el quirófano y el cirujano, y quién está en la cola.

**Botones útiles:**
- `➕ Admitir paciente` — agrega un proceso aleatorio.
- `🚨 Caso crítico` — agrega uno de gravedad 1 (máxima prioridad).
- `👥 Llegan 8` — stress test, agrega 8 a la vez.
- `Orden de llegada / Por gravedad` — cambia el algoritmo de scheduling en caliente.
- `⚠️ Provocar deadlock` — lanza la demo. Dos pacientes tomarán Quirófano y Cirujano en orden cruzado y se trabarán entre ellos.
- `✅ Resolver deadlock` — deriva al paciente menos grave para destrabar el sistema (esto es la **estrategia de recuperación por terminación de proceso víctima**).

###  Historia Clínica

Tabla en vivo de todos los pacientes con su PID, gravedad, estado, ticks de CPU usados y recursos que tienen tomados. Es el equivalente al `ps aux` o al monitor de procesos.

###  Recepción

Terminal de comandos. Aceptá:

| Comando | Qué hace |
|---|---|
| `AYUDA` | Lista todos los comandos |
| `ADMITIR Juan GRAVEDAD 2 TIEMPO 10` | Crea un paciente con esa prioridad y burst |
| `ALTA <pid o nombre>` | Termina ese proceso |
| `TRIAGE LLEGADA` o `TRIAGE GRAVEDAD` | Cambia el scheduler |
| `OPERAR <pid> QUIROFANO` | El paciente intenta tomar ese recurso |
| `LIBERAR <pid> QUIROFANO` | Lo libera |
| `RECURSOS` | Muestra dueño y cola de cada recurso |
| `LISTA` | Tabla de todos los procesos |
| `DEADLOCK` | Dispara la demo de deadlock |
| `EASTER` | Easter egg 🐍 |

###  Bitácora de Guardia

Log en vivo de todos los eventos del sistema. Útil para mostrar en la defensa qué está pasando bajo el capó: ingresos, context switches, adquisiciones de locks, detección de deadlock, etc.

###  Farmacia (Productor-Consumidor)

Demuestra el patrón clásico de **bounded buffer**.

- 2 farmacéuticos (**productores**) generan medicamentos.
- 3 enfermeros (**consumidores**) los retiran.
- Buffer acotado de capacidad 8.

**Qué observar:** si los productores van más rápido, el buffer se llena y se bloquean al hacer `put()`. Si los consumidores van más rápido, el buffer se vacía y se bloquean al hacer `get()`. La sincronización está implementada con `queue.Queue(maxsize=8)` de Python, que internamente usa un mutex y dos condition variables.

###  Asistente Médico

Chat con IA temática. Le podés preguntar sobre cualquier concepto de SO o del simulador y te lo explica con la metáfora del hospital. Usa Claude Haiku 4.5 si tenés la API key configurada; sino, tiene respuestas locales para preguntas frecuentes.

###  Snake

Mini-juego clásico. Si tocás un borde, la serpiente vuelve a su tamaño original. Si chocás contra vos mismo, GAME OVER (SPACE o R para reiniciar). No tiene relación con SO, es solo un easter egg.

---

##  Cómo funciona por dentro

### Estructura del proyecto

```
Simulador-SO/
├── main.py                    # Entry point: arranca scheduler, detector y UI
├── core/
│   ├── state.py              # HospitalState: estado global compartido
│   ├── scheduler.py          # Hilo del scheduler (Round Robin / Priority)
│   ├── deadlock.py           # Hilo detector de deadlock
│   ├── dscript.py            # Intérprete de comandos de Recepción
│   └── ai_brain.py           # Cliente de IA (Anthropic)
├── ui/
│   ├── desktop.py            # Escritorio y dock
│   ├── window_base.py        # Sistema de ventanas flotantes
│   ├── hospital_app.py       # Panel principal
│   ├── process_app.py        # Historia Clínica
│   ├── terminal_app.py       # Recepción
│   ├── log_app.py            # Bitácora
│   ├── pharmacy_app.py       # Productor-Consumidor
│   ├── ai_app.py             # Asistente Médico
│   ├── snake_app.py          # Snake
│   ├── boot_screen.py        # Pantalla de arranque
│   ├── topbar.py / dock.py   # Topbar y dock con tooltips
│   ├── toast.py              # Notificaciones flotantes
│   └── theme.py              # Paleta de colores y tipografía
└── assets/icons/             # Íconos PNG del dock
```

### Hilos en ejecución

El simulador corre con **al menos 3 hilos principales**, más los que se crean dinámicamente:

1. **Hilo principal (Tkinter):** dibuja la UI.
2. **`Scheduler`:** elige qué proceso ejecutar y simula context switches con un quantum de 0.4s.
3. **`DeadlockDetector`:** revisa el grafo de espera cada 0.5s buscando ciclos.
4. **Demo de deadlock:** 2 hilos worker que pelean por dos locks.
5. **Farmacia:** 2 productores + 3 consumidores, todos hilos daemon.

### Primitivas de sincronización usadas (las REALES)

```python
# En core/state.py:

self.lock = threading.RLock()                       # exclusión mutua del estado
self.cpu_sem = threading.Semaphore(num_cpus)        # CPUs disponibles
self.resources = {
    "QUIROFANO": threading.Lock(),                  # mutex de recurso
    "CIRUJANO":  threading.Lock(),
}
self.logs = queue.Queue()                           # productor-consumidor (logs)
self.pharmacy_queue = queue.Queue(maxsize=8)        # bounded buffer (farmacia)
```

### Detección de deadlock

`HospitalState.detect_deadlock()` construye un **grafo de espera** (wait-for graph) a partir del estado actual: por cada proceso bloqueado, agrega una arista hacia el dueño del recurso que está esperando. Luego hace **DFS** buscando ciclos. Si encuentra uno, lo resuelve matando al proceso de menor prioridad (mayor número), liberando sus recursos.

Esta es la estrategia clásica de **deadlock detection + recovery**: dejar que el deadlock ocurra, detectarlo, y romperlo terminando un proceso víctima.

### Patrón productor-consumidor

`queue.Queue(maxsize=N)` de Python implementa exactamente lo que el libro de Silberschatz describe:

- `put()` bloquea si el buffer está lleno.
- `get()` bloquea si el buffer está vacío.
- Internamente usa un mutex y dos condition variables (`not_full`, `not_empty`).

La Farmacia usa este patrón explícitamente. La cola de logs también lo usa (productores: scheduler, deadlock detector, todos los hilos del sistema; consumidor: la app Bitácora).

---

## Para la defensa del obligatorio

### Parte 3 — Concurrencia y sincronización

El simulador demuestra **en vivo** los siguientes conceptos:

1. **Hilos concurrentes:** scheduler, detector, productores y consumidores corren simultáneamente.
2. **Exclusión mutua (mutex):** `RLock` protege el diccionario de procesos. Sin esto, dos hilos modificando el estado al mismo tiempo causarían race conditions.
3. **Semáforos:** `cpu_sem = Semaphore(N)` limita cuántos procesos están en estado RUNNING al mismo tiempo. Es el patrón canónico de "N CPUs disponibles".
4. **Locks reales sobre recursos:** quirófano y cirujano son `threading.Lock()`, no simulaciones.
5. **Productor-consumidor con bounded buffer:** la Farmacia usa `queue.Queue(maxsize=8)`.
6. **Deadlock real:** dos hilos tomando dos locks en orden invertido. No es una animación, es un deadlock que el sistema operativo Python detectaría como tal.
7. **Detección y recuperación:** DFS sobre wait-for graph, terminación de proceso víctima.

### Parte 4 — Ataque + ingeniería social

Esta parte del obligatorio se entrega como documento aparte, no está en el código del simulador.

---

##  Bugs conocidos y limitaciones

- El deadlock dura 10 segundos antes de auto-resolverse si nadie toca el botón. Esto es a propósito, para que se pueda ver el cartel rojo.
- Snake no tiene puntuación máxima ni niveles. Es minimalista.
- La IA requiere conexión a internet y API key. Sin eso, funciona en modo offline con respuestas básicas.
- Las ventanas se pueden arrastrar pero no redimensionar.

---

