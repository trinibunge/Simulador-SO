# Hospital MS — Simulador de Sistemas Operativos

[![Maximiliano López](https://img.shields.io/badge/GitHub-Maximiliano_López-B7E3FF?logo=github&logoColor=black)](https://github.com/maaxilopp)
[![Trinidad Bunge](https://img.shields.io/badge/GitHub-Trinidad_Bunge-FFD966?logo=github&logoColor=black)](https://github.com/trinibun)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)

Un SO ficticio con interfaz gráfica (estilo "escritorio con apps") que demuestra los conceptos clásicos de la materia **funcionando de verdad** bajo el capó. Cubre la **Parte 3** del obligatorio: concurrencia y sincronización reales con hilos y procesos.

---

## Indice

- [La metáfora](#la-metáfora)
- [Cómo correrlo](#cómo-correrlo)
- [Las apps del sistema](#las-apps-del-sistema)
- [Parte 3 — Concurrencia y sincronización](#parte-3--concurrencia-y-sincronización)
- [Parte 4 — Pendiente](#parte-4--pendiente)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Limitaciones conocidas](#limitaciones-conocidas)

---

## La metáfora

| Concepto SO               | Cómo se ve en el simulador                                        |
|---------------------------|-------------------------------------------------------------------|
| Proceso                   | Paciente con PID y nombre                                         |
| CPU (Semaphore)           | Doctor de guardia atendiendo                                      |
| Estado READY              | En sala de espera                                                 |
| Estado RUNNING            | Siendo atendido en consultorio                                    |
| Estado BLOCKED            | Esperando un recurso médico                                       |
| Prioridad                 | Triage (1 = crítico, 10 = leve)                                   |
| Burst time                | Tiempo de atención necesario                                      |
| Recurso compartido (Lock) | Quirófano · Cirujano                                              |
| Round Robin               | Atención por orden de llegada                                     |
| Priority Scheduling       | Atención por gravedad                                             |
| Deadlock                  | Dos pacientes se traban por Quirófano + Cirujano                  |
| Productor-Consumidor      | Farmacéuticos producen, enfermeros consumen                       |
| Lectores-Escritores       | Doctores consultan la historia clínica, enfermeras la actualizan  |
| Apps interactivas         | Wordle y Snake corren como procesos del SO compitiendo por la CPU |
| IPC (proceso separado)    | Demonio de logging (`hospital.log`)                               |
| Chatbot                   | Respuestas locales por palabras clave sobre conceptos de SO       |

---

## Cómo correrlo

### Requisitos

- **Python 3.10 o superior** (probado con 3.14)
- Dependencias:

```bash
pip install pillow
```

### Ejecutar

```bash
python main.py
```

---

## Las apps del sistema

Cuando arranca el simulador, ves un escritorio con un dock abajo. Cada ícono abre una app.

### Hospital (panel principal)

El panel central de operaciones. Tiene 3 columnas y una sección inferior.

- **Sala de espera (READY):** pacientes esperando un doctor libre.
- **Consultorios (RUNNING):** doctores atendiendo. Cada consultorio = una CPU.
- **Esperando recurso (BLOCKED):** pacientes que pidieron un recurso ocupado.
- **Recursos compartidos:** quién tiene el quirófano y el cirujano, y quién está en la cola.

**Botones útiles:**

- `Admitir paciente` — agrega un proceso aleatorio.
- `Caso crítico` — agrega uno de gravedad 1 (máxima prioridad).
- `Llegan 8` — stress test, agrega 8 a la vez.
- `Orden de llegada / Por gravedad` — cambia el algoritmo de scheduling en caliente.
- `Provocar deadlock` — lanza la demo. Dos pacientes tomarán Quirófano y Cirujano en orden cruzado y se trabarán.
- `Resolver deadlock` — deriva al paciente menos grave para destrabar el sistema (estrategia de **recuperación por terminación de proceso víctima**).

### Historia Clínica

Tabla en vivo de todos los pacientes con su PID, gravedad, estado, ticks de CPU usados y recursos tomados. Equivalente al `ps aux` o al monitor de procesos.

### Recepción (terminal)

| Comando                              | Qué hace                                   |
|--------------------------------------|--------------------------------------------|
| `AYUDA`                              | Lista todos los comandos                   |
| `ADMITIR Juan GRAVEDAD 2 TIEMPO 10`  | Crea un paciente con esa prioridad y burst |
| `ALTA <pid o nombre>`                | Termina ese proceso                        |
| `TRIAGE LLEGADA` o `TRIAGE GRAVEDAD` | Cambia el scheduler                        |
| `OPERAR <pid> QUIROFANO`             | El paciente intenta tomar ese recurso      |
| `LIBERAR <pid> QUIROFANO`            | Lo libera                                  |
| `RECURSOS`                           | Muestra dueño y cola de cada recurso       |
| `LISTA`                              | Tabla de todos los procesos                |
| `DEADLOCK`                           | Dispara la demo de deadlock                |
| `EASTER`                             | Easter egg                                 |

### Bitácora de Guardia

Log en vivo de todos los eventos del sistema. Útil para la defensa: ingresos, context switches, adquisiciones de locks, detección de deadlock, etc.

### Farmacia (Productor-Consumidor)

Demuestra el patrón clásico de **bounded buffer**.

- 2 farmacéuticos (**productores**) generan medicamentos.
- 3 enfermeros (**consumidores**) los retiran.
- Buffer acotado de capacidad 8.

Si los productores van más rápido, el buffer se llena y se bloquean al hacer `put()`. Si los consumidores van más rápido, el buffer se vacía y se bloquean al hacer `get()`. Implementado con `queue.Queue(maxsize=8)`, que internamente usa un mutex y dos condition variables (`not_full`, `not_empty`).

### Historia Clínica Compartida (Lectores-Escritores)

Demuestra el problema clásico de **Readers-Writers** (Courtois, 1971).

- **Doctores (lectores)** consultan la historia clínica. Pueden hacerlo **varios a la vez** sin problema.
- **Enfermeras (escritoras)** actualizan la historia. Necesitan acceso **exclusivo**: ningún lector ni otra escritora activa.

**Qué observar en la bitácora:**

- Cuando llega el primer lector, bloquea a las escritoras.
- Mientras haya lectores activos, las escritoras quedan en cola.
- Cuando el último lector se va, se libera el lock y entra la escritora.
- Si una escritora está activa, todos los demás (lectores y escritoras) esperan.

Implementado con dos locks (`_readers_lock` y `_write_lock`) y un contador `_reader_count`, siguiendo el protocolo canónico: el primer lector adquiere el write_lock y el último lo libera.

### Métricas

Panel de métricas calculadas a partir de **acumuladores reales** (no inventadas): waiting time, response time, turnaround, CPU utilization, throughput. Cumple la invariante `waiting + cpu + blocked ≈ turnaround`.

### Chatbot

Chatbot temático con respuestas locales basadas en palabras clave. Responde preguntas frecuentes sobre el simulador y sobre conceptos de Sistemas Operativos (procesos, scheduling, deadlock, mutex, semáforos, productor-consumidor, etc.).

### Wordle y Snake — apps como procesos reales

Estos dos juegos no son adorno: están **registrados en el scheduler** como procesos con `kind="app"` y demuestran multitarea real.

- Aparecen en la **Historia Clínica** como procesos vivos con PID, igual que los pacientes.
- **Pelean por la CPU** contra los pacientes en cada ciclo del scheduler (compiten por el semáforo `cpu_sem`).
- **Nunca terminan por burst** (son interactivas) — siguen vivas hasta que cerrás la ventana, igual que un proceso de usuario real.
- Su tiempo de CPU consumido se cuenta para la métrica de **CPU utilization** en el panel de métricas.

**Wordle:** versión en español, palabras de 5 letras. Listas de objetivos y válidas en `assets/wordle/`. Buen ejemplo de cómo una app interactiva sigue consumiendo quantum mientras el usuario piensa.

**Snake:** clásico minimalista. Si tocás un borde, la serpiente vuelve a su tamaño original. Si chocás contra vos, GAME OVER (SPACE o R para reiniciar).

> **Tip para la defensa:** abrí el Hospital, la Farmacia, la Historia Clínica Compartida, el Wordle y el Snake al mismo tiempo. Mirá el panel de métricas: tenés decenas de hilos y un proceso aparte (el log daemon) compitiendo por una sola CPU. Es un SO de verdad, en chiquito.

---

## Parte 3 — Concurrencia y sincronización

Esta es la parte central del obligatorio que cubre este código. Se usaron **tanto hilos como procesos** concurrentes, con justificación explícita para cada uno.

### Por qué hilos Y procesos (justificación)

La consigna pide justificar la decisión. Acá va:

| Componente                               | Tipo                                            | Por qué                                                                                                                                                                                                                                        |
|------------------------------------------|-------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Scheduler`                              | **Hilo**                                        | Lee y modifica el diccionario de pacientes constantemente. Compartir memoria es esencial; serializar el estado en cada tick mataría la performance.                                                                                            |
| `DeadlockDetector`                       | **Hilo**                                        | Necesita inspeccionar el wait-for graph en vivo, que vive en `HospitalState`. Imposible sin memoria compartida.                                                                                                                                |
| `Farmacia` (productores/consumidores)    | **Hilos**                                       | Comparten el bounded buffer (`queue.Queue`). Es el caso de libro de cuándo usar hilos.                                                                                                                                                         |
| `Historia Clínica` (lectores/escritores) | **Hilos**                                       | Comparten el lock del recurso (`_write_lock`) y el contador de lectores. Implementación del protocolo de Courtois.                                                                                                                             |
| UI (Tkinter)                             | **Hilo principal**                              | Tkinter no es thread-safe; tiene que ser el hilo principal.                                                                                                                                                                                    |
| `log_daemon`                             | **Proceso separado** (`multiprocessing.Process`)| Hace I/O a disco intensivo y **no necesita memoria compartida**. Aislarlo en su propio espacio de direcciones replica el patrón UNIX de `syslogd`, demuestra **IPC real** (con `multiprocessing.Queue`) y si crashea no se lleva al SO entero. |

> **La regla que aplicamos:** hilos cuando hay estado compartido caliente; procesos cuando hay aislamiento natural o I/O independiente. Esto está documentado como comentario en `main.py`.

### Primitivas de sincronización usadas

```python
# En core/state.py:

self.lock = threading.RLock()                       # exclusión mutua del estado
self.ready_cv = threading.Condition(self.lock)      # scheduler duerme acá (sin polling)
self.cpu_sem = threading.Semaphore(num_cpus)        # N CPUs disponibles
self.resources = {
    "QUIROFANO": threading.Lock(),                  # mutex de recurso
    "CIRUJANO":  threading.Lock(),
}
self.pharmacy_queue = queue.Queue(maxsize=8)        # bounded buffer (farmacia)
self.log_in_queue  = mp.Queue()                     # IPC con proceso daemon
self.log_out_queue = mp.Queue()                     # IPC vuelta desde daemon
```

### Conceptos demostrados (en vivo, no animados)

1. **Hilos concurrentes:** scheduler, detector, productores y consumidores corren simultáneamente.
2. **Procesos concurrentes con IPC:** demonio de log en un `mp.Process` separado, comunicación por `mp.Queue`.
3. **Exclusión mutua (mutex):** `RLock` protege el estado. Sin esto, dos hilos modificando pacientes causarían race conditions.
4. **Condition variables:** `ready_cv` evita busy-wait en el scheduler — duerme hasta que llegue un READY.
5. **Semáforos contadores:** `cpu_sem = Semaphore(N)` limita cuántos procesos están RUNNING simultáneamente.
6. **Locks reales sobre recursos:** quirófano y cirujano son `threading.Lock()`, no simulaciones gráficas.
7. **Productor-consumidor con bounded buffer:** Farmacia con `queue.Queue(maxsize=8)`.
8. **Lectores-Escritores (Courtois 1971):** Historia Clínica con N lectores concurrentes y escritor exclusivo, implementado con dos locks y contador.
9. **Deadlock real:** dos hilos tomando dos locks en orden invertido. Es un deadlock que el SO detectaría como tal.
10. **Detección y recuperación:** DFS sobre wait-for graph, terminación de proceso víctima (menor prioridad).
11. **Métricas reales:** acumuladores `ready_acc`, `running_acc`, `blocked_acc` actualizados en cada transición. Nada inventado.

### Hilos vivos durante la ejecución

| Hilo / Proceso                         | Cantidad | Tipo                     |
|----------------------------------------|----------|--------------------------|
| UI Tkinter                             | 1        | Hilo principal           |
| Scheduler                              | 1        | Hilo daemon              |
| DeadlockDetector                       | 1        | Hilo daemon              |
| Log bridge                             | 1        | Hilo daemon              |
| Productores Farmacia                   | 2        | Hilos daemon             |
| Consumidores Farmacia                  | 3        | Hilos daemon             |
| Lectores / Escritores Historia Clínica | variable | Hilos daemon (on-demand) |
| Workers de deadlock demo               | 2        | Hilos daemon (on-demand) |
| **log_daemon**                         | **1**    | **Proceso separado**     |

---

## Parte 4 — Pendiente

> **En desarrollo.** Esta parte (ataque que explore una vulnerabilidad conocida + componente de ingeniería social, con políticas para repelerlo) se entrega como documento aparte y todavía está en proceso. Esta sección se actualizará cuando esté lista.

---

## Estructura del proyecto

```
Simulador-SO/
├── main.py                    # Entry point: arranca scheduler, detector, daemon y UI
├── core/
│   ├── state.py              # HospitalState: estado global + primitivas de sincronización
│   ├── scheduler.py          # Hilo del scheduler (Round Robin / Priority)
│   ├── deadlock.py           # Hilo detector de deadlock (DFS sobre wait-for graph)
│   ├── log_daemon.py         # Proceso separado de logging (IPC con mp.Queue)
│   ├── metrics.py            # Cálculo de métricas desde acumuladores reales
│   ├── dscript.py            # Intérprete de comandos de Recepción
│   └── ai_brain.py           # Chatbot: respuestas locales por palabras clave
├── ui/
│   ├── desktop.py            # Escritorio y dock
│   ├── window_base.py        # Sistema de ventanas flotantes
│   ├── hospital_app.py       # Panel principal
│   ├── process_app.py        # Historia Clínica
│   ├── terminal_app.py       # Recepción
│   ├── log_app.py            # Bitácora
│   ├── pharmacy_app.py       # Productor-Consumidor
│   ├── readers_app.py        # Lectores-Escritores (protocolo Courtois)
│   ├── metrics_app.py        # Panel de métricas
│   ├── ai_app.py             # Chatbot
│   ├── wordle_app.py         # Wordle (proceso interactivo)
│   ├── snake_app.py          # Snake (proceso interactivo)
│   ├── boot_screen.py        # Pantalla de arranque
│   └── theme.py              # Paleta de colores y tipografía
└── assets/
    ├── icons/                # Íconos PNG del dock
    └── wordle/               # Diccionarios de palabras (objetivos y válidas)
```

---

## Limitaciones conocidas

- El deadlock dura 10 segundos antes de auto-resolverse si nadie toca el botón. Es a propósito, para que se vea el cartel rojo en la defensa.
- La IA requiere conexión a internet y API key. Sin eso, modo offline con respuestas básicas.
- Las ventanas se pueden arrastrar pero no redimensionar.

