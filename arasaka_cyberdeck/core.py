"""
ARASAKA CYBERDECK // nucleo: o que da para abrir (apps, jogos, VMs, modulos, pastas, acoes) e a busca.
"""
from __future__ import annotations

import ast
import configparser
import json
import operator
import os
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
VERSION = "1.0.0"

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / APP_ID
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
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
    roots = [HOME / ".steam/steam", HOME / ".local/share/Steam", HOME / ".var/app/com.valvesoftware.Steam/.local/share/Steam"]
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
        cfg = json.loads((Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "arasaka-blackwall/config.json").read_text())
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
    for f in (DATA_HOME / "applications/piphin-hub.desktop",):
        try:
            m = re.search(r"^Exec=(.+)$", f.read_text(encoding="utf-8"), re.M)
            if m:
                return shlex.split(re.sub(r"%[fFuU]", "", m.group(1)))
        except OSError:
            pass
    return None


def central_modules() -> list[Item]:
    root = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "Arasaka Central/modules"
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
    names = {"DESKTOP": "Área de Trabalho", "DOWNLOAD": "Downloads", "DOCUMENTS": "Documentos", "MUSIC": "Músicas",
             "PICTURES": "Imagens", "VIDEOS": "Vídeos"}
    out = [Item(key="dir:home", title="Pasta pessoal", kind="PASTA", subtitle=str(HOME), icon="user-home", url=HOME.as_uri())]
    try:
        txt = (Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "user-dirs.dirs").read_text(encoding="utf-8")
    except OSError:
        txt = ""
    for key, title in names.items():
        m = re.search(rf'^XDG_{key}_DIR="?([^"\n]+)"?', txt, re.M)
        p = Path(m.group(1).replace("$HOME", str(HOME))) if m else None
        if p and p.is_dir() and p != HOME:
            out.append(Item(key="dir:" + key.lower(), title=p.name, kind="PASTA", subtitle=str(p), icon="folder", url=p.as_uri(), words=title))
    return out


def actions() -> list[Item]:
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
        apps = desktop_apps()
        urls = {" ".join(a.run) for a in apps}
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
