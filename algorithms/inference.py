"""Punto 5. Inferencia mediante encadenamiento hacia adelante."""
from models.logic import match_premises, substitute


def forward_chain(kb):
    """Retorna una tupla con los hechos originales y derivados, sin duplicados.

    Cada ronda usa los hechos disponibles al comenzarla. La base de entrada
    debe conservarse.
    kb.facts contiene objetos Atom; kb.rules contiene objetos Rule con los
    atributos premises y conclusion. Los hechos se comparan directamente.

    Tips:
    - match_premises(regla.premises, hechos) genera (sustitución, hechos usados).
      Si no hay coincidencias, no genera resultados. La sustitución es un
      diccionario, por ejemplo {'?p': 'ana'}.
    - substitute(regla.conclusion, sustitución) retorna un nuevo objeto Atom
      con las variables reemplazadas por los valores de la sustitución.
    """
    facts = set(kb.facts)
    new_facts = set()

    while True:
        for rule in kb.rules:
            for substitution, used_facts in match_premises(rule.premises, facts):
                new_fact = substitute(rule.conclusion, substitution)
                if new_fact not in facts:
                    new_facts.add(new_fact)
        if not new_facts:
            break
        facts.update(new_facts)
        new_facts.clear()

    return tuple(facts)
 
"""
Al revisar el código con IA, se encontró que la lógica funcionaba correctamente, 
pero faltaba devolver los resultados. Por eso, se sugirió utilizar break para 
finalizar el ciclo y retornar los hechos al final de la función. Se mantuvo la 
estructura original porque no necesitaba cambios adicionales.

def forward_chain(kb):
    facts = set(kb.facts)
    new_facts = set()

    while True:
        for rule in kb.rules:
            for substitution, used_facts in match_premises(rule.premises, facts):
                new_fact = substitute(rule.conclusion, substitution)
                if new_fact not in facts:
                    new_facts.add(new_fact)
        if not new_facts:
            return tuple(facts)
        facts.update(new_facts)
        new_facts.clear()
"""
 
    
    # FIN DEL BLOQUE DEL ESTUDIANTE
