#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import platform as plt
import sys
from collector.graph import refresh


class ConnectionFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        # first layer: title or image
        title = tk.Label(self, text='VisualCLR')
        title.grid(row=0, column=0, columnspan=4)

        # second layer: dropdown list
        process_title = tk.Label(self, text='Процессы:')
        process_title.grid(row=1, column=0, columnspan=1)

        controller.active_pid = tk.IntVar(self)

        processes = tk.OptionMenu(self, controller.active_pid, *(controller.processes.keys()))
        processes.grid(row=1, column=1, columnspan=3)

        # third layer: buttons
        btn_connect = tk.Button(self, text='Подключиться')
        def connect_cb(event):
            print(f'Connecting to {controller.active_pid.get()}...')
            controller.queues.start \
                .put(controller.processes[controller.active_pid.get()])
            controller.event_generate('<<StartSession>>')

        btn_connect.bind('<Button-1>', connect_cb)
        btn_connect.grid(row=2, column=0, columnspan=2)

        btn_exit = tk.Button(self, text='Выход')
        def exit_cb(event):
            controller.server.stop(None).wait()
            processes = set(controller.processes.keys())
            for process in processes:
                controller.queues.finish.put(process)
                controller.event_generate('<<FinishSession>>')
            controller.destroy()

        btn_exit.bind('<Button-1>', exit_cb)
        btn_exit.grid(row=2, column=2, columnspan=2)

        def update_cb(event):
            pids = set(controller.processes.keys())
            processes['menu'].delete(0, 'end')
            for pid in pids:
                processes['menu'].add_command(label=pid, command=tk._setit(controller.active_pid, pid))

        self.bind('<<UpdateList>>', update_cb)


class MonitorFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        # tabs
        tabsystem = ttk.Notebook(self)

        tabs = [
            CommonFrame(tabsystem, controller),
            LogsFrame(tabsystem, controller),
            MetricsFrame(tabsystem, controller),
            ObjectsFrame(tabsystem, controller),
        ]

        for tab in tabs:
            tabsystem.add(tab, text=tab.text)
        tabsystem.grid(row=0, column=0, columnspan=4)

        def back_cb(event):
            controller.event_generate('<<FinishActiveSession>>')
            controller.show_frame(ConnectionFrame)

        btn_back = tk.Button(self, text='Назад')
        btn_back.bind('<Button-1>', back_cb)
        btn_back.grid(row=1, column=0, columnspan=4)


class CommonFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        self.pid = tk.StringVar(self, 'PID:')
        pid = tk.Label(self, textvariable=self.pid)
        pid.pack()

        self.cmd = tk.StringVar(self, 'CMD:')
        cmd = tk.Label(self, textvariable=self.cmd)
        cmd.pack()

        self.path = tk.StringVar(self, 'PATH:')
        path = tk.Label(self, textvariable=self.path, wraplength=400)
        path.pack()

        self.sdks = tk.StringVar(self, 'SDKs:')
        sdks = tk.Label(self, textvariable=self.sdks, wraplength=400)
        sdks.pack()

        self.rts = tk.StringVar(self, 'Runtimes:')
        rts = tk.Label(self, textvariable=self.rts, wraplength=400)
        rts.pack()

        osystem = tk.Label(self, text=f'ОС: {plt.platform()}')
        osystem.pack()

        bits = tk.Label(self, text=f'Разрядность: {plt.architecture()[0]}')
        bits.pack()

        arch = tk.Label(self, text=f'Архитектура: {plt.machine()}')
        arch.pack()

        version = sys.version.split('\n')[0].strip()
        pyversion = tk.Label(self, text=f'Python v{version}')
        pyversion.pack()

        self.text = 'Общая информация'
        controller.common = self


class LogsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        self.logs = tk.Text(self, wrap=None, font='roboto 8')
        self.logs.bind("<Key>", lambda e: "break")
        self.logs.pack()

        self.text = 'Логи'
        controller.traces = self


class MetricsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        UPDATE_TIMEOUT=1000
        VALUES_LIMIT = 11

        # threads number
        threads = tk.Frame(self)
        self.threads = [0] * VALUES_LIMIT
        self.thread = tk.IntVar(threads, 0)
        threads.after(UPDATE_TIMEOUT,
            lambda: refresh(threads, self.threads, self.thread, 'Число потоков', VALUES_LIMIT, UPDATE_TIMEOUT))
        threads.pack()

        self.text = 'Метрики'
        controller.metrics = self


class ObjectsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)


        self.text = 'Объекты'
        controller.objects = self
