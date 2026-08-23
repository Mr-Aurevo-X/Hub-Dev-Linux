# Hub Dev (Linux)

> **Dépôt privé** — plateforme Linux Mr-Aurevo-X (GTK 4 + Uni-UI).  
> **Private repo** — Mr-Aurevo-X Linux platform (GTK 4 + Uni-UI).

---

## Français

Lanceur localhost (ex-LocalDock) : scan des disques, tuiles, start/stop, ports. Outils : Diff texte, Snippets, JSON, .env, Lua.

- **GitHub** : `Mr-Aurevo-X/Hub-Dev-Linux` (privé)
- **Plateforme** : voir [linux-platform](https://github.com/Mr-Aurevo-X/linux-platform)

## Installation / Install

```bash
flatpak install --user -y https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases/latest/download/org.mraurevox.HubDev.flatpak
flatpak run org.mraurevox.HubDev
```

Dev local :

```bash
bash LANCER.sh
```

### Confidentialité

Local-first, pas de télémétrie. Vérif. GitHub au démarrage (lecture seule, pas de toggle). Pas d'install auto. Le Flatpak accède au disque hôte pour scanner et lancer vos serveurs.

---

## English

Localhost launcher (ex-LocalDock): disk scan, tiles, start/stop, ports. Tools: text diff, snippets, JSON, .env, Lua.

- **GitHub**: `Mr-Aurevo-X/Hub-Dev-Linux` (private)
- **Platform**: see [linux-platform](https://github.com/Mr-Aurevo-X/linux-platform)

### Privacy

Local-first, no telemetry. GitHub version check at startup (read-only, no toggle). No auto-install. The Flatpak uses host disk access to scan and start your servers.

---

Copyright © 2026 Mr-Aurevo-X
