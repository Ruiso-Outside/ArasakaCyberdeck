"""
ARASAKA CYBERDECK // nucleo: o que da para abrir (apps, jogos, VMs, modulos, pastas, acoes) e a busca.
"""
from __future__ import annotations

import ast
import configparser
import json
import operator
import os
import sys
import re
import shlex
import shutil
import subprocess
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

APP_ID = "arasaka-cyberdeck"
APP_NAME = "ARASAKA CYBERDECK"
VERSION = "1.1.0"

HOME = Path.home()


def _config_home() -> Path:
    """Configuracoes: %APPDATA% no Windows, ~/.config (XDG) no Linux. Com a pasta pessoal trocada (testes), fica nela."""
    if sys.platform == "win32" and HOME == Path.home():
        return Path(os.environ.get("APPDATA") or HOME)
    return Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))


def _data_home() -> Path:
    """Dados: %LOCALAPPDATA% no Windows, ~/.local/share (XDG) no Linux."""
    if sys.platform == "win32" and HOME == Path.home():
        return Path(os.environ.get("LOCALAPPDATA") or HOME)
    return Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))


CONFIG_DIR = _config_home() / APP_ID
DATA_HOME = _data_home()
ASSETS = Path(__file__).resolve().parent / "assets"
LANG = (os.environ.get("LANG") or "pt_BR").split(".")[0]


@dataclass
class Item:
    key: str              # identificador estavel (para a contagem de uso)
    title: str
    kind: str             # APP, JOGO, VM, MODULO, PASTA, ACAO, CALC
    subtitle: str = ""
    icon: str = ""        # nome do tema de icones ou caminho
    run: list[str] = field(default_factory=list)   # comando
    url: str = ""         # ou um endereco para o xdg-open
    words: str = ""       # termos extras de busca
    confirm: str = ""     # pergunta antes (desligar, reiniciar)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ================================================================ Windows: Menu Iniciar, apps da Loja e acoes
WIN = sys.platform == "win32"
SKIP_LNK = re.compile(r"uninstall|desinstal|readme|leia-me|help|ajuda|manual|license|licen[cç]a|website|site da web", re.I)
STARTFILE = "@startfile"   # run = [STARTFILE, arquivo, argumentos...]: abre pelo Windows (atalhos .lnk)


def start_menu_dirs() -> list[Path]:
    dirs = [Path(os.environ.get("APPDATA") or HOME / "AppData/Roaming") / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("PROGRAMDATA") or "C:/ProgramData") / "Microsoft/Windows/Start Menu/Programs"]
    return [d for d in dirs if d.is_dir()]


def _url_target(f: Path) -> str:
    m = re.search(r"^URL=(.+)$", f.read_text(encoding="utf-8", errors="ignore"), re.M)
    return m.group(1).strip() if m else ""


def windows_apps() -> list[Item]:
    """Atalhos (.lnk e .url) do Menu Iniciar do usuario e de todos; o do usuario vence."""
    found: dict[str, Item] = {}
    for d in start_menu_dirs():
        for f in sorted(list(d.rglob("*.lnk")) + list(d.rglob("*.url"))):
            title = f.stem
            if title.lower() in found or SKIP_LNK.search(title):
                continue
            url = _url_target(f) if f.suffix.lower() == ".url" else ""
            folder = f.parent.name if f.parent != d else ""
            game = "steam://rungameid/" in url or bool(re.search(r"games|jogos|steam|epic|gog|ubisoft|ea app", folder, re.I))
            found[title.lower()] = Item(key="lnk:" + title.lower(), title=title, kind="JOGO" if game else "APP",
                                        subtitle=folder, icon=str(f), url=str(f), words=f"{folder} {url}")
    return list(found.values())


def _store_cache() -> Path:
    return CONFIG_DIR / "store-apps.json"


