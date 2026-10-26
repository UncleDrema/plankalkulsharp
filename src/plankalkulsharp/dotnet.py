"""Build Plankalkul modules and start the shared .NET executor."""

import hashlib
from collections import deque
from importlib.resources import as_file, files
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4


class BuildError(Exception):
    """The .NET SDK could not build the generated program."""


def _sdk_version(dotnet: str) -> str:
    # Resolve with our packaged global.json, not the caller's SDK preference.
    # Shared builds copy this file; module builds copy it explicitly below.
    try:
        with as_file(files("plankalkulsharp").joinpath("dotnet_assets")) as assets:
            result = subprocess.run(
                [dotnet, "--version"], cwd=assets, capture_output=True, text=True,
                encoding="utf-8", errors="replace", check=False, **_dotnet_options(),
            )
    except OSError as error:
        raise BuildError(f"cannot run dotnet: {error}") from error
    version = result.stdout.strip()
    if result.returncode or not version.startswith("10."):
        raise BuildError("a stable .NET 10 SDK is required; install it alongside other SDK versions")
    return version


def _require_dotnet() -> str:
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        raise BuildError("dotnet not found on PATH; install the .NET 10 SDK")
    _sdk_version(dotnet)
    return dotnet


def _dotnet_options() -> dict[str, int]:
    """Avoid a transient console window when the monitor invokes build tools."""
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}


