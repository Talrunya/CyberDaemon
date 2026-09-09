#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path


APP_NAME = "CyberDaemon"
VERSION = "0.1.0-beta"
ARCH = "x86_64"


def die(message: str) -> None:
    raise RuntimeError(message)


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> None:
    print("==>", " ".join(str(x) for x in command))
    subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
    )


def copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        die(f"File not found: {src}")

    dst.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Do not propagate source ownership/ACL metadata.
    shutil.copyfile(src, dst)

    try:
        dst.chmod(src.stat().st_mode & 0o777)
    except OSError:
        try:
            dst.chmod(0o644)
        except OSError:
            pass


def copy_tree(src: Path, dst: Path) -> None:
    if not src.is_dir():
        die(f"Directory not found: {src}")

    dst.mkdir(
        parents=True,
        exist_ok=True,
    )

    for item in src.iterdir():
        target = dst / item.name

        if item.is_symlink():
            try:
                resolved = item.resolve(strict=True)
            except OSError:
                continue

            if resolved.is_dir():
                copy_tree(
                    resolved,
                    target,
                )
            elif resolved.is_file():
                copy_file(
                    resolved,
                    target,
                )
            continue

        if item.is_dir():
            copy_tree(
                item,
                target,
            )
        else:
            copy_file(
                item,
                target,
            )


def copy_import(
    import_name: str,
    target_site: Path,
) -> list[Path]:
    """
    Resolve an import exactly as the current CPython resolves it.

    Returns native extension files that should also be scanned by ldd.
    """
    spec = importlib.util.find_spec(import_name)

    if spec is None:
        die(
            f"Required Python import not found: "
            f"{import_name}"
        )

    target_site.mkdir(
        parents=True,
        exist_ok=True,
    )

    native_files: list[Path] = []

    if spec.submodule_search_locations:
        source = Path(
            next(
                iter(
                    spec.submodule_search_locations
                )
            )
        )

        target = (
            target_site
            / source.name
        )

        copy_tree(
            source,
            target,
        )

        native_files.extend(
            target.rglob("*.so")
        )
        native_files.extend(
            target.rglob("*.so.*")
        )

        return native_files

    if spec.origin and spec.origin not in (
        "built-in",
        "frozen",
    ):
        source = Path(spec.origin)

        if not source.is_file():
            die(
                f"Import origin is not a file: "
                f"{source}"
            )

        target = (
            target_site
            / source.name
        )

        copy_file(
            source,
            target,
        )

        if source.suffix.startswith(".so"):
            native_files.append(target)

        return native_files

    die(
        f"Unsupported import layout: "
        f"{import_name}"
    )


def qt_paths() -> tuple[Path | None, Path | None]:
    """
    Ask PySide6 itself for the Qt plugin/QML locations.

    This is important on Arch/CachyOS because Qt may be installed by the
    distribution under /usr/lib/qt6 rather than inside site-packages/PySide6.
    """
    query = (
        "from PySide6.QtCore import QLibraryInfo;"
        "print(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath));"
        "print(QLibraryInfo.path(QLibraryInfo.LibraryPath.Qml2ImportsPath))"
    )

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                query,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(
            "⚠️ Could not query Qt paths:",
            exc,
        )
        return None, None

    values = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    plugins = (
        Path(values[0])
        if len(values) > 0
        and Path(values[0]).is_dir()
        else None
    )

    qml = (
        Path(values[1])
        if len(values) > 1
        and Path(values[1]).is_dir()
        else None
    )

    return plugins, qml


