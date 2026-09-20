# Hub Dev (Linux)

> **WIP** — encore en développement.  
> **WIP** — still in development.

Lanceur localhost (ex-LocalDock) : scan des disques, tuiles, start/stop, ports. Outils : Diff texte, Snippets, JSON, .env, Lua.

**1.2.8** — [releases](https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases) · GPL-3.0-or-later · © 2026 Mr-Aurevo-X

---

## Français

### Installer (Flatpak)

Prérequis : [Flatpak](https://flatpak.org/setup/) + runtime GNOME 49 (installé automatiquement depuis Flathub au premier `flatpak install`).

```bash
rm -f org.mraurevox.HubDev.flatpak
wget --no-continue -O org.mraurevox.HubDev.flatpak \
  https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases/download/v1.2.8/org.mraurevox.HubDev.flatpak
flatpak install --user -y --reinstall ./org.mraurevox.HubDev.flatpak
wget --no-continue -O INSTALLER-RACCOURCI-FLATPAK.sh \
  https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases/download/v1.2.8/INSTALLER-RACCOURCI-FLATPAK.sh
bash ./INSTALLER-RACCOURCI-FLATPAK.sh
flatpak run org.mraurevox.HubDev
```

Dev sans installer : `bash LANCER.sh`

### Ce que ça fait

- Loopback : scan, tuiles, start / stop, ports locaux
- Arrêter coupe le process qui écoute le port (pas seulement le helper Flatpak)
- Outils : diff texte, snippets, JSON, .env, Lua

### Ce que ça ne fait pas

Pas de télémétrie, pas d’install automatique, pas de canal Flathub.  
Le Flatpak accède au disque hôte pour scanner et lancer **vos** serveurs.

### Confidentialité

Local-first. Données : `~/.config/Mr-Aurevo-X/hubs/dev/`.  
Vérif. GitHub au démarrage (lecture seule, pas de toggle).  
Texte : [LEGAL.md](LEGAL.md).

---

## English

Localhost launcher (ex-LocalDock): disk scan, tiles, start/stop, ports. Tools: text diff, snippets, JSON, .env, Lua.

### Install (Flatpak)

```bash
rm -f org.mraurevox.HubDev.flatpak
wget --no-continue -O org.mraurevox.HubDev.flatpak \
  https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases/download/v1.2.8/org.mraurevox.HubDev.flatpak
flatpak install --user -y --reinstall ./org.mraurevox.HubDev.flatpak
wget --no-continue -O INSTALLER-RACCOURCI-FLATPAK.sh \
  https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases/download/v1.2.8/INSTALLER-RACCOURCI-FLATPAK.sh
bash ./INSTALLER-RACCOURCI-FLATPAK.sh
flatpak run org.mraurevox.HubDev
```

Dev without install: `bash LANCER.sh`

Stop kills the process listening on the port (not only the Flatpak helper).  
No telemetry, no auto-install. The Flatpak uses host disk access to scan and start your servers. See [LEGAL.md](LEGAL.md).

---

## Soutien (optionnel) / Support (optional)

Si le boulot te plaît, un café — sinon profite.  
If you like the work, a coffee — otherwise just enjoy it.

[![Discord](https://img.shields.io/badge/Discord-Mr--Aurevo--X-5865F2?style=for-the-badge&logo=discord&logoColor=white&labelColor=050807)](https://discord.com/users/406891052516114442)

---

Copyright © 2026 Mr-Aurevo-X — GPL-3.0-or-later
