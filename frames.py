#!/usr/bin/env python3
import tkinter as tk


class ConnectionFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        # first layer: title or image
        title = tk.Label(self, text='VisualCLR')
        title.grid(row=0, column=0, columnspan=4)

        # second layer: dropdown list
        process = tk.StringVar(self)

        processes = tk.OptionMenu(self, process, *controller.processes)
        processes.grid(row=1, column=1, columnspan=2)

        # third layer: buttons
        btn_connect = tk.Button(self, text='Connect')
        def connect_cb(event):
            print(f'Connecting to {process.get()}...')
            controller.queues.start.put(int(process.get()))
            controller.event_generate('<<StartSession>>')

        btn_connect.bind('<Button-1>', connect_cb)
        btn_connect.grid(row=2, column=0, columnspan=2)

        btn_exit = tk.Button(self, text='Exit')
        def exit_cb(event):
            controller.server.stop(None).wait()
            processes = controller.processes.clone()
            for process in processes:
                controller.queues.finish.put(process)
                controller.event_generate('<<FinishSession>>')
            controller.destroy()

        btn_exit.bind('<Button-1>', exit_cb)
        btn_exit.grid(row=2, column=2, columnspan=2)

        def update_cb(event):
            pids = controller.processes.clone()
            processes['menu'].delete(0, 'end')
            for pid in pids:
                processes['menu'].add_command(label=pid, command=tk._setit(process, pid))

        self.bind('<<UpdateList>>', update_cb)


class MonitorFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        def back_cb(event):
            controller.event_generate('<<FinishActiveSession>>')

        btn_back = tk.Button(self, text='Disconnect')
        btn_back.bind('<Button-1>', back_cb)
        btn_back.grid(row=0, column=1, columnspan=4)
