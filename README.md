# visual-clr

## Setup

1. Clone project with submodules
2. Build up profiling lib at clr-profiler (`cargo build`)
3. Install python requirements (`pip install -r requirements.txt`)

## Usage

1. Setup environment
```bash
export CORECLR_ENABLE_PROFILING=1
export CORECLR_PROFILER_PATH="${PATH_TO_LIB}/libtest_profilers.(so|dll)"
export CORECLR_PROFILER="{DF63A541-5A33-4611-8829-F4E495985EE3}"
```
2. Run GUI app (`python3 __main__.py`)
3. Run .NET app using established environment (`dotnet ./bin/Debug/*/Program.dll`)
4. Wait until PID of the app appears at the "connect window" then click "Connect".
