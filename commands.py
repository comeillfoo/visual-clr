#!/usr/bin/env python3
import subprocess as sp
import os

def _dotnet_env(path: str) -> dict:
    dotnet_env = os.environ
    dotnet_env['PATH'] = path
    return dotnet_env


def _dotnet_list(path: str, tolist: str) -> str:
    r = sp.Popen([f'dotnet --list-{tolist}'], env=_dotnet_env(path), shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout, stderr = r.communicate()
    if r.returncode != 0:
        return stderr.decode().strip()
    else:
        return stdout.decode().strip()


list_sdks = lambda path: _dotnet_list(path, 'sdks')
list_runtimes = lambda path: _dotnet_list(path, 'runtimes')