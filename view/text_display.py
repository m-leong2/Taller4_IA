"""Resultados y explicaciones necesarios para responder el taller."""
from models.logic import atom
from runner import PROFILES

ACTION_LABELS = {'autorizar': 'AUTORIZAR', 'suspender': 'SUSPENDER',
                 'solicitar_verificacion': 'SOLICITAR VERIFICACIÓN'}
VARIABLE_LABELS = {'?t': 'Tarea', '?p': 'Persona', '?e': 'Especialidad',
                   '?z': 'Zona', '?f': 'Franja'}


def fact_text(fact):
    """Expresa en lenguaje natural los predicados definidos en el enunciado."""
    a, b = fact.arguments
    formats = {
        'Asignado': 'La tarea {a} está asignada a {b}.',
        'Requiere': '{a} requiere la especialidad {b}.',
        'Habilitado': 'Habilitación confirmada: {a}, especialidad {b}.',
        'Competente': '{a} cumple los requisitos de especialidad para {b}.',
        'EnZona': '{a} se realiza en la zona {b}.',
        'AislamientoConfirmado': 'Aislamiento confirmado en {a}, franja {b}.',
        'SinAlertaConfirmada': 'Ausencia de alerta confirmada en {a}, franja {b}.',
        'Preparada': 'Las condiciones de la zona de {a} están verificadas para la franja {b}.',
        'Programada': '{a} está programada en la franja {b}.',
        'Disponible': '{a} está disponible en la franja {b}.',
        'Autorizada': '{a} está autorizada en la franja {b}.',
        'Alerta': 'Alerta confirmada en {a}, franja {b}.',
        'AislamientoFallido': 'El aislamiento de {a} falló en la franja {b}.',
        'Bloqueada': '{a} está bloqueada en la franja {b}.',
    }
    return formats[fact.predicate].format(a=a, b=b)


def comparison_rows(results):
    return [(PROFILES[r.profile], r.trace.metrics.attempts,
             r.trace.metrics.backtracks, f'{r.seconds:.6f}') for r in results]


def answer_text(query, answers):
    if not answers:
        return 'No demostrada.'
    if not query.variables:
        return 'Demostrada.'
    return '\n'.join(', '.join(f'{VARIABLE_LABELS.get(key, key)}: {value}'
                                for key, value in answer.items()) for answer in answers)


def decision_summary(report):
    task, slot = report['task'], report['slot']
    facts = report['inference'].facts
    authorized = atom('Autorizada', task, slot) in facts
    blocked = atom('Bloqueada', task, slot) in facts
    if authorized and blocked:
        return 'Se derivaron autorización y bloqueo. La prioridad dada es suspender.'
    if blocked:
        proof = report['inference'].trace.proofs.get(atom('Bloqueada', task, slot))
        causes = [fact_text(f) for f in proof.premises
                  if f.predicate in ('Alerta', 'AislamientoFallido')] if proof else []
        return 'Hay un bloqueo demostrado para esta tarea y franja.' + (
            ' ' + ' '.join(causes) if causes else '')
    if authorized:
        return 'Las condiciones de autorización están demostradas.'
    zones = [f.arguments[1] for f in facts if f.predicate == 'EnZona' and f.arguments[0] == task]
    missing = []
    for zone in zones:
        for predicate, condition in (('AislamientoConfirmado', 'el aislamiento'),
                                     ('SinAlertaConfirmada', 'la ausencia de alertas')):
            if atom(predicate, zone, slot) not in facts:
                missing.append(f'Falta confirmar {condition} en {zone} para la franja {slot}.')
    return 'No se demostró autorización ni bloqueo.' + (' ' + ' '.join(missing) if missing else '')


def logic_summary(report):
    facts, task, slot = report['inference'].facts, report['task'], report['slot']
    authorized = 'demostrada' if atom('Autorizada', task, slot) in facts else 'no demostrada'
    blocked = 'demostrado' if atom('Bloqueada', task, slot) in facts else 'no demostrado'
    lines = [f'Intervención: {task} · Franja {slot}',
            report['data']['cases'][report['case']]['description'],
            f'Autorización: {authorized}', f'Bloqueo: {blocked}',
            f'Acción: {ACTION_LABELS[report["action"]]}']
    if report['custom_query']:
        lines.extend(['', f'Consulta: {report["query"]}',
                      answer_text(report['query'], report['answers'])])
    return lines


def relevant_derivations(report):
    return [d for d in report['inference'].trace.derivations
            if (d.conclusion.predicate == 'Competente'
                and d.conclusion.arguments[1] == report['task'])
            or (d.conclusion.predicate in ('Preparada', 'Autorizada', 'Bloqueada')
                and d.conclusion.arguments == (report['task'], report['slot']))]


def precedence_text(problem):
    relations = [f'{c.left} < {c.right}' for c in problem.constraints if c.kind == 'before']
    return 'Precedencias: ' + (', '.join(relations) if relations else 'ninguna')


def display(report, show_steps=False):
    print(f'OBSERVATORIO SEGURO | Punto {report["point"]}')
    if report['point'] <= 3:
        problem, result = report['problem'], report['result']
        print(f'{problem.name}\n{PROFILES[result.profile]}')
        print(precedence_text(problem))
        if report['point'] == 1:
            for task in problem.tasks:
                print(f'{task.name}: técnico {task.technician}, zona {task.zone}, dominio {list(task.slots)}')
        if report['point'] == 2:
            print('Tarea | Dominio inicial | Antes del retroceso')
            for task in problem.tasks:
                print(f'{task.name} | {problem.domains[task.name]} | {result.domains_before_search[task.name]}')
        if report['comparison']:
            print('\nAlgoritmo | Intentos | Retrocesos | Tiempo (s)')
            for row in comparison_rows(report['comparison']):
                print(' | '.join(map(str, row)))
        print('\nProgramación encontrada:' if result.solution is not None else '\nNo existe solución.')
        if result.solution is not None:
            for task in problem.tasks:
                print(f'  {task.name}: franja {result.solution[task.name]}')
        if report['point'] != 1 and not report['comparison']:
            metrics = result.trace.metrics
            print(f'Intentos: {metrics.attempts} | Retrocesos: {metrics.backtracks}')
        if show_steps:
            for event in result.trace.events:
                print(f'{event["message"]} {event["assignment"]}')
        return

    print('\n'.join(logic_summary(report)))
    if show_steps:
        print('\nDerivación hacia adelante:')
        for derivation in relevant_derivations(report):
            print(f'  {derivation.rule.name}: {derivation.rule.description}')
            for premise in derivation.premises:
                print(f'    {fact_text(premise)}')
            print('    Conclusión: ' + fact_text(derivation.conclusion))
            print('    Sustitución: ' + ', '.join(f'{key} = {value}'
                  for key, value in derivation.substitution.items()))