def ldd_paths(binary: Path) -> list[Path]:
    try:
        result = subprocess.run(
            [
                "ldd",
                str(binary),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []

    result_paths: list[Path] = []

    for line in result.stdout.splitlines():
        line = line.strip()

        if "=>" in line:
            path_text = (
                line.split("=>", 1)[1]
                .strip()
                .split()[0]
            )
        else:
            parts = line.split()
            path_text = (
                parts[0]
                if parts
                else ""
            )

        if not path_text.startswith("/"):
            continue

        path = Path(path_text)

        if path.is_file():
            result_paths.append(path)

    return result_paths


def copy_native_dependencies(
    app_lib: Path,
    binaries: list[Path],
) -> None:
    # Never bundle glibc/loader/kernel libraries.
    excluded_names = {
        "ld-linux-x86-64.so.2",
        "libc.so.6",
        "libm.so.6",
        "libpthread.so.0",
        "libdl.so.2",
        "librt.so.1",
    }

    seen: set[Path] = set()
    queue = list(binaries)

    while queue:
        binary = queue.pop()

        if not binary.is_file():
            continue

        try:
            binary = binary.resolve()
        except OSError:
            continue

        if binary in seen:
            continue

        seen.add(binary)

        for dependency in ldd_paths(binary):
            if (
                dependency.name
                in excluded_names
            ):
                continue

            target = (
                app_lib
                / dependency.name
            )

            if not target.exists():
                copy_file(
                    dependency,
                    target,
                )

            queue.append(dependency)


def main() -> int:
    base = Path(__file__).resolve().parent

    app_entry = base / "app.py"
    ui_dir = base / "ui"
    hardware_dir = base / "hardware"
    assets_dir = (
        ui_dir
        / "assets"
    )
    icon = (
        assets_dir
        / "cyberdaemon_emblem.png"
    )

    release_dir = (
        base
        / "cyberdaemon"
    )
    release_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        release_dir
        / f"{APP_NAME}-{VERSION}-{ARCH}.AppImage"
    )

    appimagetool = shutil.which(
        "appimagetool"
    )

    if not appimagetool:
        die(
            "appimagetool not found in PATH"
        )

    if not app_entry.is_file():
        die(
            f"Missing: {app_entry}"
        )

    if not ui_dir.is_dir():
        die(
            f"Missing: {ui_dir}"
        )

    if not hardware_dir.is_dir():
        die(
            f"Missing: {hardware_dir}"
        )

    if not assets_dir.is_dir():
        die(
            f"Missing: {assets_dir}"
        )

    if not icon.is_file():
        die(
            f"Missing: {icon}"
        )

    print("=" * 52)
    print(
        f"🚀 {APP_NAME} Python AppImage"
    )
    print("=" * 52)
    print(
        f"Project : {base}"
    )
    print(
        f"Python  : {sys.executable}"
    )
    print(
        f"Version : {sys.version.split()[0]}"
    )
    print(
        f"Output  : {output}"
    )
    print()

    # Always build into a brand-new temporary directory.
    # This eliminates stale/root-owned build files.
    temp_root = Path(
        tempfile.mkdtemp(
            prefix="cyberdaemon-appimage-"
        )
    )

    appdir = (
        temp_root
        / f"{APP_NAME}.AppDir"
    )

    try:
        usr = appdir / "usr"
        bin_dir = usr / "bin"
        lib_dir = usr / "lib"
        python_root = (
            lib_dir
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
        )
        site_dir = (
            python_root
            / "site-packages"
        )
        app_root = (
            appdir
            / "opt"
            / "cyberdaemon"
        )

        for directory in (
            bin_dir,
            python_root,
            site_dir,
            app_root,
        ):
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        # ------------------------------------------------------
        # Standard library
        # ------------------------------------------------------
        stdlib = Path(
            sysconfig.get_paths()["stdlib"]
        )

        print(
            "📦 Copying Python stdlib:",
            stdlib,
        )

        copy_tree(
            stdlib,
            python_root,
        )

        # Do not copy the complete site-packages.
        # Resolve only actual imports used by CyberDaemon.
        print(
            "📦 Copying PySide6 / shiboken6 / hid"
        )

        native_modules: list[Path] = []

        for import_name in (
            "PySide6",
            "shiboken6",
            "hid",
        ):
            native_modules.extend(
                copy_import(
                    import_name,
                    site_dir,
                )
            )

        # Python 3.14 provides typing in the stdlib. Remove any third-party
        # backport accidentally included by a package tree.
        for shadow in (
            site_dir / "typing.py",
            site_dir / "typing_extensions.py",
        ):
            if shadow.is_file():
                shadow.unlink()

        # ------------------------------------------------------
        # CyberDaemon source
        # ------------------------------------------------------
        print(
            "📦 Copying CyberDaemon"
        )

        ignored = {
            ".git",
            "__pycache__",
            "dist",
            "cyberdaemon",
            "build_tmp",
            "build-appimage",
            "build_python_appimage",
            "build_cyberdaemon.py",
            "build_cyberdaemon_final.py",
            "build_cyberdaemon_fixed.py",
            "build_cyberdaemon_portable.py",
            "build_cyberdaemon_aquastudio_style.py",
            "build_cyberdaemon_reliable.py",
            "build_cyberdaemon_final_hidfix.py",
            "build_appimage.py",
            "build_appimage.fish",
        }

        for item in base.iterdir():
            if item.name in ignored:
                continue

            target = (
                app_root
                / item.name
            )

            if item.is_dir():
                copy_tree(
                    item,
                    target,
                )
            elif item.is_file() and (
                item.suffix in {
                    ".py",
                    ".json",
                    ".txt",
                }
                or item.name == "LICENSE"
            ):
                copy_file(
                    item,
                    target,
                )

        # Exact runtime asset location used by the application.
        copy_tree(
            assets_dir,
            app_root
            / "ui"
            / "assets",
        )

        # ------------------------------------------------------
        # Python executable + libpython
        # ------------------------------------------------------
        print(
            "📦 Copying Python runtime"
        )

        copy_file(
            Path(sys.executable),
            bin_dir / "python3",
        )

        libpython = (
            Path(
                sysconfig.get_config_var(
                    "LIBDIR"
                )
                or ""
            )
            /
            (
                sysconfig.get_config_var(
                    "LDLIBRARY"
                )
                or ""
            )
        )

        if libpython.is_file():
            copy_file(
                libpython,
                lib_dir
                / libpython.name,
            )

        # ------------------------------------------------------
        # Qt plugins: query the REAL path from PySide6.
        # ------------------------------------------------------
        plugins_src, qml_src = qt_paths()

        if plugins_src is None:
            die(
                "PySide6 did not report a valid Qt "
                "plugin directory."
            )

        bundled_plugins = (
            usr
            / "lib"
            / "qt6"
            / "plugins"
        )

        print(
            "📦 Qt plugins:",
            plugins_src,
        )

        copy_tree(
            plugins_src,
            bundled_plugins,
        )

        # QML is deliberately not bundled. CyberDaemon has no need for
        # the host's KDE QML tree and copying it was the source of the
        # previous QML problems.
        if qml_src:
            print(
                "ℹ️ Qt QML found but not bundled:",
                qml_src,
            )

        # ------------------------------------------------------
        # Native library dependencies
        # ------------------------------------------------------
        print(
            "📦 Collecting native dependencies"
        )

        copy_native_dependencies(
            lib_dir,
            native_modules,
        )

        # Also scan all bundled Qt platform/plugin .so files.
        qt_plugin_binaries = list(
            bundled_plugins.rglob("*.so")
        )

        copy_native_dependencies(
            lib_dir,
            qt_plugin_binaries,
        )

        # ------------------------------------------------------
        # AppImage metadata
        # ------------------------------------------------------
        copy_file(
            icon,
            appdir
            / "CyberDaemon.png",
        )

        desktop = (
            appdir
            / "CyberDaemon.desktop"
        )

        desktop.write_text(
            "[Desktop Entry]\n"
            "Name=CyberDaemon\n"
            "Comment=HS80 MAX control for Linux\n"
            "Exec=CyberDaemon\n"
            "Icon=CyberDaemon\n"
            "Terminal=false\n"
            "Type=Application\n"
            "Categories=AudioVideo;Audio;\n",
            encoding="utf-8",
        )

        apprun = appdir / "AppRun"

        apprun.write_text(
            "#!/bin/sh\n"
            'HERE="$(dirname "$(readlink -f "$0")")"\n'
            f'PYVER="{sys.version_info.major}.{sys.version_info.minor}"\n'
            'QT_PLUGIN_ROOT="$HERE/usr/lib/qt6/plugins"\n'
            'export PYTHONHOME="$HERE/usr"\n'
            'export PYTHONPATH="$HERE/usr/lib/python${PYVER}/site-packages:$HERE/opt/cyberdaemon"\n'
            'export PATH="$HERE/usr/bin:$PATH"\n'
            'export LD_LIBRARY_PATH="$HERE/usr/lib:${LD_LIBRARY_PATH:-}"\n'
            'export QT_PLUGIN_PATH="$QT_PLUGIN_ROOT"\n'
            'export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLUGIN_ROOT/platforms"\n'
            'exec "$HERE/usr/bin/python3" "$HERE/opt/cyberdaemon/app.py" "$@"\n',
            encoding="utf-8",
        )

        apprun.chmod(0o755)

        # ------------------------------------------------------
        # Final sanity checks
        # ------------------------------------------------------
        checks = (
            appdir / "AppRun",
            appdir / "CyberDaemon.desktop",
            appdir / "CyberDaemon.png",
            bin_dir / "python3",
            app_root / "app.py",
            app_root
            / "ui"
            / "assets"
            / "icon_overview.svg",
            app_root
            / "ui"
            / "assets"
            / "linux_tux.svg",
            site_dir / "PySide6",
            site_dir / "shiboken6",
        )

        for check in checks:
            if not check.exists():
                die(
                    f"AppDir check failed: {check}"
                )

        platform_dir = (
            bundled_plugins
            / "platforms"
        )

        if not platform_dir.is_dir():
            die(
                f"Qt platforms directory missing: "
                f"{platform_dir}"
            )

        platform_plugins = list(
            platform_dir.glob("libq*.so")
        )

        if not platform_plugins:
            die(
                "No Qt platform plugins were bundled."
            )

        print(
            "✅ Qt platform plugins:",
            ", ".join(
                plugin.name
                for plugin in platform_plugins
            ),
        )

        print(
            "✅ AppDir sanity check OK"
        )
        print(
            "🔥 Creating AppImage"
        )

        env = os.environ.copy()
        env["ARCH"] = ARCH

        run(
            [
                appimagetool,
                str(appdir),
                str(output),
            ],
            cwd=base,
            env=env,
        )

    finally:
        shutil.rmtree(
            temp_root,
            ignore_errors=True,
        )

    if not output.is_file():
        die(
            f"AppImage was not created: {output}"
        )

    output.chmod(0o755)

    print()
    print("=" * 52)
    print("🎉 CYBERDAEMON FERTIG")
    print("=" * 52)
    print(output)
    print()
    print(
        "Profile storage:"
    )
    print(
        "  ~/.config/CyberDaemon/profiles.json"
    )
    print()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(
            f"❌ Build failed: "
            f"exit {exc.returncode}"
        )
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"❌ {exc}")
        raise SystemExit(1)
