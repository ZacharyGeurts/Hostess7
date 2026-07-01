# NEXUS-Shield Wiki

**Live wiki:** https://github.com/ZacharyGeurts/NEXUS-Shield/wiki

**GitHub Pages manual (illustrated):** https://zacharygeurts.github.io/NEXUS-Shield/

---

## Pages (g16 1.0)

| Page | Topic |
|------|-------|
| [Home](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Home) | Overview |
| [Host Desktop](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Host-Desktop) | First page, startbar, app mirror |
| [Queen Browser](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Queen-Browser) | Browser chrome, OS inside, drop/rise |
| [Host Freeze](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Host-Freeze) | Soft/mem/disk freeze |
| [Installers](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Installers) | Clone + scripts |
| [Field I/O](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Field-IO) | API, state, diagrams |
| [Field Thermal Guard](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Field-Thermal-Guard) | Landauer budget, incremental redata |
| [Panel Guide](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Panel-Guide) | Command deck tabs + screenshots |
| [Linux Installation](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Linux-Installation) | Install & verify |
| [Boot Implementation](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Boot-Implementation) | Reboot reload |
| [Underlay F9 Tristate](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Underlay-F9-Tristate) | 2026 installer |
| [Architecture](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Architecture) | Module map |
| [Configuration](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Configuration) | Config layers |
| [Self-Defense](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Self-Defense) | Manifest signing |
| [Licensing](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Licensing) | MIT vs GPL |

---

## Publish wiki

```bash
./scripts/publish-wiki.sh
```

Or manually:

```bash
git clone https://github.com/ZacharyGeurts/NEXUS-Shield.wiki.git
rsync -a --delete wiki/ NEXUS-Shield.wiki/
cd NEXUS-Shield.wiki && git add -A && git commit -m "wiki: g16 1.0 host desktop, Queen Browser, host freeze" && git push
```