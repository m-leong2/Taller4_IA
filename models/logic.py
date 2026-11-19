"""Átomos, reglas y sustituciones sin símbolos de función. Módulo suministrado."""
from dataclasses import dataclass
import re


def is_variable(term):
    return term.startswith('?')


@dataclass(frozen=True)
class Atom:
    predicate: str
    arguments: tuple[str, ...]

    def __str__(self):
        return f'{self.predicate}({", ".join(self.arguments)})'

    @property
    def variables(self):
        return tuple(dict.fromkeys(t for t in self.arguments if is_variable(t)))


def atom(predicate, *arguments):
    return Atom(predicate, tuple(arguments))


def parse_atom(text):
    """Solo consultas atómicas: Autorizada(inspeccion,2) o Autorizada(?t,?f)."""
    match = re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*)\(\s*([^()]*)\s*\)', text.strip())
    if not match:
        raise ValueError('Consulta esperada: Predicado(argumento, argumento)')
    args = tuple(x.strip() for x in match[2].split(',')) if match[2].strip() else ()
    if any(not re.fullmatch(r'\??[A-Za-z0-9_]+', x) for x in args):
        raise ValueError('Los argumentos deben ser constantes o variables con ?')
    return Atom(match[1], args)


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    premises: tuple[Atom, ...]
    conclusion: Atom

    def __post_init__(self):
        body_variables = {v for p in self.premises for v in p.variables}
        if not set(self.conclusion.variables) <= body_variables:
            raise ValueError(f'Variable de conclusión sin premisa en {self.name}')

@dataclass(frozen=True)
class KnowledgeBase:
    facts: tuple[Atom, ...]
    rules: tuple[Rule, ...]

    def __post_init__(self):
        if any(f.variables for f in self.facts):
            raise ValueError('Los hechos deben ser cerrados, sin variables')
        if len(set(self.facts)) != len(self.facts):
            raise ValueError('Hechos iniciales repetidos')
        if len({r.name for r in self.rules}) != len(self.rules):
            raise ValueError('Identificadores de reglas repetidos')
        arities = {}
        for expression in (*self.facts, *(a for r in self.rules for a in (*r.premises, r.conclusion))):
            arity = arities.setdefault(expression.predicate, len(expression.arguments))
            if arity != len(expression.arguments):
                raise ValueError(f'Aridad inconsistente: {expression.predicate}')

    def validate_query(self, query):
        expressions = (*self.facts, *(a for r in self.rules for a in (*r.premises, r.conclusion)))
        for expression in expressions:
            if expression.predicate == query.predicate:
                if len(expression.arguments) != len(query.arguments):
                    raise ValueError('Aridad incorrecta en la consulta')
                return
        raise ValueError(f'Predicado desconocido: {query.predicate}')


def resolve(term, substitution):
    while is_variable(term) and term in substitution:
        term = substitution[term]
    return term


def substitute(expression, substitution):
    return atom(expression.predicate, *(resolve(t, substitution) for t in expression.arguments))


def unify(left, right, substitution=None):
    """Retorna una sustitución nueva o None. Términos: variables y constantes."""
    if left.predicate != right.predicate or len(left.arguments) != len(right.arguments):
        return None
    result = dict(substitution or {})
    for first, second in zip(left.arguments, right.arguments):
        first, second = resolve(first, result), resolve(second, result)
        if first == second:
            continue
        if is_variable(first):
            result[first] = second
        elif is_variable(second):
            result[second] = first
        else:
            return None
    return result


def match_premises(premises, facts, substitution=None, matched=()):
    """Genera (sustitución, hechos usados) con las mismas ligaduras en toda regla."""
    current = dict(substitution or {})
    if not premises:
        yield current, matched
        return
    for fact in facts:
        extended = unify(premises[0], fact, current)
        if extended is not None:
            yield from match_premises(premises[1:], facts, extended, matched + (fact,))


def ask(facts, query):
    """Respuestas sin duplicados. Una consulta cerrada probada retorna [{}]."""
    answers = []
    for fact in facts:
        substitution = unify(query, fact)
        if substitution is not None:
            answer = {v: resolve(v, substitution) for v in query.variables}
            if answer not in answers:
                answers.append(answer)
    return answers


@dataclass(frozen=True)
class Derivation:
    conclusion: Atom
    rule: Rule
    substitution: dict
    premises: tuple[Atom, ...]
    round: int


class InferenceTrace:
    """Conserva la primera justificación de cada hecho, fuera del algoritmo."""

    def __init__(self):
        self.derivations = []
        self.proofs = {}

    def record(self, conclusion, rule, substitution, premises, round_number):
        derivation = Derivation(conclusion, rule, dict(substitution), tuple(premises), round_number)
        self.proofs[conclusion] = derivation
        self.derivations.append(derivation)


@dataclass
class InferenceResult:
    facts: tuple[Atom, ...]
    trace: InferenceTrace


def describe_inference(kb, facts):
    """Justifica los hechos retornados; no agrega conclusiones a la solución.

    La presentación reconstruye una derivación válida por niveles. No representa
    el orden de ejecución interno de la implementación del estudiante.
    """
    facts = tuple(facts)
    if len(facts) != len(set(facts)) or not set(kb.facts) <= set(facts):
        raise ValueError('El resultado debe conservar los hechos iniciales sin duplicados')
    remaining = set(facts) - set(kb.facts)
    justified = list(kb.facts)
    trace = InferenceTrace()
    rounds = 0
    while remaining:
        new = []
        for rule in kb.rules:
            for substitution, premises in match_premises(rule.premises, justified):
                conclusion = substitute(rule.conclusion, substitution)
                if conclusion in remaining and conclusion not in new:
                    new.append(conclusion)
                    trace.record(conclusion, rule, substitution, premises, rounds + 1)
        if not new:
            raise ValueError('Hay conclusiones retornadas que no se justifican con la base')
        justified.extend(new)
        remaining.difference_update(new)
        rounds += 1
    return InferenceResult(facts, trace)