def refresh_store_apps():
    """Apps da Microsoft Store (Get-StartApps). Lento (~1 s): roda em segundo plano e fica guardado."""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                              "Get-StartApps | Where-Object { $_.AppID -like '*!*' } | Select-Object Name, AppID | ConvertTo-Json -Compress"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
        data = json.loads(out) if out else []
        data = [data] if isinstance(data, dict) else data
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _store_cache().write_text(json.dumps([{"name": a["Name"], "id": a["AppID"]} for a in data if a.get("Name")]), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def store_apps(existing: set[str]) -> list[Item]:
    c = _store_cache()
    try:
        fresh = time.time() - c.stat().st_mtime < 6 * 3600
        data = json.loads(c.read_text(encoding="utf-8"))
    except Exception:
        fresh, data = False, []
    if not fresh:
        import threading
        threading.Thread(target=refresh_store_apps, daemon=True).start()   # vale a partir da proxima abertura
    return [Item(key="uwp:" + a["id"], title=a["name"], kind="APP", subtitle="Microsoft Store", icon="",
                 url="shell:AppsFolder\\" + a["id"], words="loja store")
            for a in data if a["name"].lower() not in existing]


def steam_roots_windows() -> list[Path]:
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            roots.append(Path(winreg.QueryValueEx(k, "SteamPath")[0]))
    except Exception:  # noqa: BLE001
        pass
    roots.append(Path(os.environ.get("ProgramFiles(x86)") or "C:/Program Files (x86)") / "Steam")
    return roots


def windows_folders() -> list[Item]:
    """Pastas do usuario pelo registro do Explorer (seguem o lugar real, mesmo movidas para outro disco)."""
    names = {"Desktop": "Área de Trabalho", "{374DE290-123F-4565-9164-39C4925E467B}": "Downloads", "Personal": "Documentos",
             "My Music": "Músicas", "My Pictures": "Imagens", "My Video": "Vídeos"}
    out = [Item(key="dir:home", title="Pasta pessoal", kind="PASTA", subtitle=str(HOME), icon="user-home", url=str(HOME))]
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            for key, title in names.items():
                try:
                    p = Path(os.path.expandvars(winreg.QueryValueEx(k, key)[0]))
                except OSError:
                    continue
                if p.is_dir():
                    out.append(Item(key="dir:" + key.lower(), title=p.name, kind="PASTA", subtitle=str(p), icon="folder",
                                    url=str(p), words=title))
    except Exception:  # noqa: BLE001
        pass
    return out


def windows_actions() -> list[Item]:
    return [
        Item("act:lock", "Bloquear a tela", "ACAO", "Pede a senha para voltar", "system-lock-screen",
             ["rundll32.exe", "user32.dll,LockWorkStation"], words="bloquear lock trancar"),
        Item("act:suspend", "Suspender", "ACAO", "Dorme e volta de onde parou", "system-suspend",
             ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], words="suspender dormir sleep"),
        Item("act:logout", "Encerrar a sessão", "ACAO", "", "system-log-out", ["shutdown", "/l"], words="sair logout encerrar"),
        Item("act:reboot", "Reiniciar o PC", "ACAO", "", "system-reboot", ["shutdown", "/r", "/t", "0"], words="reiniciar reboot restart",
             confirm="Reiniciar o computador?"),
        Item("act:poweroff", "Desligar o PC", "ACAO", "", "system-shutdown", ["shutdown", "/s", "/t", "0"], words="desligar shutdown",
             confirm="Desligar o computador?"),
        Item("act:settings", "Configurações do sistema", "ACAO", "", "preferences-system", url="ms-settings:",
             words="configuracoes ajustes settings"),
    ]


def central_launcher_windows() -> list[str] | None:
    """O atalho da Central no Menu Iniciar ou na Area de Trabalho (aberto com argumentos pelo os.startfile)."""
    for d in start_menu_dirs() + [HOME / "Desktop"]:
        lnk = d / "Arasaka Central.lnk"
        if lnk.is_file():
            return [STARTFILE, str(lnk)]
    return None


# ================================================================ apps do menu (.desktop)
def app_dirs() -> list[Path]:
    dirs = [DATA_HOME / "applications", DATA_HOME / "flatpak/exports/share/applications",
            Path("/var/lib/flatpak/exports/share/applications"), Path("/var/lib/snapd/desktop/applications")]
    for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"):
        if d:
            dirs.append(Path(d) / "applications")
    seen, out = set(), []
    for d in dirs:
        if str(d) not in seen and d.is_dir():
            seen.add(str(d))
            out.append(d)
    return out


