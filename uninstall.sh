#!/usr/bin/env bash
# ARASAKA CYBERDECK // desinstalador (o historico de uso em ~/.config/arasaka-cyberdeck e mantido)
set -uo pipefail
APP_ID=arasaka-cyberdeck
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_ID"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
SCHEMA=org.gnome.settings-daemon.plugins.media-keys
KP=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/arasaka-cyberdeck/
if command -v gsettings >/dev/null && gsettings list-schemas | grep -qx $SCHEMA; then
  CUR=$(gsettings get $SCHEMA custom-keybindings)
  NEW=$(python3 -c "import ast,sys; l=[x for x in ast.literal_eval(sys.argv[1].replace('@as ','')) if x!=sys.argv[2]]; print(repr(l))" "$CUR" "$KP" 2>/dev/null)
  [ -n "$NEW" ] && gsettings set $SCHEMA custom-keybindings "$NEW"
  gsettings reset-recursively $SCHEMA.custom-keybinding:$KP 2>/dev/null
fi
rm -f "$HOME/.local/bin/$APP_ID" "$APPS/$APP_ID.desktop" \
      "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/$APP_ID.svg" \
      "${XDG_DATA_HOME:-$HOME/.local/share}/icons/Arasaka/scalable/apps/$APP_ID.svg"
rm -rf "$DATA/app" "$DATA/venv"
update-desktop-database -q "$APPS" 2>/dev/null
echo "■ Arasaka Cyberdeck removido (o atalho de teclado tambem)."
