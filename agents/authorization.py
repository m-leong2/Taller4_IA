"""Punto 5. La prioridad de bloqueo es una regla operativa suministrada."""
from models.logic import atom


def select_action(facts, task, slot):
    """Retorna 'suspender', 'autorizar' o 'solicitar_verificacion'.

    El bloqueo tiene prioridad sobre la autorización.

    Entradas: facts contiene los objetos Atom retornados por forward_chain.
    task y slot son valores concretos de texto, por ejemplo 'inspeccion' y '2'.
    En la parte lógica las franjas son texto; en el CSP son enteros.

    Tips:
    - atom('Bloqueada', task, slot) construye el hecho que puede buscar en facts.
    """
    # TODO: Add your code here
    raise NotImplementedError
    # FIN DEL BLOQUE DEL ESTUDIANTE
