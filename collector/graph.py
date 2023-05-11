import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

def _plot_graph(target: tk.Frame, x: list, y: list, title: str, color: str = 'b'):
    fig = Figure(figsize=(4,2), dpi=70)
    fig.suptitle(title.format(y[-1]))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(x, y, color=color, marker='o')
    ax.grid()

    canvas = FigureCanvasTkAgg(fig, master=target)
    canvas.draw()

    gwidget = canvas.get_tk_widget()
    gwidget.pack()
    for slave in target.slaves()[:-1]:
        slave.destroy()


def refresh(master: tk.Frame, values: list, value, title: str, limit: int = 10, timeout: int = 0, difference: bool = False, color: str = 'b'):
    values.pop(0)
    next_value = float(value.get())
    if difference:
        next_value -= values[-1]
    values.append(next_value)
    _plot_graph(master, list(range(limit)), values, title, color)
    if timeout > 0:
        master.after(timeout, lambda: refresh(master, values, value, title, limit, timeout, difference, color))
