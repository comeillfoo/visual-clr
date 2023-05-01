#!/usr/bin/env python3
import logcollector_pb2_grpc
from logcollector_pb2 import OperationResponse, TimestampRequest, ResponseTypes, SessionStartRequest, SessionFinishRequest


class LogCollectorService(logcollector_pb2_grpc.LogCollectorServicer):
    def __init__(self, app):
        self.app = app


    def _class_stamp_stub(self, request: TimestampRequest, operation: str) -> OperationResponse:
        if request.pid != self.app.active_pid:
            return OperationResponse(is_ok=False, response_type=ResponseTypes.RESET)
        print(f'class {request.payload} {operation} at {request.time}')
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
        if self.app.active_pid == request.pid:
            # accept session
            return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)
        else:
            # reject because of busyness
            return OperationResponse(is_ok=False, response_type=ResponseTypes.BUSY)


    def FinishSession(self, request: SessionFinishRequest, context) -> OperationResponse:
        self.app.queues.finish.put(request.pid)
        self.app.event_generate('<<FinishSession>>')
        return OperationResponse(is_ok=True, response_type=ResponseTypes.OK)


def serve(port, app):
    logcollector_pb2_grpc.add_LogCollectorServicer_to_server(LogCollectorService(app), app.server)
    app.server.add_insecure_port(f'[::]:{port}')
    print(f'server started: localhost:{port}')
    app.server.start()
    app.server.wait_for_termination()
