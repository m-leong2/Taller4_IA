"""Carga escenarios y conecta las funciones evaluadas con las vistas."""
from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter

from algorithms.csp import (ac3, backtracking_search,
                            order_domain_values, select_unassigned_variable)
from algorithms.inference import forward_chain
from agents.authorization import select_action
from knowledge.observatory import build_rules
from models.csp import SchedulingCSP, SearchTrace, copy_domains
from models.logic import KnowledgeBase, ask, atom, describe_inference, parse_atom

ROOT = Path(__file__).resolve().parent
POINTS = {1: 'Formulación y retroceso', 2: 'Propagación de restricciones',
          3: 'Heurísticas para CSP',
          5: 'Inferencia y agente lógico'}
PROFILES = {
    'basic': 'Retroceso básico',
    'ac3': 'AC-3 inicial + retroceso',
    'heuristics': 'AC-3 inicial + retroceso con MRV/grado/LCV',
}


@dataclass
class SearchResult:
    profile: str
    solution: dict | None
    trace: SearchTrace
    seconds: float
    domains_before_search: dict


def csp_layouts():
    return sorted(path.stem for path in (ROOT / 'layouts/csp').glob('*.json'))


def load_csp(layout):
    if layout not in csp_layouts():
        raise ValueError(f'Instancia desconocida: {layout}')
    return SchedulingCSP.load(ROOT / 'layouts/csp' / f'{layout}.json')


def solve_csp(problem, profile, record=True):
    if profile not in PROFILES:
        raise ValueError(f'Perfil desconocido: {profile}')
    trace = SearchTrace(record)
    domains = copy_domains(problem.domains)
    trace.record('initial', 'Dominios iniciales; disponibilidades ya aplicadas.', {}, domains)
    start = perf_counter()
    possible = ac3(problem, domains) if profile in ('ac3', 'heuristics') else True
    if profile in ('ac3', 'heuristics'):
        trace.record('preprocessed', 'Dominios después de AC-3.', {}, domains)
    if possible:
        solution = backtracking_search(
            problem, domains,
            select_unassigned_variable if profile == 'heuristics' else None,
            order_domain_values if profile == 'heuristics' else None, trace)
    else:
        solution = None
    elapsed = perf_counter() - start
    final_domains = ({x: [solution[x]] for x in problem.variables}
                     if solution is not None else domains)
    trace.record('solution' if solution is not None else 'unsatisfiable',
                 'Programación completa.' if solution is not None else 'No existe solución.',
                 solution or {}, final_domains)
    if solution is not None and not problem.is_solution(solution):
        raise ValueError('El buscador devolvió una asignación inválida')
    return SearchResult(profile, solution, trace, elapsed, copy_domains(domains))


def load_logic(case):
    data = json.loads((ROOT / 'layouts/logic/observatorio.json').read_text(encoding='utf-8'))
    if case not in data['cases']:
        raise ValueError(f'Caso desconocido: {case}')
    variant = data['cases'][case]
    facts = [atom(*entry) for entry in data['facts']]
    for entry in variant['remove']:
        facts.remove(atom(*entry))
    for entry in variant['add']:
        fact = atom(*entry)
        if fact not in facts:
            facts.append(fact)
    return KnowledgeBase(tuple(facts), build_rules()), data


def run(args):
    if args.point <= 3:
        layout = args.layout or ('control' if args.point == 1 else 'precedencias')
        profile = args.profile or {1: 'basic', 2: 'ac3', 3: 'heuristics'}[args.point]
        allowed = {1: ('basic',), 2: ('basic', 'ac3'), 3: tuple(PROFILES)}
        if profile not in allowed[args.point]:
            raise ValueError('Ese perfil requiere funciones de un punto posterior')
        if args.compare and args.point != 3:
            raise ValueError('--compare corresponde al punto 3')
        problem = load_csp(layout)
        # La comparación mide los algoritmos sin copiar fotografías ni animar.
        comparison = [solve_csp(problem, p, False) for p in PROFILES] if args.compare else []
        result = solve_csp(problem, profile, record=not args.text or args.steps)
        return dict(point=args.point, problem=problem,
                    result=result, comparison=comparison)

    if args.layout is not None or args.profile is not None or args.compare:
        raise ValueError('layout, profile y compare son opciones de CSP (puntos 1–3)')
    kb, data = load_logic(args.case)
    task, slot = data['default_task'], data['default_slot']
    schedule = atom('Programada', task, slot)
    if schedule not in kb.facts:
        raise ValueError('La tarea y franja deben pertenecer a la programación de referencia')
    query = parse_atom(args.query) if args.query else atom('Autorizada', task, slot)
    kb.validate_query(query)
    report = dict(point=args.point, kb=kb, data=data, case=args.case,
                  task=task, slot=slot, query=query, custom_query=bool(args.query))
    result = describe_inference(kb, forward_chain(kb))
    report.update(inference=result, answers=ask(result.facts, query),
                  action=select_action(result.facts, task, slot))
    return report
