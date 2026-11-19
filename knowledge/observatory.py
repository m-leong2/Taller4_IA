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
    # TODO: Add your code here
    raise NotImplementedError
    # FIN DEL BLOQUE DEL ESTUDIANTE
