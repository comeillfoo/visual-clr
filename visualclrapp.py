#!/usr/bin/env python3
from concurrent import futures
import grpc
import tkinter as tk
from frames import ConnectionFrame, MonitorFrame
from collector.service import serve
from collector.context import SessionQueues
from safe_structs import SafeSet
from threading import Thread
from queue import Queue
import os


class VisualCLRApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        # init members
        self.processes = SafeSet()
        self.processes.add(0)
        self.active_pid = None
        self.queues = SessionQueues(Queue(), Queue(1), Queue())
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))

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
            old_set = self.processes.clone()
            self.processes.remove(pid)
            new_set = self.processes.clone()
            if old_set != new_set:
                self.frames[ConnectionFrame].event_generate('<<UpdateList>>')
            if pid == self.active_pid:
                self.active_pid = None
                self.show_frame(ConnectionFrame)

    def finish_active_session(self, event):
        self.queues.finish.put(self.active_pid)
        self.finish_session(event)

    def append_session(self, event):
        if not self.queues.pending.empty():
            pid = self.queues.pending.get()
            old_set = self.processes.clone()
            self.processes.add(pid)
            new_set = self.processes.clone()
            if old_set != new_set:
                self.frames[ConnectionFrame].event_generate('<<UpdateList>>')

    def start_session(self, event):
        if not self.queues.start.empty():
            pid = self.queues.start.get()
            self.active_pid = pid
            self.show_frame(MonitorFrame)
            self.init_tabs({ 'pid': pid, 'path': os.environ['PATH'] })

    def init_tabs(self, data):
        self.common.pid.set(f"PID: {data['pid']}")
        self.common.path.set(f"PATH: {data['path']}")
