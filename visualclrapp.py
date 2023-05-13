#!/usr/bin/env python3
from concurrent import futures
import grpc
import tkinter as tk
from frames import ConnectionFrame, MonitorFrame
from collector.service import serve
from utility import SessionQueues
from safe_structs import SafeSet
from threading import Thread
from queue import Queue
import os
from tkinter import messagebox as mb
from commands import list_sdks, list_runtimes
from enums import ThreadStates
from utility import unix2str


class VisualCLRApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        # init members
        self.processes = {}
        self.processes[0] = { 'pid': 0, 'cmd': 'debug', 'path': os.environ['PATH'] }
        self.queues = SessionQueues(Queue(), Queue(1), Queue(), Queue(), Queue(), Queue())
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        self.threads_data = {}

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

        # setup context
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
        self.common.pid.set(f"PID: {data['pid']}")
        self.common.path.set(f"PATH: {data['path']}")
        self.common.sdks.set(f"SDKs: {list_sdks(data['path'])}")
        self.common.rts.set(f"Runtimes: {list_runtimes(data['path'])}")
        self.common.cmd.set(f"CMD: {data['cmd']}")

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
                prev = self.metrics.thread.get()
                self.metrics.thread.set(prev + (+1 if op == ThreadStates.CREATED else -1))

            # update threads_data
            if op == ThreadStates.CREATED:
                self.threads_data[request.id] = {
                    'state': 'готовность',
                    'created': unix2str(request.time),
                    'destroyed': 'еще не завершен'
                }
                self.threads.listv.set(list(self.threads_data.keys()))
            if op == ThreadStates.DESTROYED:
                self.threads_data[request.id]['state'] = 'завершен'
                self.threads_data[request.id]['destroyed'] = unix2str(request.time)
                self.threads.listv.set(list(self.threads_data.keys()))
            if op == ThreadStates.RESUMED:
                self.threads_data[request.id]['state'] = 'выполняемый'
            if op == ThreadStates.SUSPENDED:
                self.threads_data[request.id]['state'] = 'ожидает'

    def update_stats(self, event):
        if not self.queues.stats.empty():
            request = self.queues.stats.get()
            self.metrics.cpu.set(str(request.cpu))
            self.metrics.read_kbytes.set(str(request.read_bytes / 1024))
            self.metrics.write_kbytes.set(str(request.write_bytes / 1024))