def _run_build(command: list[str], *, cwd: Path) -> None:
    """Stream build progress to stderr, keeping stdout available for CLI JSON."""
    tail = deque(maxlen=200)
    # Interactive builds must not wait for NuGet's vulnerability database.
    with subprocess.Popen([*command, "-p:NuGetAudit=false"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", **_dotnet_options()) as process:
        try:
            for line in process.stdout:
                tail.append(line)
                print(line, end="", file=sys.stderr, flush=True)
            code = process.wait()
        except BaseException:
            process.kill()
            process.wait()
            raise
    if code:
        raise BuildError(f"dotnet build failed (exit {code}):\n{''.join(tail)}")


def _copy_assets(source, destination: Path) -> None:
    """Copy package sources, deliberately excluding generated build products."""
    for item in source.iterdir():
        if item.name in {"bin", "obj", "__pycache__"}:
            continue
        target = destination / item.name
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _copy_assets(item, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.read_bytes())


def _asset_fingerprint(dotnet: str) -> str:
    """Fingerprint sources and the toolchain that turns them into the shared host."""
    digest = hashlib.sha256()
    root = files("plankalkulsharp").joinpath("dotnet_assets")

    def add(directory, prefix: str = "") -> None:
        for item in sorted(directory.iterdir(), key=lambda child: child.name):
            if item.name in {"bin", "obj", "__pycache__"}:
                continue
            name = f"{prefix}{item.name}"
            if item.is_dir():
                add(item, name + "/")
            else:
                digest.update(name.encode("utf-8"))
                digest.update(item.read_bytes())

    add(root)
    sdk = _sdk_version(dotnet)
    digest.update(f"{sdk}|{platform.system()}|{platform.machine()}".encode("utf-8"))
    return digest.hexdigest()[:20]


def _cache_root() -> Path:
    override = os.environ.get("PLANKALKUL_CACHE_DIR")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home()
    return Path(base) / "PlankalkulSharp" / "dotnet"


def _build_shared(project: str, output: str) -> Path:
    """Build a packaged host once and atomically publish it in the user cache."""
    dotnet = _require_dotnet()
    fingerprint = _asset_fingerprint(dotnet)
    component = project.split("/", 1)[0]
    target = _cache_root() / fingerprint / component
    ready = target / output
    if ready.is_file():
        return ready

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.parent / f".{component}-{uuid4().hex}"
    try:
        _copy_assets(files("plankalkulsharp").joinpath("dotnet_assets"), stage)
        _run_build(
            [dotnet, "build", project, "-c", "Release", "-nologo", "-v:n"],
            cwd=stage,
        )
        staged_ready = stage / output
        if not staged_ready.is_file():
            raise BuildError(f"dotnet build did not produce {staged_ready}")
        try:
            stage.replace(target)
        except FileExistsError:
            # Another Plankalkul process won the race; its finished cache is valid.
            shutil.rmtree(stage, ignore_errors=True)
        if not ready.is_file():
            raise BuildError(f"shared build cache did not contain {ready}")
        return ready
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def ensure_worker() -> Path:
    """Return the cached Worker DLL, building Worker and Runtime when needed."""
    return _build_shared("worker/PlankalkulWorker.csproj", "worker/bin/Release/net10.0/PlankalkulWorker.dll")


def ensure_machine() -> Path:
    """Return the cached WPF monitor DLL; ordinary CLI commands never call this."""
    return _build_shared("desktop/PlankalkulMachine.csproj", "desktop/bin/Release/net10.0-windows/PlankalkulMachine.dll")


def _runtime_dll(worker: Path) -> Path:
    runtime = worker.parent / "PlankalkulRuntime.dll"
    if not runtime.is_file():
        raise BuildError(f"Worker cache did not contain {runtime}")
    return runtime


def _copy_module_output(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("PlankalkulProgram.dll", "PlankalkulProgram.deps.json", "PlankalkulProgram.pdb"):
        artifact = source / name
        if artifact.is_file():
            shutil.copy2(artifact, destination / name)


def build_program(il_source: str, build_dir: Path, *, runtime_dll: Path | None = None) -> Path:
    """Build a module into ``build_dir`` and return its absolute DLL path.

    The module references the Runtime from Worker instead of carrying a private
    allocator implementation or a copied Runtime DLL.
    """
    dotnet = _require_dotnet()
    build_dir = build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    runtime_dll = (runtime_dll or _runtime_dll(ensure_worker())).resolve()
    assets = files("plankalkulsharp").joinpath("dotnet_assets")
    for name in ("PlankalkulProgram.ilproj", "nuget.config", "global.json"):
        item = assets.joinpath(name)
        (build_dir / name).write_bytes(item.read_bytes())
    (build_dir / "PlankalkulProgram.il").write_text(il_source, encoding="utf-8")

    # Generated IL includes the source path/hash and compiler metadata. Hash the
    # actual compiler output as well, so editable codegen changes invalidate it.
    digest = hashlib.sha256(il_source.encode("utf-8"))
    digest.update(runtime_dll.read_bytes())
    digest.update(_asset_fingerprint(dotnet).encode("ascii"))
    cached = _cache_root() / "modules" / digest.hexdigest()
    assembly = build_dir / "bin" / "Release" / "net10.0" / "PlankalkulProgram.dll"
    if (cached / assembly.name).is_file():
        print("Using cached program module", file=sys.stderr, flush=True)
        _copy_module_output(cached, assembly.parent)
        return assembly

    _run_build(
        [
            dotnet, "build", "PlankalkulProgram.ilproj", "-c", "Release", "-nologo", "-v:n",
            f"-p:PlankalkulRuntimePath={runtime_dll}",
        ],
        cwd=build_dir,
    )
    if not assembly.is_file():
        raise BuildError(f"dotnet build did not produce {assembly}")

    # Only successful output is published. Independent runs may build the same
    # source concurrently; a completed cache entry can safely win that race.
    cached.parent.mkdir(parents=True, exist_ok=True)
    stage = cached.parent / f".module-{uuid4().hex}"
    try:
        _copy_module_output(assembly.parent, stage)
        try:
            stage.replace(cached)
        except FileExistsError:
            if not (cached / assembly.name).is_file():
                raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return assembly


def run_program(
    il_source: str,
    args: list[str],
    *,
    heap_size: int = 1_048_576,
    memory_stats: bool = False,
    memory_trace: bool = False,
) -> int:
    """Build temporarily and run the module inside the shared Worker."""
    dotnet = _require_dotnet()
    worker = ensure_worker()
    temporary_root = _cache_root() / "temporary"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="run-", dir=temporary_root) as temporary_dir:
        assembly = build_program(il_source, Path(temporary_dir), runtime_dll=_runtime_dll(worker))
        environment = os.environ.copy()
        environment["PLANKALKUL_HEAP_SIZE"] = str(heap_size)
        environment["PLANKALKUL_MEMORY_STATS"] = "1" if memory_stats else "0"
        environment["PLANKALKUL_MEMORY_TRACE"] = "1" if memory_trace else "0"
        # CLI Worker inherits the caller's console.  CREATE_NO_WINDOW would
        # detach it on Windows and silently discard the program's stdout.
        process = subprocess.Popen([dotnet, str(worker), "--module", str(assembly), "--", *args], env=environment)
        try:
            return process.wait()
        except KeyboardInterrupt:
            # The console signal asks Worker to stop; do not leave a temporary
            # module behind if a non-cooperative module ignores it.
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return 130
