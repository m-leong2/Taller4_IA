"""python main.py abre el menú; -t permite trabajar sin ventana gráfica."""
import argparse
import sys
from runner import POINTS, PROFILES, run
from view.text_display import display


def parser():
    p = argparse.ArgumentParser(description='Taller 4 - Observatorio Seguro')
    p.add_argument('-p', '--point', type=int, choices=POINTS, default=1)
    p.add_argument('-l', '--layout', help='CSP: control, precedencias, jornada o triangulo')
    p.add_argument('--profile', choices=PROFILES, help='Puntos 1–3: variante del buscador')
    p.add_argument('--compare', action='store_true', help='Punto 3: comparar los tres perfiles')
    p.add_argument('--case', choices=['autorizacion', 'bloqueo', 'informacion_insuficiente'],
                   default='autorizacion', help='Punto 5: conjunto de hechos')
    p.add_argument('--query', help='Consulta atómica; ejemplo: Autorizada(?t,?f)')
    p.add_argument('-t', '--text', action='store_true', help='Resultados en terminal, sin Tkinter')
    p.add_argument('--steps', action='store_true', help='Incluir pasos en la salida de texto')
    p.add_argument('-x', '--frame-time', type=float, default=0.5, help='Segundos por paso gráfico')
    return p


def execute(args):
    if not 0.05 <= args.frame_time <= 10:
        raise ValueError('El tiempo por paso debe estar entre 0.05 y 10 segundos')
    if args.point <= 3 and (args.query is not None or args.case != 'autorizacion'):
        raise ValueError('case y query son opciones del punto 5')
    report = run(args)
    if args.text:
        display(report, args.steps)
    else:
        from view.graphics_display import show
        show(report, args.frame_time)


def main():
    if len(sys.argv) == 1:
        from menu import launch
        launch()
        return
    p = parser()
    try:
        execute(p.parse_args())
    except (ValueError, OSError, NotImplementedError) as error:
        p.error(str(error))


if __name__ == '__main__':
    main()
