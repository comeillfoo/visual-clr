#!/usr/bin/env python3
import logcollector_pb2_grpc
from logcollector_pb2 import OperationResponse, TimestampRequest, TimestampIdRequest, ResponseTypes, SessionStartRequest, SessionFinishRequest
from datetime import datetime


class LogCollectorService(logcollector_pb2_grpc.LogCollectorServicer):
    def __init__(self, app):
        self.app = app

    def _append_log(self, timestamp: float, payload: str):
        t = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
        log = f'[{t}]: {payload}\n'
        print(log, end='')
        self.app.queues.logs.put(log)
        self.app.event_generate('<<AppendLog>>')

    def _class_stamp_stub(self, request: TimestampRequest, operation: str) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)
        self._append_log(request.time, f'class {request.payload} {operation}')
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)


    def ClassLoadStartStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._class_stamp_stub(request, 'started loading')


    def ClassLoadFinishedStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._class_stamp_stub(request, 'finished loading')


    def ClassUnloadStartStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._class_stamp_stub(request, 'started unloading')


    def ClassUnloadFinishedStamp(self, request: TimestampRequest, context) -> OperationResponse:
        return self._class_stamp_stub(request, 'finished unloading')


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

    def _thread_stamp_stub(self, request: TimestampIdRequest, operation: str) -> OperationResponse:
        if request.pid != self.app.active_pid.get():
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)
        self._append_log(request.time, f'thread[{request.id}] {operation}')
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)

    def ThreadCreated(self, request, context):
        return self._thread_stamp_stub(request, 'created')

    def ThreadDestroyed(self, request, context):
        return self._thread_stamp_stub(request, 'destroyed')

    def ThreadResumed(self, request, context):
        return self._thread_stamp_stub(request, 'resumed')

    def ThreadSuspended(self, request, context):
        return self._thread_stamp_stub(request, 'suspended')


def serve(port, app):
    logcollector_pb2_grpc.add_LogCollectorServicer_to_server(LogCollectorService(app), app.server)
    app.server.add_insecure_port(f'[::]:{port}')
    print(f'server started: localhost:{port}')
    app.server.start()
    app.server.wait_for_termination()
