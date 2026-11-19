"""Menú de terminal; las visualizaciones se ejecutan en un proceso separado."""
from pathlib import Path
import subprocess
import sys

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Label, Select, Static

from runner import POINTS, PROFILES, load_csp

ROOT = Path(__file__).resolve().parent
CASES = [('Autorización', 'autorizacion'), ('Bloqueo', 'bloqueo'),
         ('Información insuficiente', 'informacion_insuficiente')]


class WorkshopMenu(App):
    TITLE = 'Observatorio Seguro — Taller 4'
    ENABLE_COMMAND_PALETTE = False
    CSS = '''
    Screen { background: #0d1117; color: #e6edf3; }
    #title { height: 3; padding: 0 2; background: #161b22; content-align: left middle; }
    #body { height: 1fr; }
    #points { width: 33; border-right: solid #30363d; padding: 1; }
    #options { width: 1fr; padding: 1 2; }
    .point { width: 100%; height: 4; background: #161b22; }
    .active { border: solid #f0c040; background: #1c2836; }
    Label { margin-top: 1; color: #58a6ff; }
    Select { width: 100%; }
    #csp-options, #logic-options, #profile-options, #display-options { height: auto; }
    #purpose { height: auto; margin-bottom: 1; }
    #actions { height: 3; margin: 0 2; }
    #actions Button { margin-right: 1; }
    #status { height: auto; max-height: 5; padding: 1 2; }
    '''
    BINDINGS = [('q', 'quit', 'Salir'), ('r', 'run', 'Ejecutar')]

    def compose(self) -> ComposeResult:
        yield Static('OBSERVATORIO SEGURO · Taller 4', id='title')
        with Horizontal(id='body'):
            with VerticalScroll(id='points'):
                for point, name in POINTS.items():
                    yield Button(f'{point}. {name}', id=f'point-{point}', classes='point')
            with VerticalScroll(id='options'):
                yield Static('', id='purpose')
                with VerticalScroll(id='csp-options'):
                    yield Label('Instancia', id='layout-label')
                    yield Select([(load_csp('control').name, 'control')],
                                 value='control', allow_blank=False, id='layout')
                    with VerticalScroll(id='profile-options'):
                        yield Label('Algoritmo')
                        yield Select([(name, key) for key, name in PROFILES.items()],
                                     value='basic', allow_blank=False, id='profile')
                with VerticalScroll(id='logic-options'):
                    yield Label('Caso')
                    yield Select(CASES, value='autorizacion', allow_blank=False, id='case')
                with VerticalScroll(id='display-options'):
                    yield Label('Visualización')
                    yield Select([('Texto en terminal', 'text'), ('Gráfica', 'graphics')],
                                 value='graphics', allow_blank=False, id='display')
        with Horizontal(id='actions'):
            yield Button('Ejecutar', id='run', variant='primary')
            yield Button('Salir', id='quit')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self):
        self.point = 1
        self.update_options()

    def update_options(self):
        for point in POINTS:
            self.query_one(f'#point-{point}', Button).set_class(point == self.point, 'active')
        descriptions = {
            1: 'Comprobar la programación de control mediante retroceso.',
            2: 'Observar la reducción de dominios y los límites de AC-3.',
            3: 'Observar el efecto de MRV, grado y LCV sobre la búsqueda.',
            5: 'Seguir una derivación y justificar la decisión del agente.',
        }
        self.query_one('#purpose', Static).update(descriptions[self.point])
        self.query_one('#csp-options').display = self.point <= 3
        self.query_one('#logic-options').display = self.point == 5
        self.query_one('#profile-options').display = self.point in (2, 3)
        if self.point <= 3:
            layouts = {1: ['control'], 2: ['precedencias', 'triangulo'],
                       3: ['precedencias', 'jornada']}[self.point]
            layout = self.query_one('#layout', Select)
            layout.set_options([(load_csp(name).name, name) for name in layouts])
            layout.value = {1: 'control', 2: 'precedencias', 3: 'jornada'}[self.point]
            layout.display = self.point != 1
            self.query_one('#layout-label').display = self.point != 1
            keys = {1: ['basic'], 2: ['basic', 'ac3'], 3: list(PROFILES)}[self.point]
            options = [(PROFILES[key], key) for key in keys]
            if self.point == 3:
                options.append(('Comparar los tres algoritmos', 'compare'))
            profile = self.query_one('#profile', Select)
            profile.set_options(options)
            profile.value = {1: 'basic', 2: 'ac3', 3: 'compare'}[self.point]
        self.query_one('#status', Static).update('')
        self.query_one('#status').display = False

    def on_button_pressed(self, event):
        if event.button.id.startswith('point-'):
            if not self.query_one('#run', Button).disabled:
                self.point = int(event.button.id.split('-')[1])
                self.update_options()
        elif event.button.id == 'quit':
            self.exit()
        elif event.button.id == 'run':
            self.action_run()

    def command(self):
        command = [sys.executable, '-X', 'utf8', str(ROOT / 'main.py'), '-p', str(self.point)]
        if self.point <= 3:
            command += ['-l', self.query_one('#layout', Select).value]
            profile = self.query_one('#profile', Select).value
            if profile == 'compare':
                command += ['--compare']
            else:
                command += ['--profile', profile]
        else:
            command += ['--case', self.query_one('#case', Select).value]
        if self.query_one('#display', Select).value == 'text':
            command.append('-t')
            if self.point == 5:
                command.append('--steps')
        return command

    def action_run(self):
        button = self.query_one('#run', Button)
        if button.disabled:
            return
        command = self.command()
        button.disabled = True
        if '-t' in command:
            try:
                with self.suspend():
                    try:
                        subprocess.run(command, cwd=ROOT)
                        input('\nPulse Enter para volver al menú...')
                    except (OSError, EOFError, KeyboardInterrupt) as error:
                        print(f'Ejecución finalizada: {error}')
            finally:
                button.disabled = False
        else:
            self.query_one('#status', Static).update('Cierre la visualización para volver al menú.')
            self.query_one('#status').display = True
            self.run_graphics(command)

    @work(thread=True)
    def run_graphics(self, command):
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            message = 'Visualización cerrada.' if result.returncode == 0 else result.stderr.strip()
        except OSError as error:
            message = str(error)
        self.call_from_thread(self.finish_run, message)

    def finish_run(self, message):
        self.query_one('#status', Static).update(message)
        self.query_one('#status').display = True
        self.query_one('#run', Button).disabled = False


def launch():
    WorkshopMenu().run()
