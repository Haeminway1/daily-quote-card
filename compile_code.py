#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
FRONTEND = SRC / "frontend"
BACKEND = SRC / "backend"
CONTRACT_PATH = ROOT / "gas.project.json"


def main() -> int:
    contract = load_contract()
    build = require_build(contract)
    runtime = runtime_dir(contract)
    build_dir = runtime / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    code = compile_backend(build)
    html = compile_frontend(build, contract)

    write(build_dir / "Code.js", code)
    write(build_dir / "index.html", html)
    shutil.copyfile(ROOT / contract["payload"]["manifest"], build_dir / "appsscript.json")
    print(f"Built GAS payload at {build_dir}")
    return 0


def load_contract() -> dict:
    try:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"gas.project.json could not be read: {exc}") from exc


def require_build(contract: dict) -> dict:
    build = contract.get("build")
    if not isinstance(build, dict):
        raise SystemExit("gas.project.json build block is required")
    for field in ["plainScripts", "babelScripts", "backendFiles"]:
        value = build.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise SystemExit(f"gas.project.json build.{field} must be an array of non-empty strings")
    for field in ["mountComponent", "htmlTemplate"]:
        if not isinstance(build.get(field), str) or not build[field]:
            raise SystemExit(f"gas.project.json build.{field} must be a non-empty string")
    if not build["babelScripts"]:
        raise SystemExit("gas.project.json build.babelScripts must include at least one JSX entry")
    return build


def runtime_dir(contract: dict) -> Path:
    raw = os.environ.get("GAS_DEV_RUNTIME_DIR") or contract.get("runtimeDir")
    if not isinstance(raw, str) or not raw:
        raise SystemExit("gas.project.json runtimeDir must be a non-empty string")
    if raw == "~":
        return Path.home()
    if raw.startswith("~/"):
        return Path.home() / raw[2:]
    return Path(raw).expanduser().resolve()


def compile_backend(build: dict) -> str:
    parts = []
    for name in build["backendFiles"]:
        path = assert_file(BACKEND / name, f"build.backendFiles entry {name}")
        parts.append(f"// {name}\n{path.read_text(encoding='utf-8').rstrip()}\n")
    return "\n".join(parts)


def compile_frontend(build: dict, contract: dict) -> str:
    template = assert_file(ROOT / build["htmlTemplate"], "build.htmlTemplate").read_text(encoding="utf-8")
    if "width=device-width" not in template:
        raise SystemExit("build.htmlTemplate must include a mobile viewport meta tag")
    project_name = contract.get("wrapper", {}).get("projectName", "")
    wrapper_origin = contract.get("wrapper", {}).get("origin") or (f"https://{project_name}.pages.dev" if project_name else "")

    css = optional_text(FRONTEND / "css.html")
    bootstrap = optional_text(FRONTEND / "js.html")
    bundle = frontend_bundle(build)

    html = template.replace("<?!= include('css') ?>", css)
    html = html.replace("<?!= include('js') ?>", "\n".join([bootstrap, bundle]).strip())
    html = html.replace("<!-- CLAUDE_MOBILE_BUNDLE -->", bundle)
    html = html.replace("__WRAPPER_ORIGIN__", wrapper_origin)
    return html


def frontend_bundle(build: dict) -> str:
    parts = []
    for vendor in ["react.production.min.js", "react-dom.production.min.js"]:
        path = FRONTEND / "vendor" / vendor
        if path.exists():
            parts.append(script_tag(f"vendor/{vendor}", path.read_text(encoding="utf-8")))

    for name in build["plainScripts"]:
        path = resolve_frontend_file(name)
        parts.append(script_tag(name, path.read_text(encoding="utf-8")))

    for name in build["babelScripts"]:
        path = resolve_frontend_file(name)
        parts.append(script_tag(name, transform_jsx(path)))

    mount = "\n".join([
        "(function () {",
        "  var root = document.getElementById('root');",
        f"  var Component = window['{build['mountComponent']}'];",
        "  if (root && Component && window.React && window.ReactDOM) {",
        "    window.ReactDOM.createRoot(root).render(window.React.createElement(Component));",
        "  }",
        "  if (typeof window.updateMobileViewportStatus === 'function') {",
        "    window.updateMobileViewportStatus();",
        "  }",
        "})();",
    ])
    parts.append(script_tag("mount", mount.strip()))
    return "\n".join(parts)


def resolve_frontend_file(name: str) -> Path:
    candidates = [FRONTEND / name, FRONTEND / "claude" / name, ROOT / name]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(f"Missing build frontend source: {name}")


def transform_jsx(path: Path) -> str:
    command = [
        "npx",
        "--yes",
        "esbuild@0.25.5",
        str(path),
        "--loader:.jsx=jsx",
        "--jsx=transform",
        "--format=iife",
        "--log-level=warning",
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        message = "\n".join(part for part in [result.stdout, result.stderr] if part)
        raise SystemExit(f"Failed to transpile {path.name}:\n{message}")
    return result.stdout


def script_tag(label: str, code: str) -> str:
    safe = code.replace("</script>", "<\\/script>")
    return f'<script data-source="{label}">\n{safe.rstrip()}\n</script>'


def optional_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def assert_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(f"Missing {label}: {path}")
    return path


def write(path: Path, content: str) -> None:
    path.write_text(f"{content.rstrip()}\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(130)
