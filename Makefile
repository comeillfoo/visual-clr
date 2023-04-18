PY=python3
PROTOC=grpc_tools.protoc
BASEDIR=$(CURDIR)/protos
OUTDIR=$(PWD)
PROTOC_FLAGS=-I $(BASEDIR) --python_out=$(OUTDIR) --grpc_python_out=$(OUTDIR)


%_pb2.py: $(BASEDIR)/%.proto
	$(PY) -m $(PROTOC) $(PROTOC_FLAGS) $<


clean:
	rm -f $(OUTDIR)/*_pb2*.py

.PHONY: clean