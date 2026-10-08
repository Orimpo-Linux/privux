# Privux

Distribució Linux de privacitat d'**Orimpo**. Aquest repositori conté la **fase 1 (prova de concepte)** del full de ruta: l'eina `privux` i els paquets Debian, sense ISO encara.

> Estat: prova de concepte. Pensat per provar-lo sobre un **Debian 13 amb KDE Plasma** instal·lat a mà, idealment en maquinari real.

## Què hi ha

| Part | Què fa |
|---|---|
| `src/privux/` | L'eina `privux` (Python 3.11+, **sense dependències**) |
| `debian/` | Empaquetat: `privux-cli` (l'eina) i `privux-desktop` (meta-paquet: Plasma, Firefox ESR, LibreOffice, Thunderbird, firmware...) |
| `tests/` | Tests amb `unittest`, contra un arrel temporal |
| `.github/workflows/ci.yml` | CI: tests + construcció dels `.deb` dins `debian:trixie` |
| `docs/` | Document base del projecte (decisions, riscos, full de ruta) |

## L'eina `privux`

Cada ajust és una **opció independent** amb valor per defecte. El perfil «Alta privacitat» és simplement el conjunt dels valors per defecte; afegir «Estàndard» o «Paranoia» més endavant serà definir un altre conjunt de valors.

| Opció | Per defecte | Què configura |
|---|---|---|
| `firewall` | `on` | nftables: denega l'entrada, permet tot el que inicia la màquina. Només toca la taula `inet privux`, no la de Docker/libvirt |
| `dns` | `quad9` | DNS sobre TLS amb systemd-resolved. Valors: `quad9`, `quad9-unfiltered`, `mullvad`, `off` |
| `mac_randomization` | `on` | NetworkManager: MAC diferent per a cada xarxa (`stable`) |
| `kernel_hardening` | `on` | sysctl: nucli i pila de xarxa |
| `firefox_hardening` | `on` | Política de Firefox ESR: sense telemetria, protecció contra seguiment, uBlock Origin. **Sense** `resistFingerprinting` (trenca pàgines) |
| `auto_updates` | `on` | `unattended-upgrades` per a actualitzacions de seguretat, **mai** reinicia sol |

```
privux                       # = privux status
privux status [--json]       # l'estat real vs. l'esperat (exit 1 si hi ha diferències)
privux list [--json]         # opcions, valor actual, valors possibles
privux get dns
sudo privux set dns mullvad  # desa i aplica una sola opció
sudo privux set firewall off
sudo privux apply [--dry-run]
sudo privux reset [opció...] # torna als valors per defecte
```

`--json` està pensat per al futur **panell de configuració de Plasma**, que serà una capa fina sobre aquesta mateixa eina.

### Garanties de seguretat del motor

- Els ajustos que l'usuari canvia es guarden a `/etc/privux/privux.conf`; només es desa el que s'ha canviat, així els valors per defecte poden millorar amb les actualitzacions.
- Si `privux` ha de sobreescriure un fitxer que **no** és seu (per exemple el `/etc/nftables.conf` de Debian), en guarda una còpia **una sola vegada** com a `<fitxer>.privux-orig`.
- No esborra mai un fitxer que no sigui seu.
- Si una ordre posterior (`systemctl`, `sysctl`...) falla, és un avís, no un error.

## Desenvolupament

```
make test        # tests (cap dependència externa)
make deb         # construeix els .deb (cal debhelper, dh-python, pybuild-plugin-pyproject)
```

**Prova-ho sempre contra un arrel temporal, no contra el teu sistema.** `--root` redirigeix tot el que escriu `privux`:

```
R=$(mktemp -d)
PYTHONPATH=src python3 -m privux --root $R apply
PYTHONPATH=src python3 -m privux --root $R status
```

> Compte: si executes `privux apply` com a root **sense** `--root`, s'aplica de debò a la màquina (inclòs el tallafocs d'entrada: una sessió SSH nova deixaria d'entrar).

## Per verificar en un Debian 13 real

Aquests punts s'han escrit a partir de la documentació i el coneixement dels paquets, però **no s'han pogut comprovar en un Debian 13**. Són la primera tasca de la prova de concepte:

1. **Ruta de les polítiques de Firefox ESR.** S'usa `/etc/firefox/policies/policies.json`; confirmar que el `firefox-esr` de Debian la llegeix. Confirmar també que `browser.contentblocking.category` s'accepta com a preferència de política.
2. **`systemd-resolved` a Debian 13.** És un paquet separat; comprovar que `/etc/resolv.conf` apunta a l'stub i que NetworkManager l'usa.
3. **DNS sobre TLS amb portals captius** (hotels, universitats): amb `DNSOverTLS=yes` el portal no es pot obrir. Solució prevista al panell: un botó «mode portal captiu» que desactivi temporalment `dns` i `mac_randomization`. De moment: `sudo privux set dns off`.
4. **Adreces IP dels resolutors** (Quad9, Mullvad): contrastar-les amb la documentació oficial dels proveïdors.
5. **El `.deb`.** El flux `pybuild` amb `--destdir=debian/privux-cli` (a `debian/rules`) no s'ha pogut provar en local. La CI amb `debian:trixie` és qui ho ha de validar.
6. **Instantànies Btrfs abans d'actualitzar** (Snapper): encara no està integrat.

## Pendent de decidir

- **Llicència.** `debian/copyright` diu GPL-3+ de manera **provisional**. Decidir-ho abans de publicar.
- **Correu del mantenidor** i **URL de GitHub** a `debian/control`: ara són marcadors (`info@orimpo.invalid`, `github.com/orimpo/privux`).
- **Element.** No és als repositoris de Debian; la via prevista és Flatpak (`im.riot.Riot`). No està al meta-paquet encara.
- **Antivirus (ClamAV)**, **client VPN** i **panell**: fases 2 i 3 del full de ruta.

## Textos i idioma

El codi i els comentaris són en anglès; els textos de cara a l'usuari són en català i passen per la funció `_()` (a `options.py`), de manera que traduir-los amb gettext més endavant no obliga a tocar la lògica.
