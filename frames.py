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
            ThreadsFrame(tabsystem, controller),
            GcFrame(tabsystem, controller),
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

        UPDATE_TIMEOUT = 2000
        VALUES_LIMIT = 11
        PLOT_SIZE = (5, 2.5)

        # threads number
        threads = tk.Frame(self)
        self.threads = [0] * VALUES_LIMIT
        self.thread = tk.IntVar(threads, 0)
        threads.after(UPDATE_TIMEOUT,
            lambda: refresh(threads, self.threads, self.thread, 'Число потоков: {:.0f}', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='g', figsize=PLOT_SIZE))
        threads.grid(row=0, column=0)

        # exceptions number
        exceptions = tk.Frame(self)
        self.exceptions = [0] * VALUES_LIMIT
        self.exception = tk.IntVar(exceptions, 0)
        exceptions.after(UPDATE_TIMEOUT,
            lambda: refresh(exceptions, self.exceptions, self.exception, 'Выброшено исключений: {:.0f}', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='r', figsize=PLOT_SIZE))
        exceptions.grid(row=0, column=1)

        # cpu usage
        cpu = tk.Frame(self)
        self.cpus = [0.0] * VALUES_LIMIT
        self.cpu = tk.StringVar(cpu, '0.0')
        cpu.after(UPDATE_TIMEOUT,
            lambda: refresh(cpu, self.cpus, self.cpu, 'CPU, {:.2f}%', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='b', figsize=PLOT_SIZE))
        cpu.grid(row=1, column=0)

        # memory usage
        memory = tk.Frame(self)
        self.memories = [0.0] * VALUES_LIMIT
        self.memory = tk.StringVar(memory, '0.0')
        memory.after(UPDATE_TIMEOUT,
            lambda: refresh(memory, self.memories, self.memory, 'Mem, {:.2f}Кб', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='#A0522D', figsize=PLOT_SIZE))
        memory.grid(row=1, column=1)

        # io usage
        io_read = tk.Frame(self)
        self.reads = [0.0] * VALUES_LIMIT
        self.read_kbytes = tk.StringVar(io_read, '0.0')
        io_read.after(UPDATE_TIMEOUT,
            lambda: refresh(io_read, self.reads, self.read_kbytes, 'Прочитано, {}Кб', VALUES_LIMIT, UPDATE_TIMEOUT, difference=True,
            color='#20B2AA', figsize=PLOT_SIZE))
        io_read.grid(row=2, column=0)

        io_write = tk.Frame(self)
        self.writes = [0.0] * VALUES_LIMIT
        self.write_kbytes = tk.StringVar(io_write, '0.0')
        io_write.after(UPDATE_TIMEOUT,
            lambda: refresh(io_write, self.writes, self.write_kbytes, 'Записано, {}Кб', VALUES_LIMIT, UPDATE_TIMEOUT, difference=True,
            color='#DB7093', figsize=PLOT_SIZE))
        io_write.grid(row=2, column=1)

        self.text = 'Метрики'
        controller.metrics = self


class ObjectsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)


        self.text = 'Объекты'
        controller.objects = self


class ThreadsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        # thread info
        thread_info = tk.Frame(self, highlightthickness=10)
        info_headers = {
            'pid': 'PID:',
            'state': 'Состояние:',
            'created': 'Создан:',
            'destroyed': 'Завершен:'
        }
        pid = tk.StringVar(thread_info, f'{info_headers["pid"]} ?')
        pid_w = tk.Label(thread_info, textvariable=pid)
        pid_w.grid(row=0, column=0, sticky='w')
        state = tk.StringVar(thread_info, f'{info_headers["state"]} ?')
        state_w = tk.Label(thread_info, textvariable=state)
        state_w.grid(row=1, column=0, sticky='w')
        created = tk.StringVar(thread_info, f'{info_headers["created"]} ?')
        created_w = tk.Label(thread_info, textvariable=created)
        created_w.grid(row=2, column=0, sticky='w')
        destroyed = tk.StringVar(thread_info, f'{info_headers["destroyed"]} ?')
        destroyed_w = tk.Label(thread_info, textvariable=destroyed)
        destroyed_w.grid(row=3, column=0, sticky='w')

        thread_info.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)

        # threads list
        thread_selector = tk.Frame(self)
        self.listv = tk.Variable(thread_selector, value=[])
        thread_listbox = tk.Listbox(thread_selector, listvariable=self.listv, selectmode=tk.SINGLE)
        thread_listbox.pack(side=tk.LEFT, fill=tk.BOTH)
        threads_scroller = tk.Scrollbar(thread_selector, command=thread_listbox.yview)
        threads_scroller.pack(side=tk.RIGHT, fill=tk.Y)
        thread_listbox.config(yscrollcommand=threads_scroller.set)
        thread_selector.pack(side=tk.LEFT, fill=tk.BOTH)

        def thread_select(event):
            thread_listbox = event.widget
            selection = thread_listbox.curselection()
            if not selection:
                return
            index = int(selection[0])
            thread_id = thread_listbox.get(index)
            pid.set(f'{info_headers["pid"]} {thread_id}')

            thread = controller.threads_data[thread_id]
            state.set(f'{info_headers["state"]} {thread["state"]}')
            created.set(f'{info_headers["created"]} {thread["created"]}')
            destroyed.set(f'{info_headers["destroyed"]} {thread["destroyed"]}')
        thread_listbox.bind('<<ListboxSelect>>', thread_select)

        self.text = 'Потоки'
        controller.threads = self


class GcFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        UPDATE_TIMEOUT = 2000
        VALUES_LIMIT = 21
        PLOT_SIZE = (8, 2)

        # gen 0
        gen0_header = tk.Label(self, text='GC Generation 0 (Поколение 0)', anchor='w')
        gen0_header.pack(fill=tk.BOTH, expand=1, padx=10)
        gen0 = tk.Frame(self)
        self.usage_gen0 = [0.0] * VALUES_LIMIT
        self.current_gen0 = tk.StringVar(gen0, '0.0')
        gen0.after(UPDATE_TIMEOUT,
            lambda: refresh(
                gen0, self.usage_gen0, self.current_gen0, 'Gen 0: {:.2f}Кб',VALUES_LIMIT, UPDATE_TIMEOUT,
                color='r', figsize=PLOT_SIZE))
        gen0.pack(fill=tk.BOTH, expand=1)

        # gen 1
        gen1_header = tk.Label(self, text='GC Generation 1 (Поколение 1)', anchor='w')
        gen1_header.pack(fill=tk.BOTH, expand=1, padx=10)
        gen1 = tk.Frame(self)
        self.usage_gen1 = [0.0] * VALUES_LIMIT
        self.current_gen1 = tk.StringVar(gen1, '0.0')
        gen1.after(UPDATE_TIMEOUT,
            lambda: refresh(gen1, self.usage_gen1, self.current_gen1, 'Gen 1: {:.2f}Кб', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='r', figsize=PLOT_SIZE))
        gen1.pack(fill=tk.BOTH, expand=1)

        # gen 2
        gen2_header = tk.Label(self, text='GC Generation 2 (Поколение 2)', anchor='w')
        gen2_header.pack(fill=tk.BOTH, expand=1, padx=10)
        gen2 = tk.Frame(self)
        self.usage_gen2 = [0.0] * VALUES_LIMIT
        self.current_gen2 = tk.StringVar(gen2, '0.0')
        gen2.after(UPDATE_TIMEOUT,
            lambda: refresh(gen2, self.usage_gen2, self.current_gen2, 'Gen 2: {:.2f}Кб', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='r', figsize=PLOT_SIZE))
        gen2.pack(fill=tk.BOTH, expand=1)

        # gc large-object heap
        loh_header = tk.Label(self, text='Large-object heap (Куча больших объектов)', anchor='w')
        loh_header.pack(fill=tk.BOTH, expand=1, padx=10)
        loh = tk.Frame(self)
        self.usage_loh = [0.0] * VALUES_LIMIT
        self.current_loh = tk.StringVar(loh, '0.0')
        loh.after(UPDATE_TIMEOUT,
            lambda: refresh(loh, self.usage_loh, self.current_loh, 'LOH: {:.2f}Кб', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='r', figsize=PLOT_SIZE))
        loh.pack(fill=tk.BOTH, expand=1)

        # gc pinned-object heap
        poh_header = tk.Label(self, text='Pinned-object heap (Куча закрепленных объектов)', anchor='w')
        poh_header.pack(fill=tk.BOTH, expand=1, padx=10)
        poh = tk.Frame(self)
        self.usage_poh = [0.0] * VALUES_LIMIT
        self.current_poh = tk.StringVar(poh, '0.0')
        loh.after(UPDATE_TIMEOUT,
            lambda: refresh(poh, self.usage_poh, self.current_poh, 'POH: {:.2f}Кб', VALUES_LIMIT, UPDATE_TIMEOUT,
            color='r', figsize=PLOT_SIZE))
        poh.pack(fill=tk.BOTH, expand=1)

        self.text = 'GC'
        controller.gc = self
