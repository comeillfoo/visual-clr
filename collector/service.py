#!/usr/bin/env python3
import logcollector_pb2_grpc
from logcollector_pb2 import ResponseTypes, OperationResponse, TimestampRequest, \
    TimestampIdRequest, SessionStartRequest, SessionFinishRequest, \
    ObjectAllocatedStampRequest, UpdateGenerationsRequest
from utility import unix2str
from enums import ThreadStates


class LogCollectorService(logcollector_pb2_grpc.LogCollectorServicer):
    def __init__(self, app):
        self.app = app

    def _update_stats(self, request):
        self.app.queues.stats.put(request.stats)
        self.app.event_generate('<<UpdateStats>>')
        # self._append_log(request.time, f'CPU: {request.stats.cpu:.2f}%; IO: {request.stats.read_bytes}/{request.stats.write_bytes}')

    def _append_log(self, timestamp: float, payload: str):
        log = f'[{unix2str(timestamp)}]: {payload}\n'
        print(log, end='')
        self.app.queues.logs.put(log)
        self.app.event_generate('<<AppendLog>>')

    def _class_stamp_stub(self, request: TimestampRequest, operation: str) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)
        if operation == 'loaded':
            self.app.event_generate('<<ClassLoaded>>')
        elif operation == 'unloaded':
            self.app.event_generate('<<ClassUnloaded>>')

        self._append_log(request.time, f'class {request.payload} {operation}')
        self._update_stats(request)
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)

    def ClassLoadFinishedStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._class_stamp_stub(request, 'loaded')

    def ClassUnloadFinishedStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._class_stamp_stub(request, 'unloaded')

    def StartSession(self, request: SessionStartRequest, context) -> OperationResponse:
        print(f'Pending Session {request.pid}: {request.cmd}')
        self.app.queues.pending.put(request)
        self.app.event_generate('<<PendingSession>>')
        if self.app.active_pid.get() == request.pid:
            # accept session
            return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)
        else:
            # reject because of busyness
            return OperationResponse(is_ok=False, response_type=ResponseTypes.BUSY)

    def FinishSession(self, request: SessionFinishRequest, context) -> OperationResponse:
        print(f'Finishing Session for {request.pid}')
        self.app.queues.finish.put(request.pid)
        self.app.event_generate('<<FinishSession>>')
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)

    def _thread_stamp_stub(self, request: TimestampIdRequest, operation: ThreadStates) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)

        self.app.queues.threads.put((request, operation))
        self.app.event_generate('<<UpdateThreads>>')

        self._append_log(request.time, f'thread {request.id} {operation}')
        self._update_stats(request)
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)

    def ThreadCreated(self, request: TimestampIdRequest, context) -> OperationResponse:
        return self._thread_stamp_stub(request, ThreadStates.CREATED)

    def ThreadDestroyed(self, request: TimestampIdRequest, context) -> OperationResponse:
        return self._thread_stamp_stub(request, ThreadStates.DESTROYED)

    def ThreadResumed(self, request: TimestampIdRequest, context) -> OperationResponse:
        return self._thread_stamp_stub(request, ThreadStates.RESUMED)

    def ThreadSuspended(self, request: TimestampIdRequest, context) -> OperationResponse:
        return self._thread_stamp_stub(request, ThreadStates.SUSPENDED)

    def ExceptionThrown(self, request: TimestampRequest, context) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)

        self.app.event_generate('<<IncrementExceptions>>')
        self._append_log(request.time, f'{request.payload} thrown')
        self._update_stats(request)
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)

    def _jit_compilation_stub(self, request: TimestampRequest, op: str) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)

        self._append_log(request.time, f'jit-compilation {request.payload} {op}')
        self._update_stats(request)
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)

    def JitCompilationStartStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._jit_compilation_stub(request, 'started')

    def JitCompilationFinishedStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._jit_compilation_stub(request, 'finished')

    def ObjectAllocationStamp(self, request: ObjectAllocatedStampRequest, context) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)

        self.app.queues.allocations.put(request)
        self.app.event_generate('<<AllocateObject>>')
        self._append_log(request.time, f'object type {request.class_name} {request.size} bytes allocated')
        self._update_stats(request)
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)

    def GarbageCollectionFinishedStamp(self, request: UpdateGenerationsRequest, context) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)

        self.app.queues.objects.put(request)
        self.app.event_generate('<<UpdateObjects>>')
        self._append_log(request.time, f'GC collection finished')
        self._update_stats(request)
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)



def serve(port, app):
    logcollector_pb2_grpc.add_LogCollectorServicer_to_server(LogCollectorService(app), app.server)
    app.server.add_insecure_port(f'[::]:{port}')
    print(f'server started: localhost:{port}')
    app.server.start()
    app.server.wait_for_termination()
