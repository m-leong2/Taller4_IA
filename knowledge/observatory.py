"""Punto 4. Cinco reglas comunes a todos los casos de Observatorio Seguro."""
from models.logic import Rule, atom


def build_rules():
    """Retorna una tupla de cinco Rule. Los hechos se cargan desde los escenarios.

    Condiciones del observatorio:
    R1. Un técnico es competente para una tarea si está asignado a ella,
        la tarea requiere una especialidad y él está habilitado en esa especialidad.
    R2. Una tarea está preparada en una franja si está en una zona con aislamiento
        confirmado y ausencia de alerta confirmada para esa misma franja.
    R3. Se autoriza una tarea si está programada en esa franja, su técnico asignado
        está disponible y es competente para ella, y la tarea está preparada.
    R4. Se bloquea una tarea programada si su zona tiene una alerta en esa franja.
    R5. Se bloquea una tarea programada si el aislamiento de su zona falló en esa franja.

    Predicados (argumentos en este orden):
      Asignado(tarea, persona), Requiere(tarea, especialidad),
      Habilitado(persona, especialidad), Competente(persona, tarea),
      EnZona(tarea, zona), AislamientoConfirmado(zona, franja),
      SinAlertaConfirmada(zona, franja), Preparada(tarea, franja),
      Programada(tarea, franja), Disponible(persona, franja),
      Autorizada(tarea, franja), Alerta(zona, franja),
      AislamientoFallido(zona, franja), Bloqueada(tarea, franja).

    Tips:
    - atom('Competente', '?p', '?t') construye el átomo Competente(p, t).
      En el código, '?p' y '?t' son variables; 'ana' es una constante.
      En el PDF use variables sin '?' y los cuantificadores universales.
    - Rule(nombre, descripcion, premisas, conclusion) recibe una tupla de
      objetos Atom como premisas y un Atom como conclusión. La tupla representa
      la conjunción; las variables de la regla se interpretan universalmente.
    """
    r1 = Rule(
        "R1",
        "Técnico competente si está asignado a la tarea, la tarea requiere una especialidad y está habilitado en ella.",
        (
            atom("Asignado", "?t", "?p"),
            atom("Requiere", "?t", "?e"),
            atom("Habilitado", "?p", "?e"),
        ),
        atom("Competente", "?p", "?t"),
    )

    r2 = Rule(
        "R2",
        "Tarea preparada en una franja si su zona tiene aislamiento confirmado y sin alerta confirmada en esa franja.",
        (
            atom("EnZona", "?t", "?z"),
            atom("AislamientoConfirmado", "?z", "?f"),
            atom("SinAlertaConfirmada", "?z", "?f"),
        ),
        atom("Preparada", "?t", "?f"),
    )

    r3 = Rule(
        "R3",
        "Tarea autorizada si está programada en la franja, su técnico asignado está disponible y es competente, y está preparada.",
        (
            atom("Programada", "?t", "?f"),
            atom("Asignado", "?t", "?p"),
            atom("Disponible", "?p", "?f"),
            atom("Competente", "?p", "?t"),
            atom("Preparada", "?t", "?f"),
        ),
        atom("Autorizada", "?t", "?f"),
    )

    r4 = Rule(
        "R4",
        "Tarea programada bloqueada si su zona tiene una alerta en esa franja.",
        (
            atom("Programada", "?t", "?f"),
            atom("EnZona", "?t", "?z"),
            atom("Alerta", "?z", "?f"),
        ),
        atom("Bloqueada", "?t", "?f"),
    )

    r5 = Rule(
        "R5",
        "Tarea programada bloqueada si el aislamiento de su zona falló en esa franja.",
        (
            atom("Programada", "?t", "?f"),
            atom("EnZona", "?t", "?z"),
            atom("AislamientoFallido", "?z", "?f"),
        ),
        atom("Bloqueada", "?t", "?f"),
    )

    return (r1, r2, r3, r4, r5)
    # FIN DEL BLOQUE DEL ESTUDIANTE
