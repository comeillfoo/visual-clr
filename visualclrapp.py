#!/usr/bin/env python3
from concurrent import futures
import grpc
import tkinter as tk
from frames import ConnectionFrame, MonitorFrame
from collector.service import serve
from utility import SessionQueues, ManagedObject, unix2str
from safe_structs import SafeSet
from threading import Thread
from queue import Queue
import os
from tkinter import messagebox as mb
from commands import list_sdks, list_runtimes
from enums import ThreadStates, GcGenerations

_kb_unboxer = lambda v: float(v) * 1024
_kb_boxer = lambda v: str(v / 1024)

def _fold_variable(variable, inc, unboxer = lambda v: v, boxer = lambda v: v):
    prev = unboxer(variable.get())
    variable.set(boxer(prev + inc))


class VisualCLRApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        # init members
        self.processes = {}
        self.processes[0] = { 'pid': 0, 'cmd': 'debug', 'path': os.environ['PATH'] }
        self.queues = SessionQueues(Queue(), Queue(1), Queue(), Queue(), \
                                    Queue(), Queue(), Queue(), Queue())
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        self.threads_data = {}
        self.objects_data = {}

        # init GUI
        tk.Tk.__init__(self, *args, **kwargs)
        self.title('VisualCLR')

        container = tk.Frame(self)
        container.pack(side = "top", fill = "both", expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for Frame in (ConnectionFrame, MonitorFrame):
            frame = Frame(container, self)
            self.frames[Frame] = frame
            frame.grid(row=0, column=0, sticky ="nsew")

        self.show_frame(ConnectionFrame)

        # bind events
        self.bind('<<FinishSession>>', self.finish_session)
        self.bind('<<FinishActiveSession>>', self.finish_active_session)
        self.bind('<<PendingSession>>', self.append_session)
        self.bind('<<StartSession>>', self.start_session)
        self.bind('<<AppendLog>>', self.append_log)
        self.bind('<<UpdateThreads>>', self.update_threads)
        self.bind('<<UpdateStats>>', self.update_stats)
        self.bind('<<IncrementExceptions>>', self.increment_exceptions)
        self.bind('<<AllocateObject>>', self.allocate_object)
        self.bind('<<UpdateObjects>>', self.update_objects)
        self.bind('<<ClassLoaded>>', self.class_loaded)
        self.bind('<<ClassUnloaded>>', self.class_unloaded)

        # start collector
        self.collector = Thread(target=serve, args=(50051, self))
        self.collector.start()
        print('thread started')


    def show_frame(self, cls):
        self.frames[cls].tkraise()

    # event handlers
    def finish_session(self, event):
        if not self.queues.finish.empty():
            pid = self.queues.finish.get()
            if pid == self.active_pid.get():
                self.active_pid.set(0)
                mb.showwarning('Connection lost',
                               f'Disconnected from {pid}. All data now invalid')
            if pid in self.processes:
                del self.processes[pid]
                self.frames[ConnectionFrame].event_generate('<<UpdateList>>')


    def finish_active_session(self, event):
        self.queues.finish.put(self.active_pid.get())
        self.finish_session(event)

    def append_session(self, event):
        if not self.queues.pending.empty():
            request = self.queues.pending.get()
            # TODO: the point of improvement
            old_set = set(self.processes.keys())
            self.processes[request.pid] = {
                'pid': request.pid,
                'cmd': request.cmd,
                'path': request.path
            }
            new_set = set(self.processes.keys())
            if old_set != new_set:
                self.frames[ConnectionFrame].event_generate('<<UpdateList>>')

    def start_session(self, event):
        if not self.queues.start.empty():
            data = self.queues.start.get()
            self.show_frame(MonitorFrame)
            self.init_tabs(data)

    def init_tabs(self, data):
        # common
        self.common.pid.set(f"PID: {data['pid']}")
        self.common.path.set(f"PATH: {data['path']}")
        self.common.sdks.set(f"SDKs: {list_sdks(data['path'])}")
        self.common.rts.set(f"Runtimes: {list_runtimes(data['path'])}")
        self.common.cmd.set(f"CMD: {data['cmd']}")

        # metrics
        reset_list = [0.0] * self.metrics.VALUES_LIMIT
        self.metrics.threads = reset_list.copy()
        self.metrics.thread.set(0)
        self.metrics.exceptions = reset_list.copy()
        self.metrics.exception.set(0)
        self.metrics.cpus = reset_list.copy()
        self.metrics.cpu.set('0.0')
        self.metrics.memories = reset_list.copy()
        self.metrics.memory.set('0.0')
        self.metrics.reads = reset_list.copy()
        self.metrics.read_kbytes.set('0.0')
        self.metrics.writes = reset_list.copy()
        self.metrics.write_kbytes.set('0.0')
        self.metrics.classes.set(0)
        self.metrics.objects_disposed.set(0)
        self.metrics.classes_loaded.set(0)
        self.metrics.classes_unloaded.set(0)
        # TODO: update labels
        # logs
        self.traces.logs.delete('1.0', tk.END)
        self.objects.stats.delete(*self.objects.stats.get_children(''))
        # threads
        self.threads.listv.set([])

        # gc
        reset_list = [0.0] * self.gc.VALUES_LIMIT
        self.gc.usage_gen0 = reset_list.copy()
        self.gc.current_gen0.set('0.0')
        self.gc.usage_gen1 = reset_list.copy()
        self.gc.current_gen1.set('0.0')
        self.gc.usage_gen2 = reset_list.copy()
        self.gc.current_gen2.set('0.0')
        self.gc.usage_loh = reset_list.copy()
        self.gc.current_loh.set('0.0')
        self.gc.usage_poh = reset_list.copy()
        self.gc.current_poh.set('0.0')

        # self fields
        self.threads_data = {}
        self.objects_data = {}

    def append_log(self, event):
        while not self.queues.logs.empty():
            log = self.queues.logs.get()
            count = lambda txt: int(txt.index('end').split('.')[0]) - 1
            if count(self.traces.logs) > 40:
                self.traces.logs.delete('1.0', '2.0')
            self.traces.logs.insert('end', log)

    def update_threads(self, event):
        if not self.queues.threads.empty():
            request, op = self.queues.threads.get()
            # update counter
            if op == ThreadStates.CREATED or op == ThreadStates.DESTROYED:
                # prev = self.metrics.thread.get()
                # self.metrics.thread.set(prev + (+1 if op == ThreadStates.CREATED else -1))
                _fold_variable(self.metrics.thread, (+1 if op == ThreadStates.CREATED else -1))

            # update threads_data
            if op == ThreadStates.CREATED:
                self.threads_data[request.id] = {
                    'state': 'готовность',
                    'created': unix2str(request.time),
                    'destroyed': ''
                }
                self.threads.listv.set(list(self.threads_data.keys()))
            if op == ThreadStates.DESTROYED:
                self.threads_data[request.id]['state'] = 'завершен'
                self.threads_data[request.id]['destroyed'] = unix2str(request.time)
                self.threads.listv.set(list(self.threads_data.keys()))
            if op == ThreadStates.RESUMED:
                if request.id not in self.threads_data:
                    self.threads_data[request.id] = {
                        'state': 'выполняемый',
                        'created': unix2str(request.time),
                        'destroyed': ''
                    }
                else:
                    self.threads_data[request.id]['state'] = 'выполняемый'
            if op == ThreadStates.SUSPENDED:
                if request.id not in self.threads_data:
                    self.threads_data[request.id] = {
                        'state': 'ожидает',
                        'created': unix2str(request.time),
                        'destroyed': ''
                    }
                else:
                    self.threads_data[request.id]['state'] = 'ожидает'

    def update_stats(self, event):
        if not self.queues.stats.empty():
            request = self.queues.stats.get()
            self.metrics.cpu.set(str(request.cpu))
            self.metrics.read_kbytes.set(str(request.read_bytes / 1024))
            self.metrics.write_kbytes.set(str(request.write_bytes / 1024))

    def increment_exceptions(self, event):
        _fold_variable(self.metrics.exception, 1)
        # prev = self.metrics.exception.get()
        # self.metrics.exception.set(prev + 1)

    def class_loaded(self, event):
        _fold_variable(self.metrics.classes_loaded, 1)
        self.metrics.classes_loaded_v.set(
                        f'Всего классов загружено: {self.metrics.classes_loaded.get()}')
        _fold_variable(self.metrics.classes, +1)
        self.metrics.classes_v.set(
                        f'Классов загружено: {self.metrics.classes.get()}')

    def class_unloaded(self, event):
        _fold_variable(self.metrics.classes_unloaded, 1)
        self.metrics.classes_unloaded_v.set(
                        f'Всего классов выгружено: {self.metrics.classes_unloaded.get()}')
        _fold_variable(self.metrics.classes, -1)
        self.metrics.classes_v.set(
                        f'Классов загружено: {self.metrics.classes.get()}')

    def _update_generation(self, g: GcGenerations, size: float):
        if GcGenerations.UNDEFINED != g:
            if GcGenerations.GEN0 == g:
                genvar = self.gc.current_gen0
            elif GcGenerations.GEN1 == g:
                genvar = self.gc.current_gen1
            elif GcGenerations.GEN2 == g:
                genvar = self.gc.current_gen2
            elif GcGenerations.LARGE_OBJECT_HEAP == g:
                genvar = self.gc.current_loh
            elif GcGenerations.PINNED_OBJECT_HEAP == g:
                genvar = self.gc.current_poh
            else:
                return
            _fold_variable(genvar, size,
                        _kb_unboxer, _kb_boxer)

    def allocate_object(self, event):
        if not self.queues.allocations.empty():
            request = self.queues.allocations.get()
            # update memory usage
            # prev = float(self.metrics.memory.get()) * 1024
            # self.metrics.memory.set(str((prev + request.size) / 1024))
            _fold_variable(self.metrics.memory, request.size,
                        _kb_unboxer, _kb_boxer)

            id = request.object_gen.id
            g = request.object_gen.generation.value

            objects = self.objects.stats
            classes = set(map(lambda child: objects.set(child, 'class'), objects.get_children('')))
            if request.class_name not in classes:
                objects.insert('', tk.END, \
                                values=(request.class_name, round(request.size / 1024, 2), 0.0))
            else:
                updated_children = filter(lambda child: objects.set(child, 'class') == request.class_name,
                                              objects.get_children(''))
                for child in updated_children:
                    prev = float(objects.set(child, 'total')) * 1024
                    objects.set(child, 'total', round((prev + request.size) / 1024, 2))

            # save object
            self.objects_data[id] = ManagedObject(
                request.class_name,
                request.size,
                GcGenerations.from_value(g),
                False
            )
            # update gc gen
            self._update_generation(self.objects_data[id].generation, +request.size)

    def update_objects(self, event):
        if not self.queues.objects.empty():
            request = self.queues.objects.get()
            objects = self.objects.stats

            for object in request.objects:
                if object.id not in self.objects_data:
                    self.objects_data[object.id] = ManagedObject('Unknown', 0, GcGenerations.UNDEFINED, False)
                object_data = self.objects_data[object.id]
                self._update_generation(object_data.generation, -object_data.size)
                if object.generation.is_valid:
                    # update gc gens
                    object_data.generation = GcGenerations.from_value(object.generation.value)
                    self._update_generation(object_data.generation, +object_data.size)
                    # survived collection
                    if not object_data.is_retained:
                        updated_children = filter(lambda child: objects.set(child, 'class') == object_data.class_name, objects.get_children(''))
                        for child in updated_children:
                            prev = float(objects.set(child, 'retained')) * 1024
                            objects.set(child, 'retained', round((prev + object_data.size) / 1024, 2))
                        object_data.is_retained = True
                else:
                    # disposed
                    updated_children = filter(lambda child: objects.set(child, 'class') == object_data.class_name, objects.get_children(''))
                    for child in updated_children:
                        prev = float(objects.set(child, 'total')) * 1024
                        objects.set(child, 'total', round((prev - object_data.size) / 1024, 2))
                        if object_data.is_retained:
                            prev = float(objects.set(child, 'retained')) * 1024
                            objects.set(child, 'retained', round((prev - object_data.size) / 1024, 2))
                            object_data.is_retained = False

                    _fold_variable(self.metrics.objects_disposed, 1)
                    self.metrics.objects_disposed_v.set(
                        f'Объектов освобождено: {self.metrics.objects_disposed.get()}')


