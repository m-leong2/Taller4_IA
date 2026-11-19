"""Visualizaciones del proceso: agenda CSP e inferencia del agente."""
import sys
import tkinter as tk
from tkinter import ttk

from models.logic import atom
from runner import POINTS, PROFILES
from view.text_display import (ACTION_LABELS, comparison_rows, decision_summary,
                               fact_text, logic_summary, precedence_text,
                               relevant_derivations)

BG, INK = '#e8eef5', '#17365d'
GREEN, ORANGE, RED = '#d8efe1', '#fff0cf', '#f9dce0'


def prepare_windows():
    """Evita que el escalado de Windows saque la ventana de la pantalla."""
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def configure_style(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background=BG)
    style.configure('TLabel', background=BG, foreground=INK, font=('Segoe UI', 10))
    style.configure('TButton', font=('Segoe UI', 10), padding=5)
    style.configure('Playback.TButton', font=('Segoe UI Symbol', 14, 'bold'), padding=3)
    style.configure('TNotebook', background=BG)
    style.configure('TNotebook.Tab', font=('Segoe UI', 10), padding=(10, 6))
    style.configure('Treeview', rowheight=32, font=('Segoe UI', 10))
    style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))


def vertical_scroll(parent, widget):
    """Reserva espacio para la barra solo cuando el contenido lo necesita."""
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    scroll = ttk.Scrollbar(parent, orient='vertical', command=widget.yview)
    widget.grid(row=0, column=0, sticky='nsew')

    def update(first, last):
        scroll.set(first, last)
        needed = float(last) - float(first) < 0.99999
        if needed and not scroll.winfo_manager():
            scroll.grid(row=0, column=1, sticky='ns')
        elif not needed and scroll.winfo_manager():
            scroll.grid_remove()

    widget.configure(yscrollcommand=update)


def wrapped_label(parent, text, padding=(12, 6)):
    label = ttk.Label(parent, text=text, padding=padding, anchor='w',
                      justify='left', wraplength=760)
    label.pack(fill='x')
    label.bind('<Configure>', lambda event: label.configure(wraplength=max(100, event.width - 24)))


def text_box(parent):
    holder = ttk.Frame(parent)
    holder.pack(fill='both', expand=True, padx=10, pady=8)
    widget = tk.Text(holder, width=1, height=1, wrap='word', font=('Consolas', 11), bg='white',
                     fg=INK, padx=12, pady=10, relief='flat')
    vertical_scroll(holder, widget)
    return widget


def set_text(widget, value):
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    widget.insert('1.0', value)
    widget.configure(state='disabled')


def comparison_table(parent, results):
    holder = ttk.Frame(parent)
    holder.pack(fill='both', expand=True, padx=12, pady=12)
    columns = ['Algoritmo', 'Intentos', 'Retrocesos', 'Tiempo (s)']
    table = ttk.Treeview(holder, columns=columns, show='headings', height=4)
    for column, width in zip(columns, [430, 100, 110, 130]):
        table.heading(column, text=column)
        table.column(column, width=width, minwidth=80, anchor='w')
    for row in comparison_rows(results):
        table.insert('', 'end', values=row)
    vertical_scroll(holder, table)


