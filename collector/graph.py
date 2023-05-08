import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

def _plot_graph(target: tk.Frame, x: list, y: list, title: str):
    fig = Figure(figsize=(4,2), dpi=70)
    fig.suptitle(title)
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(x, y, marker='o')
    ax.grid()

    canvas = FigureCanvasTkAgg(fig, master=target)
    canvas.draw()

    gwidget = canvas.get_tk_widget()
    gwidget.pack()
    for slave in target.slaves()[:-1]:
        slave.destroy()


def refresh(master: tk.Frame, values: list, value, title: str, limit: int = 10, timeout: int = 0):
    values.pop(0)
    values.append(float(value.get()))
    _plot_graph(master, list(range(limit)), values, title)
    if timeout > 0:
        master.after(timeout, lambda: refresh(master, values, value, title, limit, timeout))
