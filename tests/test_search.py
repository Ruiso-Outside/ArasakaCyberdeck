"""Busca e calculadora do Cyberdeck com atalhos (.desktop) de teste.   python tests/test_search.py"""
import os
import sys
import tempfile
from pathlib import Path

T = Path(tempfile.mkdtemp())
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
assert "Firefox" in titles("navegador"), "palavra-chave do .desktop"
assert "Escondido" not in titles("esc"), "NoDisplay fica fora"
assert titles("ad")[0] == "Arasaka Daemon", "iniciais"
assert titles("term")[0] == "Terminal"
assert titles("desl")[0] == "Desligar o PC"
assert C.calc("2+3*4") == "14" and C.calc("12/5") == "2,4" and C.calc("10^3") == "1.000"
assert C.calc("abc") is None and C.calc("2**999999") is None and C.calc("__import__('os')") is None
ff = next(i for i in ix.items if i.title == "Firefox")
assert ff.run == ["firefox"], "tira os %U do Exec"
ix.used(ix.search("term")[0].key)
assert titles("")[0] == "Terminal", "mais usados primeiro"
print("OK: busca, palavras-chave, iniciais, escondidos, calculadora e mais usados")
