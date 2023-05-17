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
        title_pane = tk.Frame(self, pady=50)
        title = tk.Label(title_pane, text='VisualCLR')
        title.pack(fill=tk.X, expand=1)
        title_pane.pack(fill=tk.X)

        # second layer: dropdown list
        process_pane = tk.Frame(self, pady=10)
        process_title = tk.Label(process_pane, text='Процессы:')
        process_title.pack(side=tk.LEFT, fill=tk.X, expand=1)

        controller.active_pid = tk.IntVar(self)

        processes = tk.OptionMenu(process_pane, controller.active_pid, *(controller.processes.keys()))
        processes.pack(side=tk.LEFT, fill=tk.X, expand=1)
        process_pane.pack(fill=tk.X)

        # third layer: buttons
        btns_pane = tk.Frame(self, pady=10)
        btn_connect = tk.Button(btns_pane, text='Подключиться')
        def connect_cb(event):
            print(f'Connecting to {controller.active_pid.get()}...')
            controller.queues.start \
                .put(controller.processes[controller.active_pid.get()])
            controller.event_generate('<<StartSession>>')

        btn_connect.bind('<Button-1>', connect_cb)
        btn_connect.pack(side=tk.LEFT, fill=tk.X, expand=1)

        btn_exit = tk.Button(btns_pane, text='Выход')
        def exit_cb(event):
            controller.server.stop(None).wait()
            processes = set(controller.processes.keys())
            for process in processes:
                controller.queues.finish.put(process)
                controller.event_generate('<<FinishSession>>')
            controller.destroy()

        btn_exit.bind('<Button-1>', exit_cb)
        btn_exit.pack(side=tk.LEFT, fill=tk.X, expand=1)
        btns_pane.pack(fill=tk.X)

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

        self.logs = tk.Text(self, wrap=tk.CHAR, font='roboto 10')
        self.logs.bind("<Key>", lambda e: "break")
        self.logs.pack(fill=tk.BOTH, expand=1)

        self.text = 'Логи'
        controller.traces = self


class MetricsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        UPDATE_TIMEOUT = 2000
        self.VALUES_LIMIT = 11
        PLOT_SIZE = (5, 2.5)

        # threads number
        threads = tk.Frame(self)
        self.threads = [0] * self.VALUES_LIMIT
        self.thread = tk.IntVar(threads, 0)
        threads.after(UPDATE_TIMEOUT,
            lambda: refresh(threads, self.threads, self.thread, 'Число потоков: {:.0f}', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='g', figsize=PLOT_SIZE))
        threads.grid(row=0, column=0)

        # exceptions number
        exceptions = tk.Frame(self)
        self.exceptions = [0] * self.VALUES_LIMIT
        self.exception = tk.IntVar(exceptions, 0)
        exceptions.after(UPDATE_TIMEOUT,
            lambda: refresh(exceptions, self.exceptions, self.exception, 'Выброшено исключений: {:.0f}', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='r', figsize=PLOT_SIZE))
        exceptions.grid(row=0, column=1)

        # cpu usage
        cpu = tk.Frame(self)
        self.cpus = [0.0] * self.VALUES_LIMIT
        self.cpu = tk.StringVar(cpu, '0.0')
        cpu.after(UPDATE_TIMEOUT,
            lambda: refresh(cpu, self.cpus, self.cpu, 'CPU, {:.2f}%', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='b', figsize=PLOT_SIZE))
        cpu.grid(row=1, column=0)

        # memory usage
        memory = tk.Frame(self)
        self.memories = [0.0] * self.VALUES_LIMIT
        self.memory = tk.StringVar(memory, '0.0')
        memory.after(UPDATE_TIMEOUT,
            lambda: refresh(memory, self.memories, self.memory, 'Mem, {:.2f}Кб', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='#A0522D', figsize=PLOT_SIZE))
        memory.grid(row=1, column=1)

        # io usage
        io_read = tk.Frame(self)
        self.reads = [0.0] * self.VALUES_LIMIT
        self.read_kbytes = tk.StringVar(io_read, '0.0')
        io_read.after(UPDATE_TIMEOUT,
            lambda: refresh(io_read, self.reads, self.read_kbytes, 'Прочитано, {}Кб', self.VALUES_LIMIT, UPDATE_TIMEOUT, difference=True,
            color='#20B2AA', figsize=PLOT_SIZE))
        io_read.grid(row=2, column=0)

        io_write = tk.Frame(self)
        self.writes = [0.0] * self.VALUES_LIMIT
        self.write_kbytes = tk.StringVar(io_write, '0.0')
        io_write.after(UPDATE_TIMEOUT,
            lambda: refresh(io_write, self.writes, self.write_kbytes, 'Записано, {}Кб', self.VALUES_LIMIT, UPDATE_TIMEOUT, difference=True,
            color='#DB7093', figsize=PLOT_SIZE))
        io_write.grid(row=2, column=1)

        # loaded/unloaded classes and objects
        self.classes = tk.IntVar(self, 0)
        self.classes_v = tk.StringVar(self, 'Классов загружено: 0')
        classes = tk.Label(self, textvariable=self.classes_v)
        classes.grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)

        self.objects_disposed = tk.IntVar(self, 0)
        self.objects_disposed_v = tk.StringVar(self, 'Объектов освобождено: 0')
        objects_disposed = tk.Label(self, textvariable=self.objects_disposed_v)
        objects_disposed.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)

        self.classes_loaded = tk.IntVar(self, 0)
        self.classes_loaded_v = tk.StringVar(self, 'Всего классов загружено: 0')
        classes_loaded = tk.Label(self, textvariable=self.classes_loaded_v)
        classes_loaded.grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)

        self.classes_unloaded = tk.IntVar(self, 0)
        self.classes_unloaded_v = tk.StringVar(self, 'Всего классов выгружено: 0')
        classes_unloaded = tk.Label(self, textvariable=self.classes_unloaded_v)
        classes_unloaded.grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)

        self.text = 'Метрики'
        controller.metrics = self


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


class ObjectsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        def sort_column(tv: ttk.Treeview, column: str, reverse: bool = False, unboxer = lambda value: value):
            items = [(unboxer(tv.set(child, column)), child) for child in tv.get_children('')]
            items.sort(key=lambda item: item[0], reverse=reverse) # sort by value

            for index, (_, child) in enumerate(items):
                tv.move(child, '', index)

            tv.heading(column, command=lambda _column=column: \
                       sort_column(tv, _column, not reverse, unboxer))


        columns = ('class', 'total', 'retained') #, 'gen0', 'gen1', 'gen2', 'loh', 'poh')
        headings = ('Класс', 'Занимаемая память, Кб', 'Утекаемая память, Кб') #, 'Gen 0, Кб', 'Gen 1, Кб', 'Gen 2, Кб', 'LOH, Кб', 'POH, Кб')
        unboxers = (str, float, float)
        self.stats = ttk.Treeview(self, columns=columns, show='headings')
        for (column, heading, unboxer) in zip(columns, headings, unboxers):
            self.stats.heading(column, text=heading, command=lambda _column=column: \
                               sort_column(self.stats, _column, unboxer=unboxer))
        self.stats.pack(fill=tk.BOTH, expand=1)

        self.text = 'Объекты'
        controller.objects = self


class GcFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        UPDATE_TIMEOUT = 2000
        self.VALUES_LIMIT = 21
        PLOT_SIZE = (10, 2)

        # gen 0
        gen0_header = tk.Label(self, text='GC Generation 0 (Поколение 0)', anchor='w')
        gen0_header.pack(fill=tk.BOTH, expand=1, padx=10)
        gen0 = tk.Frame(self)
        self.usage_gen0 = [0.0] * self.VALUES_LIMIT
        self.current_gen0 = tk.StringVar(gen0, '0.0')
        gen0.after(UPDATE_TIMEOUT,
            lambda: refresh(
                gen0, self.usage_gen0, self.current_gen0, 'Gen 0: {:.2f}Кб',self.VALUES_LIMIT, UPDATE_TIMEOUT,
                color='#f6f64d', figsize=PLOT_SIZE))
        gen0.pack(fill=tk.BOTH, expand=1)

        # gen 1
        gen1_header = tk.Label(self, text='GC Generation 1 (Поколение 1)', anchor='w')
        gen1_header.pack(fill=tk.BOTH, expand=1, padx=10)
        gen1 = tk.Frame(self)
        self.usage_gen1 = [0.0] * self.VALUES_LIMIT
        self.current_gen1 = tk.StringVar(gen1, '0.0')
        gen1.after(UPDATE_TIMEOUT,
            lambda: refresh(gen1, self.usage_gen1, self.current_gen1, 'Gen 1: {:.2f}Кб', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='#ffcc25', figsize=PLOT_SIZE))
        gen1.pack(fill=tk.BOTH, expand=1)

        # gen 2
        gen2_header = tk.Label(self, text='GC Generation 2 (Поколение 2)', anchor='w')
        gen2_header.pack(fill=tk.BOTH, expand=1, padx=10)
        gen2 = tk.Frame(self)
        self.usage_gen2 = [0.0] * self.VALUES_LIMIT
        self.current_gen2 = tk.StringVar(gen2, '0.0')
        gen2.after(UPDATE_TIMEOUT,
            lambda: refresh(gen2, self.usage_gen2, self.current_gen2, 'Gen 2: {:.2f}Кб', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='#ff9f17', figsize=PLOT_SIZE))
        gen2.pack(fill=tk.BOTH, expand=1)

        # gc large-object heap
        loh_header = tk.Label(self, text='Large-object heap (Куча больших объектов)', anchor='w')
        loh_header.pack(fill=tk.BOTH, expand=1, padx=10)
        loh = tk.Frame(self)
        self.usage_loh = [0.0] * self.VALUES_LIMIT
        self.current_loh = tk.StringVar(loh, '0.0')
        loh.after(UPDATE_TIMEOUT,
            lambda: refresh(loh, self.usage_loh, self.current_loh, 'LOH: {:.2f}Кб', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='#ff7026', figsize=PLOT_SIZE))
        loh.pack(fill=tk.BOTH, expand=1)

        # gc pinned-object heap
        poh_header = tk.Label(self, text='Pinned-object heap (Куча закрепленных объектов)', anchor='w')
        poh_header.pack(fill=tk.BOTH, expand=1, padx=10)
        poh = tk.Frame(self)
        self.usage_poh = [0.0] * self.VALUES_LIMIT
        self.current_poh = tk.StringVar(poh, '0.0')
        loh.after(UPDATE_TIMEOUT,
            lambda: refresh(poh, self.usage_poh, self.current_poh, 'POH: {:.2f}Кб', self.VALUES_LIMIT, UPDATE_TIMEOUT,
            color='#f63838', figsize=PLOT_SIZE))
        poh.pack(fill=tk.BOTH, expand=1)

        self.text = 'GC'
        controller.gc = self