class Journey:
    """Reproduce la solución final por franjas, sin intervenir en la búsqueda."""

    def __init__(self, parent, problem, result, frame_time):
        self.parent, self.problem, self.solution = parent, problem, result.solution
        self.index, self.timer, self.playing, self.pulse = 0, None, False, 0
        self.duration = frame_time
        self.zones = list(dict.fromkeys(task.zone for task in problem.tasks))
        wrapped_label(parent, f'{problem.name} · {PROFILES[result.profile]}')
        wrapped_label(parent, 'Programación encontrada · Cada franja muestra las tareas que se realizan al mismo tiempo.'
                      if self.solution is not None else 'Sin solución · No hay una jornada para reproducir.',
                      padding=(12, 3))
        controls = ttk.Frame(parent)
        controls.pack(fill='x', padx=12, pady=8)
        for label, command in [('↺', self.reset), ('⏮', lambda: self.move(-1)),
                               ('▶', self.toggle), ('⏭', lambda: self.move(1))]:
            button = ttk.Button(controls, text=label, width=3, command=command,
                                style='Playback.TButton')
            button.pack(side='left', padx=2)
            button.bind('<space>', lambda event: self.keyboard(self.toggle))
            if label == '▶':
                self.play_button = button
            elif label == '⏮':
                self.previous_button = button
            elif label == '⏭':
                self.next_button = button
        self.status = ttk.Label(controls)
        self.status.pack(side='left', padx=12)
        self.timeline = tk.Canvas(parent, height=56, bg=BG, highlightthickness=0)
        self.timeline.pack(fill='x', padx=12)
        holder = ttk.Frame(parent)
        holder.pack(fill='both', expand=True, padx=12, pady=(4, 8))
        self.canvas = tk.Canvas(holder, bg='#f6f9fd', highlightthickness=0)
        vertical_scroll(holder, self.canvas)
        self.canvas.bind('<Configure>', lambda event: self.render())
        self.timeline.bind('<Configure>', lambda event: self.render())
        self.summary = ttk.Label(parent, padding=(12, 8))
        self.summary.pack(fill='x')
        self.render()

    def keyboard(self, action):
        action()
        return 'break'

    def render(self):
        if self.solution is None:
            self.status.configure(text='No existe una programación para reproducir.')
            for button in (self.play_button, self.previous_button, self.next_button):
                button.state(['disabled'])
            self.summary.configure(text='Revise el resultado de la búsqueda en la agenda.')
            return
        slots = self.problem.slots
        finished = self.index == len(slots)
        slot = None if finished else slots[self.index]
        completed = sum(slots.index(self.solution[t.name]) < self.index for t in self.problem.tasks)
        self.status.configure(text='Jornada completada' if finished else
                              f'Franja {slot} · ' + ('Reproduciendo' if self.playing else 'Pausado'))
        self.play_button.configure(text='⏸' if self.playing else '▶')
        self.previous_button.state(['disabled'] if self.index == 0 else ['!disabled'])
        self.next_button.state(['disabled'] if finished else ['!disabled'])
        self.summary.configure(text=f'Intervenciones completadas: {completed} de {len(self.problem.tasks)}')
        timeline = self.timeline
        timeline.delete('all')
        width = max(1, timeline.winfo_width())
        for i, value in enumerate(slots):
            x, end = i * width / len(slots) + 3, (i + 1) * width / len(slots) - 3
            fill = INK if i == self.index else GREEN if i < self.index else '#dce5ef'
            timeline.create_rectangle(x, 8, end, 48, fill=fill, outline='')
            timeline.create_text((x + end) / 2, 28, text=f'Franja {value}',
                                 fill='white' if i == self.index else INK,
                                 font=('Segoe UI', 11, 'bold'))
        canvas = self.canvas
        canvas.delete('all')
        width = max(1, canvas.winfo_width())
        if width <= 1:
            return
        columns = max(1, min(len(self.zones), int(width // 260)))
        card_width = width / columns
        row_top = 12
        for start in range(0, len(self.zones), columns):
            row_bottom = row_top + 240
            for col, zone in enumerate(self.zones[start:start + columns]):
                left, right = col * card_width + 10, (col + 1) * card_width - 10
                center = (left + right) / 2
                tasks = [t for t in self.problem.tasks if t.zone == zone]
                active = [t for t in tasks if self.solution[t.name] == slot]
                fill = '#e0f2eb' if active else 'white'
                border = '#2e907a' if active else '#d7e1ed'
                card = canvas.create_rectangle(left, row_top, right, row_top + 240,
                    fill=fill, outline=border, width=3 if active else 1)
                # Símbolos de las zonas: cúpula óptica, antena y tablero eléctrico.
                y = row_top + 24
                if zone == 'optica':
                    canvas.create_arc(center - 35, y, center + 35, y + 68, start=0, extent=180,
                                      fill='#7ca4c9', outline=INK, width=2)
                    canvas.create_rectangle(center - 35, y + 34, center + 35, y + 54,
                                            fill='#b5cbe0', outline=INK, width=2)
                    canvas.create_line(center, y + 32, center + 17, y + 7, fill=INK, width=5)
                elif zone == 'antena':
                    canvas.create_arc(center - 32, y, center + 32, y + 40, start=180, extent=180,
                                      fill='#b5cbe0', outline=INK, width=2)
                    canvas.create_line(center, y + 40, center, y + 54, fill=INK, width=4)
                    canvas.create_line(center - 20, y + 54, center + 20, y + 54, fill=INK, width=3)
                    canvas.create_line(center, y + 25, center + 22, y + 3, fill=INK, width=3)
                else:
                    canvas.create_rectangle(center - 28, y, center + 28, y + 54,
                                            fill='#b5cbe0', outline=INK, width=2)
                    canvas.create_line(center + 4, y + 8, center - 8, y + 28,
                                       center + 7, y + 28, center - 4, y + 46, fill=INK, width=4)
                canvas.create_text(center, y + 76, text=zone.capitalize(), fill=INK,
                                   font=('Segoe UI', 14, 'bold'))
                state = 'En intervención' if active else 'Completada' if all(
                    slots.index(self.solution[t.name]) < self.index for t in tasks) else 'Sin intervención en esta franja'
                badge = canvas.create_text(center, y + 106, text=state, fill=border if active else '#617184',
                    width=right - left - 28, font=('Segoe UI', 10, 'bold'), anchor='n')
                text_top = canvas.bbox(badge)[3] + 16
                details = '\n\n'.join(f'{t.label}\n{t.technician.capitalize()}' for t in active)
                if not active:
                    details = '\n'.join(f'{t.label} · franja {self.solution[t.name]}' for t in tasks)
                item = canvas.create_text(center, text_top, text=details, width=right - left - 32,
                    anchor='n', justify='center', fill=INK, font=('Segoe UI', 11))
                bottom = max(row_top + 240, canvas.bbox(item)[3] + 24)
                canvas.coords(card, left, row_top, right, bottom)
                if active:
                    canvas.create_oval(right - 25, row_top + 15, right - 15, row_top + 25,
                                       fill='#2e907a' if self.pulse % 2 == 0 else '#83cbb8', outline='')
                row_bottom = max(row_bottom, bottom)
            row_top = row_bottom + 16
        canvas.configure(scrollregion=(0, 0, width, max(canvas.winfo_height(), row_top)))
        if row_top <= canvas.winfo_height():
            canvas.yview_moveto(0)

    def pause(self):
        self.playing = False
        if self.timer is not None:
            self.parent.after_cancel(self.timer)
            self.timer = None
        self.render()

    def move(self, offset):
        self.pause()
        self.index = min(len(self.problem.slots), max(0, self.index + offset))
        self.render()

    def reset(self):
        self.pause()
        self.index = 0
        self.render()

    def toggle(self):
        if self.playing:
            self.pause()
        elif self.solution is not None:
            if self.index == len(self.problem.slots):
                self.index = 0
            self.playing, self.pulse = True, 0
            self.remaining = self.duration
            self.tick()

    def tick(self):
        self.timer = None
        if self.remaining == 0:
            self.pulse = 0
            self.index += 1
            if self.index == len(self.problem.slots):
                self.playing = False
                self.render()
                return
            self.remaining = self.duration
        self.render()
        self.pulse += 1
        delay = min(200, self.remaining)
        self.remaining -= delay
        self.timer = self.parent.after(delay, self.tick)


class Viewer:
    def __init__(self, root, report, frame_time=0.5):
        self.root, self.report = root, report
        self.frame_time = max(50, int(frame_time * 1000))
        self.index, self.timer = 0, None
        self.playing = False
        root.title(f'Observatorio Seguro | Punto {report["point"]}')
        root.geometry(f'{min(1060, root.winfo_screenwidth() - 80)}x'
                      f'{min(760, root.winfo_screenheight() - 100)}')
        root.minsize(900, 640)
        configure_style(root)
        tk.Label(root, text='OBSERVATORIO SEGURO', bg=INK, fg='white',
                 font=('Segoe UI', 17, 'bold'), padx=18, pady=10, anchor='w').pack(fill='x')
        ttk.Label(root, text=f'Punto {report["point"]} · {POINTS[report["point"]]}',
                  padding=(16, 8)).pack(anchor='w')
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        if report['point'] <= 3:
            self.build_csp()
        else:
            self.build_logic()
        root.bind('<Left>', lambda event: self.keyboard(lambda: self.move(-1),
                  lambda: self.journey.move(-1)))
        root.bind('<Right>', lambda event: self.keyboard(lambda: self.move(1),
                  lambda: self.journey.move(1)))
        root.bind('<space>', lambda event: self.keyboard(self.toggle))
        root.bind('<Home>', lambda event: self.keyboard(self.reset))
        root.bind('<End>', lambda event: self.keyboard(self.last))
        root.bind('r', lambda event: self.keyboard(self.reset))
        root.bind('R', lambda event: self.keyboard(self.reset))
        root.protocol('WM_DELETE_WINDOW', self.close)

    def tab(self, name):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=name)
        return frame

    def playback(self, parent):
        self.playback_page = parent
        controls = ttk.Frame(parent)
        controls.pack(fill='x', padx=10, pady=6)
        ttk.Button(controls, text='↺', command=self.reset, width=3,
                   style='Playback.TButton').pack(side='left', padx=(2, 5))
        self.previous_button = ttk.Button(controls, text='⏮', command=lambda: self.move(-1),
                                         width=3, style='Playback.TButton')
        self.previous_button.pack(side='left', padx=1)
        self.play_button = ttk.Button(controls, text='▶', command=self.toggle,
                                     width=3, style='Playback.TButton')
        self.play_button.pack(side='left', padx=1)
        self.next_button = ttk.Button(controls, text='⏭', command=lambda: self.move(1),
                                     width=3, style='Playback.TButton')
        self.next_button.pack(side='left', padx=1)
        self.play_state = ttk.Label(controls, width=14)
        self.play_state.pack(side='left', padx=(6, 4))
        for widget in controls.winfo_children():
            widget.bind('<space>', lambda event: self.keyboard(self.toggle))
        step = tk.Frame(parent, bg='#dbeafe', highlightbackground='#bad1ec',
                        highlightthickness=1)
        step.pack(fill='x', padx=10, pady=(2, 8))
        step.columnconfigure(1, weight=1)
        self.progress = tk.Label(step, bg=INK, fg='white', font=('Segoe UI', 10, 'bold'),
                                 padx=12, pady=8)
        self.progress.grid(row=0, column=0, sticky='nw', padx=(10, 14), pady=12)
        self.message = tk.Label(step, wraplength=760, justify='left', bg='#dbeafe', fg=INK,
                                font=('Segoe UI', 13, 'bold'), anchor='w')
        self.message.grid(row=0, column=1, sticky='ew', padx=(0, 12), pady=12)
        step.bind('<Configure>', lambda event: self.message.configure(
            wraplength=max(300, event.width - self.progress.winfo_reqwidth() - 40)))

    def build_csp(self):
        problem, result = self.report['problem'], self.report['result']
        self.events = result.trace.events
        if self.report['point'] == 2:
            page = self.tab('Dominios')
            wrapped_label(page, f'{problem.name} · {PROFILES[result.profile]}')
            wrapped_label(page, precedence_text(problem), padding=(12, 3))
            columns = ('Tarea', 'Dominio inicial', 'Antes del retroceso')
            holder = ttk.Frame(page)
            holder.pack(fill='x', padx=12, pady=12)
            self.domain_table = ttk.Treeview(holder, columns=columns, show='headings',
                                             height=min(5, len(problem.tasks)))
            for column in columns:
                self.domain_table.heading(column, text=column)
                self.domain_table.column(column, width=260)
            for task in problem.tasks:
                self.domain_table.insert('', 'end', values=(task.name,
                    str(problem.domains[task.name]), str(result.domains_before_search[task.name])))
            vertical_scroll(holder, self.domain_table)
            empty = any(not values for values in result.domains_before_search.values())
            status = ('AC-3 detectó un dominio vacío.' if empty else 'AC-3 no produjo dominios vacíos.')
            if result.profile == 'basic':
                status = 'Retroceso sin preprocesamiento de dominios.'
            status += (' El retroceso encontró una solución.' if result.solution is not None
                       else ' No existe una programación válida.')
            wrapped_label(page, status, padding=12)
        page = self.tab('Agenda')
        wrapped_label(page, f'{problem.name} · {PROFILES[result.profile]}')
        wrapped_label(page, precedence_text(problem), padding=(12, 3))
        self.playback(page)
        self.summary = ttk.Label(page, padding=(12, 8))
        self.summary.pack(side='bottom', fill='x')
        self.agenda_header = tk.Canvas(page, height=44, bg='white', highlightthickness=0)
        self.agenda_header.pack(fill='x', padx=10, pady=(5, 0))
        holder = ttk.Frame(page)
        holder.pack(fill='both', expand=True, padx=10, pady=(0, 5))
        self.canvas = tk.Canvas(holder, bg='white', highlightthickness=0)
        vertical_scroll(holder, self.canvas)
        self.canvas.bind('<Configure>', lambda event: self.render())
        if self.report['comparison']:
            comparison = self.tab('Comparación')
            ttk.Label(comparison, text=problem.name, padding=(12, 6)).pack(anchor='w')
            comparison_table(comparison, self.report['comparison'])
            self.notebook.select(comparison)
        if self.report['point'] == 3:
            self.journey = Journey(self.tab('Ver jornada'), problem, result, self.frame_time)
            self.notebook.bind('<<NotebookTabChanged>>', self.tab_changed)
        self.render()

    def tab_changed(self, event):
        if self.notebook.select() != str(self.journey.parent):
            self.journey.pause()
        else:
            self.pause()

    def build_logic(self):
        report = self.report
        self.events = relevant_derivations(report)
        result_page = self.tab('Resultado')
        set_text(text_box(result_page), '\n\n'.join(logic_summary(report)))
        page = self.tab('Hacia adelante')
        ttk.Label(page, text=f'{report["task"].capitalize()} · Franja {report["slot"]} · '
                  f'{report["case"].replace("_", " ")}', padding=(12, 6)).pack(anchor='w')
        self.playback(page)
        self.decision = tk.Label(page, bg='white', fg=INK, font=('Segoe UI', 12, 'bold'),
                                 wraplength=960, justify='left', padx=12, pady=12)
        self.decision.pack(side='bottom', fill='x', padx=10, pady=8)
        self.decision.bind('<Configure>', lambda event: self.decision.configure(
            wraplength=max(100, event.width - 24)))
        stages = ttk.Frame(page)
        stages.pack(fill='x', padx=10, pady=(0, 6))
        self.logic_stages = []
        for column, name in enumerate(('Técnico', 'Zona', 'Decisión')):
            stages.columnconfigure(column, weight=1, uniform='stage')
            label = tk.Label(stages, text=name, bg='#dce5ef', fg=INK,
                             font=('Segoe UI', 11, 'bold'), pady=8)
            label.grid(row=0, column=column, sticky='ew', padx=3)
            self.logic_stages.append(label)
        self.show_logic_details = tk.BooleanVar(value=False)
        self.logic_details_button = ttk.Checkbutton(page, text='Ver regla y sustitución',
            variable=self.show_logic_details, command=self.toggle_logic_details)
        self.logic_details_button.pack(anchor='w', padx=14, pady=4)
        self.logic_body = ttk.Frame(page)
        self.logic_body.pack(fill='both', expand=True)
        self.logic_body.columnconfigure(0, weight=1)
        self.logic_body.rowconfigure(0, weight=1)
        narrative = ttk.Frame(self.logic_body)
        narrative.grid(row=0, column=0, sticky='nsew')
        self.reasoning_text = text_box(narrative)
        self.reasoning_text.configure(font=('Segoe UI', 12))
        self.reasoning_text.tag_configure('conclusion', foreground='#17664f',
                                         font=('Segoe UI', 13, 'bold'))
        self.logic_details = ttk.Frame(self.logic_body)
        self.derivation_text = text_box(self.logic_details)
        self.render()

    def toggle_logic_details(self):
        if self.show_logic_details.get():
            self.logic_details.grid(row=1, column=0, sticky='nsew')
            self.logic_body.rowconfigure(1, weight=1)
        else:
            self.logic_details.grid_remove()
            self.logic_body.rowconfigure(1, weight=0)

    def render(self):
        self.sync_controls()
        if self.report['point'] <= 3:
            self.render_agenda()
        else:
            self.render_inference()

    def render_agenda(self):
        problem = self.report['problem']
        event = self.events[self.index]
        self.message.configure(text=event['message'])
        result = self.report['result']
        if self.index == len(self.events) - 1:
            metrics = result.trace.metrics
            status = 'Programación encontrada' if result.solution is not None else 'Sin solución'
            text = status if self.report['point'] == 1 else (
                f'{status} · Intentos: {metrics.attempts} · Retrocesos: {metrics.backtracks}')
            self.summary.configure(text=text)
        else:
            self.summary.configure(text='Búsqueda en curso')
        canvas = self.canvas
        canvas.delete('all')
        header = self.agenda_header
        header.delete('all')
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        label_width = min(460, max(280, width * 0.26))
        cell_width = (width - label_width - 24) / len(problem.slots)
        heading = header.create_text(14, 10, text='Intervención · técnico · zona', anchor='nw',
                                     width=label_width - 28, fill=INK, font=('Segoe UI', 10, 'bold'))
        headings = [heading]
        for col, slot in enumerate(problem.slots):
            headings.append(header.create_text(label_width + (col + .5) * cell_width, 10,
                anchor='n', width=cell_width - 12, text=f'Franja {slot}',
                fill=INK, font=('Segoe UI', 10, 'bold')))
        heading_height = max(header.bbox(item)[3] - header.bbox(item)[1] for item in headings)
        header.configure(height=max(44, heading_height + 20))
        previous = self.events[max(0, self.index - 1)]['domains']
        top = 0
        for task in problem.tasks:
            title = canvas.create_text(14, top + 8, text=f'{task.name} · {task.label}', anchor='nw',
                                       width=label_width - 28, fill=INK, font=('Segoe UI', 10, 'bold'))
            metadata = canvas.create_text(14, canvas.bbox(title)[3] + 8,
                text=f'{task.technician} · {task.zone}', anchor='nw',
                width=label_width - 28, fill='#617184', font=('Segoe UI', 9))
            row_height = max(72, canvas.bbox(metadata)[3] - top + 12)
            cells = []
            for col, slot in enumerate(problem.slots):
                left = label_width + col * cell_width
                available = slot in event['domains'][task.name]
                assigned = event['assignment'].get(task.name) == slot
                changed = (event['kind'] == 'preprocessed'
                           and slot in previous[task.name] and not available)
                active = event['variable'] == task.name and event['value'] == slot
                fill = GREEN if assigned else '#e8f0fc' if available else '#f3f4f6'
                text = 'Asignada' if assigned else 'En dominio' if available else '—'
                if changed or (active and event['kind'] == 'reject'):
                    fill, text = RED, 'Descartada'
                elif active and event['kind'] == 'attempt':
                    fill, text = ORANGE, 'Probar'
                item = canvas.create_text(left + cell_width / 2, top, text=text,
                    width=cell_width - 12, fill=INK, font=('Segoe UI', 10))
                row_height = max(row_height, canvas.bbox(item)[3] - canvas.bbox(item)[1] + 16)
                cells.append((left, fill, item))
            for left, fill, item in cells:
                canvas.coords(item, left + cell_width / 2, top + row_height / 2)
                background = canvas.create_rectangle(left + 4, top + 3, left + cell_width - 4,
                    top + row_height - 4, fill=fill, outline='#cbd5e1')
                canvas.tag_lower(background, item)
            top += row_height
        content_height = top + 8
        canvas.configure(scrollregion=(0, 0, width, max(height, content_height)))
        if content_height <= height:
            canvas.yview_moveto(0)

    def render_inference(self):
        report, kb = self.report, self.report['kb']
        complete = self.index == len(self.events) + 1
        derivation = self.events[self.index - 1] if 0 < self.index <= len(self.events) else None
        if complete:
            predicate = 'Bloqueada' if report['action'] == 'suspender' else 'Autorizada'
            derivation = report['inference'].trace.proofs.get(atom(predicate, report['task'], report['slot']))
        titles = {'R1': 'Comprobar la especialidad del técnico',
                  'R2': 'Comprobar las condiciones de la zona',
                  'R3': 'Comprobar la autorización de la tarea',
                  'R4': 'Comprobar si hay una alerta',
                  'R5': 'Comprobar si falló el aislamiento'}
        if derivation is not None:
            self.message.configure(text='Decisión final' if complete else titles[derivation.rule.name])
            premises = [fact_text(fact) for fact in derivation.premises]
            conclusion = '→ ' + fact_text(derivation.conclusion)
            details = [f'{derivation.rule.name} · {derivation.rule.description}',
                       ' ∧ '.join(map(str, derivation.rule.premises)) + ' → ' + str(derivation.rule.conclusion),
                       '', 'Sustitución:',
                       *(f'{key} = {value}' for key, value in derivation.substitution.items()),
                       '', 'Conclusión: ' + str(derivation.conclusion)]
        else:
            self.message.configure(text='Decisión final' if complete else 'Revisar los hechos disponibles')
            premises = [decision_summary(report) if complete else
                        report['data']['cases'][report['case']]['description'],
                        'Avance para ver cómo se aplican las reglas.' if not complete else '']
            conclusion = ''
            details = []
        set_text(self.reasoning_text, '\n\n'.join(p for p in premises if p)
                 + ('\n\n' + conclusion if conclusion else ''))
        if conclusion:
            self.reasoning_text.configure(state='normal')
            self.reasoning_text.tag_add('conclusion', f'end-{len(conclusion) + 1}c', 'end-1c')
            self.reasoning_text.configure(state='disabled')
        set_text(self.derivation_text, '\n'.join(details))
        self.logic_details_button.state(['!disabled'] if derivation else ['disabled'])
        if derivation:
            self.toggle_logic_details()
        else:
            self.logic_details.grid_remove()
            self.logic_body.rowconfigure(1, weight=0)
        known = set(kb.facts)
        known.update(d.conclusion for d in self.events[:min(self.index, len(self.events))])
        competent = any(f.predicate == 'Competente' and f.arguments[1] == report['task'] for f in known)
        prepared = atom('Preparada', report['task'], report['slot']) in known
        blocked = atom('Bloqueada', report['task'], report['slot']) in known
        for label, text, color in zip(self.logic_stages,
                ('Técnico · competente' if competent else 'Técnico · pendiente',
                 'Zona · bloqueo' if blocked else 'Zona · preparada' if prepared else 'Zona · pendiente',
                 ACTION_LABELS[report['action']] if complete else 'Decisión · pendiente'),
                (GREEN if competent else '#dce5ef', RED if blocked else GREEN if prepared else '#dce5ef',
                 (GREEN if report['action'] == 'autorizar' else RED if blocked else ORANGE)
                 if complete else '#dce5ef')):
            label.configure(text=text, bg=color)
        if complete:
            self.decision.configure(text=ACTION_LABELS[report['action']] + '\n' + decision_summary(report),
                                    bg=GREEN if report['action'] == 'autorizar' else
                                    RED if report['action'] == 'suspender' else ORANGE)
        else:
            self.decision.configure(text='Inferencia en curso', bg='white')

    def last_index(self):
        return len(self.events) - 1 if self.report['point'] <= 3 else len(self.events) + 1

    def keyboard(self, action, journey_action=None):
        if hasattr(self, 'journey') and self.notebook.select() == str(self.journey.parent):
            actions = {self.toggle: self.journey.toggle, self.reset: self.journey.reset,
                       self.last: lambda: self.journey.move(len(self.journey.problem.slots))}
            if journey_action is not None:
                journey_action()
                return 'break'
            if action in actions:
                actions[action]()
                return 'break'
        if self.notebook.select() == str(self.playback_page):
            action()
            return 'break'

    def sync_controls(self):
        self.progress.configure(text=f'Paso {self.index} de {self.last_index()}')
        self.play_button.configure(text='⏸' if self.playing else '▶')
        state = 'Reproduciendo' if self.playing else (
            'Finalizado' if self.index == self.last_index() else 'Pausado')
        self.play_state.configure(text=state)
        self.previous_button.state(['disabled'] if self.index == 0 else ['!disabled'])
        self.next_button.state(['disabled'] if self.index == self.last_index() else ['!disabled'])

    def move(self, offset):
        self.pause()
        self.index = min(self.last_index(), max(0, self.index + offset))
        self.render()

    def reset(self):
        self.pause()
        self.index = 0
        self.render()

    def last(self):
        self.pause()
        self.index = self.last_index()
        self.render()

    def play(self):
        self.pause()
        if self.index == self.last_index():
            self.index = 0
        self.playing = True
        self.render()
        self.timer = self.root.after(self.frame_time, self.tick)

    def toggle(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def tick(self):
        self.timer = None
        if not self.playing:
            return
        if self.index < self.last_index():
            self.index += 1
        if self.index == self.last_index():
            self.playing = False
        self.render()
        if self.playing:
            self.timer = self.root.after(self.frame_time, self.tick)

    def pause(self):
        self.playing = False
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.sync_controls()

    def close(self):
        if hasattr(self, 'journey'):
            self.journey.pause()
        self.pause()
        self.root.destroy()


def show(report, frame_time=0.5):
    prepare_windows()
    root = tk.Tk()
    Viewer(root, report, frame_time)
    root.mainloop()