def _localized(sec, key: str) -> str:
    for k in (f"{key}[{LANG}]", f"{key}[{LANG.split('_')[0]}]", key):
        if k in sec:
            return sec[k]
    return ""


def desktop_apps() -> list[Item]:
    found: dict[str, Item] = {}
    desk = os.environ.get("XDG_CURRENT_DESKTOP", "GNOME").split(":")
    for d in app_dirs():
        for f in sorted(d.rglob("*.desktop")):
            fid = str(f.relative_to(d)).replace("/", "-")
            if fid in found:            # o primeiro diretorio (do usuario) vence
                continue
            cp = configparser.RawConfigParser(interpolation=None, strict=False)
            cp.optionxform = str
            try:
                cp.read(f, encoding="utf-8")
            except Exception:
                continue
            if "Desktop Entry" not in cp:
                continue
            e = cp["Desktop Entry"]
            if e.get("Type") != "Application" or e.get("NoDisplay") == "true" or e.get("Hidden") == "true":
                found[fid] = None  # type: ignore[assignment]   # escondido: tambem esconde os de baixo
                continue
            if e.get("OnlyShowIn") and not set(e["OnlyShowIn"].strip(";").split(";")) & set(desk):
                continue
            if e.get("NotShowIn") and set(e["NotShowIn"].strip(";").split(";")) & set(desk):
                continue
            exe = re.sub(r"%[fFuUdDnNickvm]", "", e.get("Exec", "")).strip()
            if not exe:
                continue
            try:
                cmd = shlex.split(exe)
            except ValueError:
                continue
            cats = e.get("Categories", "").split(";")
            kind = "JOGO" if "steam://rungameid/" in exe or ("Game" in cats and "Development" not in cats) else "APP"
            found[fid] = Item(key="app:" + fid, title=_localized(e, "Name") or f.stem, kind=kind,
                              subtitle=_localized(e, "Comment") or _localized(e, "GenericName"),
                              icon=e.get("Icon", ""), run=cmd,
                              words=" ".join([_localized(e, "Keywords"), _localized(e, "GenericName"), e.get("Categories", ""), f.stem]).replace(";", " "))
    return [x for x in found.values() if x]


# ================================================================ jogos da Steam
def steam_games(existing: set[str]) -> list[Item]:
    roots = steam_roots_windows() if WIN else [HOME / ".steam/steam", HOME / ".local/share/Steam",
                                                HOME / ".var/app/com.valvesoftware.Steam/.local/share/Steam"]
    libs: list[Path] = []
    for r in roots:
        vdf = r / "steamapps/libraryfolders.vdf"
        if vdf.is_file():
            libs.append(r / "steamapps")
            for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="ignore")):
                libs.append(Path(m.group(1)) / "steamapps")
    skip = re.compile(r"Proton|Steamworks|Steam Linux Runtime|SteamVR|Redistributable", re.I)
    out, seen = [], set()
    for lib in libs:
        for acf in lib.glob("appmanifest_*.acf"):
            t = acf.read_text(encoding="utf-8", errors="ignore")
            aid = re.search(r'"appid"\s+"(\d+)"', t)
            name = re.search(r'"name"\s+"([^"]+)"', t)
            if not aid or not name or skip.search(name.group(1)) or aid.group(1) in seen:
                continue
            seen.add(aid.group(1))
            url = f"steam://rungameid/{aid.group(1)}"
            if url in existing:
                continue
            out.append(Item(key="steam:" + aid.group(1), title=name.group(1), kind="JOGO", subtitle="Steam",
                            icon=f"steam_icon_{aid.group(1)}", url=url, words="jogo steam game"))
    return out


