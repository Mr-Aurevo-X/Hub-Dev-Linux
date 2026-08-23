#!/usr/bin/env bash
# Raccourci bureau Hub Dev (install locale ou dev tree)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
BIN="${HOME}/.local/bin"
mkdir -p "${APPS}" "${BIN}"
ln -sf "${ROOT}/LANCER.sh" "${BIN}/hub-dev"
cat > "${APPS}/hub-dev.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Hub Dev
Comment=Loopback et outils dev — Mr-Aurevo-X
Exec=${BIN}/hub-dev
Icon=org.mraurevox.HubDev
Terminal=false
Categories=Development;
EOF
chmod +x "${ROOT}/LANCER.sh"
update-desktop-database "${APPS}" 2>/dev/null || true
echo "OK — lance: hub-dev"
