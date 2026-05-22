"""
Demonio de logging del Hospital MS.

Corre en un PROCESO SEPARADO (no hilo) usando multiprocessing.
Esto demuestra IPC real (Inter-Process Communication) con multiprocessing.Queue.

Justificación del diseño hilos vs procesos:

- Los hilos del scheduler, detector de deadlock, productores y consumidores
  COMPARTEN MEMORIA (el HospitalState). Por eso son hilos: necesitan ver y
  modificar las mismas estructuras (pacientes, recursos, locks) sin overhead
  de serialización.

- El demonio de logging NO necesita modificar el estado: solo recibe eventos,
  los enriquece con timestamp, los persiste a disco (journaling) y los devuelve
  formateados. Es un trabajo I/O bound que puede vivir en su propio espacio
  de direcciones. Aislarlo en un proceso significa que:
    * Si el daemon crashea, el simulador sigue vivo.
    * El I/O de escritura a disco no compite por el GIL con los hilos del kernel.
    * Demuestra el patrón clásico de UNIX: kernel produce eventos, demonio
      en otro proceso (tipo syslogd) los persiste.

La comunicación es por dos multiprocessing.Queue:
  - in_queue:  padre -> daemon  (eventos crudos)
  - out_queue: daemon -> padre  (eventos enriquecidos para la UI)
"""

import time
import os


def log_daemon(in_queue, out_queue, log_file_path: str):
    """
    Entry point del proceso de logging.

    Lee mensajes de in_queue, los enriquece con timestamp, los escribe al
    archivo de log (journaling) y los devuelve por out_queue para que la UI
    los muestre.

    Termina cuando recibe None (señal de shutdown).
    """
    # Header de boot del log, marca el inicio de la sesión
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"  HOSPITAL MS — Sesión iniciada {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  PID daemon de logging: {os.getpid()}\n")
            f.write("=" * 60 + "\n")
            f.flush()
    except Exception:
        pass

    # Aviso de arranque al proceso padre, para que la UI sepa que el daemon vive
    try:
        out_queue.put(f"[logd] Demonio de logging activo (PID={os.getpid()})", timeout=1.0)
    except Exception:
        pass

    while True:
        try:
            msg = in_queue.get(timeout=0.5)
        except Exception:
            # timeout: seguir esperando
            continue

        if msg is None:
            # señal de shutdown
            break

        try:
            tag, body = msg
        except Exception:
            tag, body = "SYS", str(msg)

        ts = time.strftime("%H:%M:%S")
        enriched = f"[{ts}] [{tag}] {body}"

        # Persistir a disco (journaling)
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(enriched + "\n")
                f.flush()
        except Exception:
            pass

        # Devolver al padre para que la UI lo pinte
        try:
            out_queue.put(enriched, timeout=0.5)
        except Exception:
            # Si la cola de salida está saturada, descartamos (el archivo ya lo tiene)
            pass

    # Despedida en el archivo
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] [logd] Demonio de logging detenido.\n")
            f.flush()
    except Exception:
        pass