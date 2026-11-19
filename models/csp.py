"""Representación y registro del CSP. Módulo suministrado."""
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Task:
    name: str
    label: str
    technician: str
    zone: str
    slots: tuple[int, ...]


@dataclass(frozen=True)
class Constraint:
    left: str
    right: str
    kind: str

    def accepts(self, left_value, right_value):
        return left_value < right_value if self.kind == 'before' else left_value != right_value


class SchedulingCSP:
    """Variables: tareas. Valores: franjas. Solo restricciones unarias/binarias."""

    def __init__(self, data):
        self.name = data['name']
        self.slots = tuple(data['slots'])
        if not self.slots or any(type(s) is not int for s in self.slots):
            raise ValueError('Las franjas deben ser enteros')
        if tuple(sorted(set(self.slots))) != self.slots:
            raise ValueError('Las franjas deben ser distintas y estar ordenadas')
        self.tasks = tuple(Task(t['id'], t['label'], t['technician'], t['zone'],
                                tuple(t['slots'])) for t in data['tasks'])
        self.variables = tuple(t.name for t in self.tasks)
        if len(set(self.variables)) != len(self.variables):
            raise ValueError('Identificadores de tareas repetidos')
        self.domains = {t.name: list(t.slots) for t in self.tasks}
        for task in self.tasks:
            if len(set(task.slots)) != len(task.slots) or not set(task.slots) <= set(self.slots):
                raise ValueError(f'Dominio inválido: {task.name}')
        # Las disponibilidades ya están aplicadas en cada dominio del archivo.
        self.constraints = []
        for i, left in enumerate(self.tasks):
            for right in self.tasks[i + 1:]:
                if left.technician == right.technician or left.zone == right.zone:
                    self.constraints.append(Constraint(left.name, right.name, 'different'))
        for left, right in data.get('before', []):
            if left not in self.variables or right not in self.variables or left == right:
                raise ValueError('Precedencia inválida')
            self.constraints.append(Constraint(left, right, 'before'))
        self.neighbors = {
            x: tuple(y for y in self.variables if y != x and any(
                {c.left, c.right} == {x, y} for c in self.constraints))
            for x in self.variables
        }

    @classmethod
    def load(cls, path: Path):
        return cls(json.loads(path.read_text(encoding='utf-8')))

    def compatible(self, x, value, y, other):
        """Conjunción de restricciones; respeta la dirección de cada precedencia."""
        for constraint in self.constraints:
            if (constraint.left, constraint.right) == (x, y):
                if not constraint.accepts(value, other):
                    return False
            elif (constraint.left, constraint.right) == (y, x):
                if not constraint.accepts(other, value):
                    return False
        return True

    def consistent(self, variable, value, assignment):
        return value in self.domains[variable] and all(
            self.compatible(variable, value, other, assigned)
            for other, assigned in assignment.items() if other != variable)

    def is_solution(self, assignment):
        return assignment is not None and set(assignment) == set(self.variables) and all(
            self.consistent(x, value, assignment) for x, value in assignment.items())


def copy_domains(domains):
    """Copia las listas para conservar los dominios originales del problema."""
    return {variable: list(values) for variable, values in domains.items()}


@dataclass
class SearchMetrics:
    attempts: int = 0
    backtracks: int = 0


class SearchTrace:
    """Contadores y fotografías de la ejecución; no implementan búsqueda."""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.metrics = SearchMetrics()
        self.events = []

    def record(self, kind, message, assignment, domains, variable=None, value=None):
        if self.enabled:
            self.events.append(dict(kind=kind, message=message,
                                    assignment=dict(assignment), domains=copy_domains(domains),
                                    variable=variable, value=value))

    def attempt(self, assignment, domains, variable, value):
        self.metrics.attempts += 1
        self.record('attempt', f'Probar {variable} en la franja {value}.',
                    assignment, domains, variable, value)

    def restore(self, assignment, domains, variable):
        self.record('restore', f'Retroceder: recuperar la rama anterior a {variable}.',
                    assignment, domains, variable)

    def fail(self, assignment, domains):
        self.metrics.backtracks += 1
        self.record('failure', 'Se agotaron las opciones de esta rama.', assignment, domains)
