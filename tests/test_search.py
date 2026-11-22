"""Busca e calculadora do Cyberdeck com atalhos de teste (.desktop no Linux, Menu Iniciar no Windows).
python tests/test_search.py"""
import json
import os
import sys
import tempfile
from pathlib import Path

WIN = sys.platform == "win32"
T = Path(tempfile.mkdtemp())
if WIN:
    # Menu Iniciar falso: atalhos .url (texto), uma pasta de programa e um desinstalador (fica fora)
    menu = T / "roaming" / "Microsoft/Windows/Start Menu/Programs"
    (menu / "Mozilla").mkdir(parents=True)
    (menu / "Firefox.url").write_text("[InternetShortcut]\nURL=file:///C:/firefox.exe\n")
    (menu / "Terminal.url").write_text("[InternetShortcut]\nURL=file:///C:/wt.exe\n")
    (menu / "Mozilla" / "Desinstalar Firefox.url").write_text("[InternetShortcut]\nURL=file:///C:/u.exe\n")
    (menu / "Arasaka Daemon.url").write_text("[InternetShortcut]\nURL=file:///C:/d.cmd\n")
    (menu / "Jogo.url").write_text("[InternetShortcut]\nURL=steam://rungameid/570\n")
    cfg = T / "roaming" / "arasaka-cyberdeck"
    cfg.mkdir(parents=True)
    (cfg / "store-apps.json").write_text(json.dumps([{"name": "Calculadora", "id": "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"}]))
    os.environ.update(APPDATA=str(T / "roaming"), LOCALAPPDATA=str(T / "local"), PROGRAMDATA=str(T / "none"))
else:
    apps = T / "data" / "applications"
    apps.mkdir(parents=True)
    for fid, name, extra in [("firefox", "Firefox", "Keywords=navegador;web;"), ("org.gnome.Terminal", "Terminal", ""),
                             ("escondido", "Escondido", "NoDisplay=true"), ("arasaka-daemon", "Arasaka Daemon", "Comment=IDE")]:
        (apps / f"{fid}.desktop").write_text(f"[Desktop Entry]\nType=Application\nName={name}\nExec={fid} %U\nIcon={fid}\n{extra}\n")
    os.environ.update(HOME=str(T), XDG_DATA_HOME=str(T / "data"), XDG_DATA_DIRS=str(T / "none"), XDG_CONFIG_HOME=str(T / "cfg"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from arasaka_cyberdeck import core as C  # noqa: E402

ix = C.Index()
titles = lambda q: [i.title for i in ix.search(q)]  # noqa: E731
assert titles("fire")[0] == "Firefox"
assert titles("ad")[0] == "Arasaka Daemon", "iniciais"
assert titles("term")[0] == "Terminal"
assert titles("desl")[0] == "Desligar o PC"
assert C.calc("2+3*4") == "14" and C.calc("12/5") == "2,4" and C.calc("10^3") == "1.000"
assert C.calc("abc") is None and C.calc("2**999999") is None and C.calc("__import__('os')") is None
if WIN:
    assert not any("Desinstalar" in t for t in titles("firefox")), "desinstalador fica fora"
    assert next(i for i in ix.items if i.title == "Jogo").kind == "JOGO", "atalho da Steam e jogo"
    calc_app = next(i for i in ix.items if i.title == "Calculadora")
    assert calc_app.url == "shell:AppsFolder\\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App", "app da Loja"
    assert next(i for i in C.actions() if i.key == "act:poweroff").run[:2] == ["shutdown", "/s"]
else:
    assert "Firefox" in titles("navegador"), "palavra-chave do .desktop"
    assert "Escondido" not in titles("esc"), "NoDisplay fica fora"
    ff = next(i for i in ix.items if i.title == "Firefox")
    assert ff.run == ["firefox"], "tira os %U do Exec"
ix.used(ix.search("term")[0].key)
assert titles("")[0] == "Terminal", "mais usados primeiro"
assert str(C.CONFIG_DIR).startswith(str(T)), "configuracoes na pasta de teste"
print("OK: busca, atalhos, iniciais, escondidos, calculadora e mais usados" + (" (Windows)" if WIN else ""))