# ================================================================ ecossistema Arasaka
def blackwall_vms() -> list[Item]:
    root = DATA_HOME / "arasaka-blackwall/machines"
    try:
        cfg = json.loads((_config_home() / "arasaka-blackwall/config.json").read_text())
        root = Path(cfg.get("vm_dir") or root).expanduser()
    except Exception:
        pass
    out = []
    exe = shutil.which("arasaka-blackwall") or str(HOME / ".local/bin/arasaka-blackwall")
    for d in sorted(root.glob("*/vm.json")) if root.is_dir() else []:
        try:
            meta = json.loads(d.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append(Item(key="vm:" + d.parent.name, title=meta.get("name") or d.parent.name, kind="VM",
                        subtitle=f"Máquina virtual · {meta.get('profile', '')}".strip(" ·"), icon="arasaka-blackwall",
                        run=[exe, "--start", d.parent.name], words="vm maquina virtual ligar blackwall"))
    return out


def central_launcher() -> list[str] | None:
    if WIN:
        return central_launcher_windows()
    for f in (DATA_HOME / "applications/piphin-hub.desktop",):
        try:
            m = re.search(r"^Exec=(.+)$", f.read_text(encoding="utf-8"), re.M)
            if m:
                return shlex.split(re.sub(r"%[fFuU]", "", m.group(1)))
        except OSError:
            pass
    return None


def central_modules() -> list[Item]:
    root = _config_home() / "Arasaka Central/modules"
    launcher = central_launcher()
    if not launcher or not root.is_dir():
        return []
    out = []
    for mf in sorted(root.glob("*/module.json")):
        try:
            m = json.loads(mf.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        icon = next((str(p) for p in (mf.parent / "icons").glob("*.png")), "") if (mf.parent / "icons").is_dir() else ""
        out.append(Item(key="mod:" + m.get("id", mf.parent.name), title=m.get("name", mf.parent.name), kind="MODULO",
                        subtitle="Módulo da Arasaka Central", icon=icon, run=launcher + [f"--module={m.get('id', mf.parent.name)}"],
                        words="central modulo " + (m.get("description") or "")))
    return out


# ================================================================ pastas e acoes
def folders() -> list[Item]:
    if WIN:
        return windows_folders()
    names = {"DESKTOP": "Área de Trabalho", "DOWNLOAD": "Downloads", "DOCUMENTS": "Documentos", "MUSIC": "Músicas",
             "PICTURES": "Imagens", "VIDEOS": "Vídeos"}
    out = [Item(key="dir:home", title="Pasta pessoal", kind="PASTA", subtitle=str(HOME), icon="user-home", url=HOME.as_uri())]
    try:
        txt = (_config_home() / "user-dirs.dirs").read_text(encoding="utf-8")
    except OSError:
        txt = ""
    for key, title in names.items():
        m = re.search(rf'^XDG_{key}_DIR="?([^"\n]+)"?', txt, re.M)
        p = Path(m.group(1).replace("$HOME", str(HOME))) if m else None
        if p and p.is_dir() and p != HOME:
            out.append(Item(key="dir:" + key.lower(), title=p.name, kind="PASTA", subtitle=str(p), icon="folder", url=p.as_uri(), words=title))
    return out


def actions() -> list[Item]:
    if WIN:
        return windows_actions()
    return [
        Item("act:lock", "Bloquear a tela", "ACAO", "Pede a senha para voltar", "system-lock-screen", ["loginctl", "lock-session"], words="bloquear lock trancar"),
        Item("act:suspend", "Suspender", "ACAO", "Dorme e volta de onde parou", "system-suspend", ["systemctl", "suspend"], words="suspender dormir sleep"),
        Item("act:logout", "Encerrar a sessão", "ACAO", "", "system-log-out", ["gnome-session-quit", "--logout"], words="sair logout encerrar"),
        Item("act:reboot", "Reiniciar o PC", "ACAO", "", "system-reboot", ["gnome-session-quit", "--reboot"], words="reiniciar reboot restart",
             confirm="Reiniciar o computador?"),
        Item("act:poweroff", "Desligar o PC", "ACAO", "", "system-shutdown", ["gnome-session-quit", "--power-off"], words="desligar shutdown",
             confirm="Desligar o computador?"),
        Item("act:settings", "Configurações do sistema", "ACAO", "", "preferences-system", ["gnome-control-center"], words="configuracoes ajustes settings"),
    ]


# ================================================================ calculadora (sem eval)
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos}


def calc(q: str) -> str | None:
    expr = q.strip().lstrip("=").replace(",", ".").replace("x", "*").replace("^", "**")
    if not expr or not re.fullmatch(r"[\d\s.+\-*/%()]+", expr) or not re.search(r"\d\s*[-+*/%]", expr):
        return None

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100:
                raise ValueError
            return OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
            return OPS[type(n.op)](ev(n.operand))
        raise ValueError
    try:
        v = ev(ast.parse(expr, mode="eval"))
    except Exception:
        return None
    if isinstance(v, float):
        v = round(v, 10)
        if v.is_integer():
            v = int(v)
    return f"{v:,}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(v, int) else str(v).replace(".", ",")


# ================================================================ indice e busca
class Index:
    def __init__(self):
        self.items: list[Item] = []
        self.usage_path = CONFIG_DIR / "usage.json"
        try:
            self.usage: dict[str, list] = json.loads(self.usage_path.read_text(encoding="utf-8"))
        except Exception:
            self.usage = {}
        self.reload()

    def reload(self):
        apps = windows_apps() if WIN else desktop_apps()
        if WIN:
            apps += store_apps({a.title.lower() for a in apps})
        urls = {" ".join(a.run) + " " + a.words for a in apps}
        existing = {u for s in urls for u in re.findall(r"steam://rungameid/\d+", s)}
        self.items = apps + steam_games(existing) + blackwall_vms() + central_modules() + folders() + actions()
        for it in self.items:
            it._n = norm(it.title)                                   # type: ignore[attr-defined]
            it._w = norm(f"{it.title} {it.subtitle} {it.words}")    # type: ignore[attr-defined]

    def boost(self, key: str) -> float:
        u = self.usage.get(key)
        if not u:
            return 0.0
        count, last = u
        age_days = (time.time() - last) / 86400
        return min(count, 30) * 2.0 / (1 + age_days / 7)

    def used(self, key: str):
        c, _ = self.usage.get(key, [0, 0])
        self.usage[key] = [c + 1, time.time()]
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.usage_path.write_text(json.dumps(self.usage), encoding="utf-8")
        except OSError:
            pass

    def search(self, q: str, limit: int = 9) -> list[Item]:
        nq = norm(q.strip())
        res: list[tuple[float, Item]] = []
        c = calc(q)
        if c is not None:
            res.append((1e9, Item("calc", c, "CALC", f"{q.strip()} =  ·  Enter copia o resultado", "accessories-calculator")))
        if not nq:
            ranked = sorted((it for it in self.items if self.usage.get(it.key)), key=lambda it: -self.boost(it.key))
            return [r for _, r in res] + ranked[:limit]
        words = nq.split()
        for it in self.items:
            n, w = it._n, it._w     # type: ignore[attr-defined]
            if n == nq:
                s = 100.0
            elif n.startswith(nq):
                s = 80.0
            elif any(part.startswith(nq) for part in re.split(r"[\s\-_.:]+", n)):
                s = 65.0
            elif all(x in w for x in words):
                s = 40.0 if nq in n else 30.0
            elif _initials(n).startswith(nq.replace(" ", "")):
                s = 50.0
            elif _subseq(nq.replace(" ", ""), n.replace(" ", "")):
                s = 12.0
            else:
                continue
            res.append((s + self.boost(it.key) - len(n) * 0.05, it))
        res.sort(key=lambda x: -x[0])
        return [it for _, it in res[:limit]]


def _initials(n: str) -> str:
    return "".join(p[0] for p in re.split(r"[\s\-_.:]+", n) if p)


def _subseq(q: str, s: str) -> bool:
    it = iter(s)
    return len(q) >= 3 and all(c in it for c in q)


def launch(it: Item) -> str | None:
    """Abre o item. Devolve um erro (texto) ou None."""
    try:
        if WIN:
            return _launch_windows(it)
        if it.url:
            subprocess.Popen(["xdg-open", it.url], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif it.run:
            subprocess.Popen(it.run, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(HOME))
        else:
            return "nada para abrir"
    except FileNotFoundError:
        return f"programa não encontrado: {it.run[0] if it.run else it.url}"
    except Exception as e:  # noqa: BLE001
        return str(e)
    return None


def _launch_windows(it: Item) -> str | None:
    if it.url:
        os.startfile(it.url)                                  # noqa: S606 - atalho, pasta, endereco ou app da Loja
    elif it.run and it.run[0] == STARTFILE:
        os.startfile(it.run[1], "open", subprocess.list2cmdline(it.run[2:]), str(HOME))  # noqa: S606
    elif it.run:
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(it.run, creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(HOME))
    else:
        return "nada para abrir"
    return None
