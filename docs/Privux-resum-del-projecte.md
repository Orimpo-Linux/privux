# Privux — Document base del projecte

**Empresa:** Orimpo
**Producte:** Privux, distribució Linux enfocada a la privacitat
**Data:** 4 d'octubre de 2026
**Estat:** fase de definició (abans de la prova de concepte)

---

## 1. Visió

Privux és una distribució Linux de codi obert pensada per a la privacitat quotidiana, amb una experiència d'ús cuidada i accessible. Vol resoldre el problema que detecteu a distros com Kali: són potents, però incòmodes per a l'ús diari (interfície poc polida, transicions pobres, sensació de lentitud).

**Proposta de valor en una frase:** una distro de privacitat que un usuari que ve de Windows o macOS pot fer servir des del primer dia, i que alhora porta les eines d'un especialista en ciberseguretat quan les necessita.

**Nota sobre referents:** Kali és una distro d'auditoria i pentesting, no de privacitat. Els referents reals en privacitat són Tails, Whonix, Qubes i Kicksecure. Privux s'ha de poder diferenciar d'ells en una frase; el diferenciador actual és *privacitat d'ús diari + usabilitat tipus Mint + arsenal de ciberseguretat opcional + VPN integrada*.

## 2. Públic objectiu i model d'amenaça

**Públic:**
- Usuari general que ve de Windows o macOS i no ha tocat mai Linux.
- Particulars i empreses amb informació sensible o confidencial.
- Especialistes en ciberseguretat que volen una alternativa més còmoda (en instal·lació directa o en VM).

**Protegeix contra:**
- Seguiment publicitari i telemetria.
- Aplicacions que espien o filtren dades.
- Robatori o pèrdua de l'equip (xifrat de disc).
- Software maliciós habitual.

**No protegeix contra (s'ha de dir clarament a la documentació):**
- Un adversari estatal o molt capaç.
- L'observació de la xarxa per part de l'operador d'internet quan la VPN no està activa: el trànsit va xifrat, però es veu amb quins servidors es connecta l'usuari.

> Recomanació: redactar aquest model d'amenaça en una o dues pàgines públiques. Evita la falsa sensació de seguretat, que és pitjor que no tenir res.

## 3. Decisions preses

| Àrea | Decisió |
|---|---|
| Base | **Debian 13 estable ("trixie")** |
| Escriptori | **KDE Plasma 6 sobre Wayland**, amb aspecte propi i coherent, proper a Windows |
| Arquitectura | **Només x86_64**, Intel i AMD (ARM queda per a més endavant) |
| Gràfiques NVIDIA | Només drivers oberts (Nouveau/NVK) |
| Wi-Fi | Xipsets habituals (Intel, Realtek, Qualcomm) |
| Firmware i microcodi tancats | **Inclosos per defecte**, explicats a la documentació com a única excepció justificada a "tot obert" |
| Instal·lador | **Calamares** (gràfic), personalitzat amb la marca |
| Xifrat de disc | **LUKS2 obligatori** per defecte |
| Sistema de fitxers | **Btrfs** amb instantànies (Snapper) |
| Arrencada dual | Permesa amb Windows |
| Mode live | **No** per a l'usuari final (la ISO arrenca directament a l'instal·lador) |
| Perfil de privacitat | **Un sol perfil: Alta privacitat**, amb cada funció activable o desactivable per separat |
| VPN per defecte | Client integrat, **no activa per defecte** (no obligatòria) |
| Tor | Només com a Tor Browser a part, sense passar tot el sistema per Tor |
| DNS | **Quad9** xifrat per defecte, canviable des del panell |
| Navegador | **Firefox ESR endurit** (protecció contra seguiment estricta, uBlock Origin, sense telemetria); Tor Browser opcional |
| Ofimàtica | LibreOffice |
| Correu | Thunderbird |
| Missatgeria | **Element** preinstal·lat |
| Programes de Windows | Aplicacions natives de Linux primer; **Wine** com a pla B |
| Actualitzacions | Seguretat **automàtiques** (`unattended-upgrades`) |
| Marxa enrere | **Btrfs + Snapper**: instantània abans de cada actualització gran |
| Versions | Quan estiguin llestes, **sense data fixa** |
| Pentest | **Meta-paquets opcionals** per àrees (no una edició separada) |
| Llicència i model | **Tot codi obert**; ingressos via suport i serveis a empreses i particulars |
| Nom i marca | **Privux** i **Orimpo** |
| Acord d'equip | Ja creat i signat |

### 3.1 Capa de hardening per defecte (Alta privacitat)

- Tallafocs amb denegació d'entrada (nftables).
- MAC aleatòria per connexió, amb interruptor fàcil per als portals captius.
- DNS xifrat amb Quad9.
- AppArmor activat; aplicacions en Flatpak amb permisos.
- Firefox ESR amb protecció contra seguiment estricta i uBlock Origin. **Sense** `resistFingerprinting` per defecte, perquè trenca massa pàgines.
- Cap servei del sistema que enviï dades a l'exterior.
- Límit de disseny: Alta privacitat no pot trencar l'ús normal (banca, streaming, portals).

### 3.2 Eina `privux` i panell de configuració

- **Eina de terminal `privux`** (per exemple `privux status`), construïda al voltant d'**opcions individuals**, cadascuna amb el seu valor per defecte. Un perfil és només un conjunt predefinit d'opcions; afegir Estàndard o Paranoia més endavant serà escriure un fitxer de configuració nou.
- **Panell gràfic integrat a la Configuració de Plasma**, com a capa fina sobre `privux`. Apartats del primer llançament:
  - **VPN:** connectar/desconnectar, servidor, kill switch, importar configuracions `.conf` externes.
  - **Antivirus:** estat, escaneig i gestió.
  - **Actualitzacions:** sistema i seguretat.
  - **Xarxa:** DNS, MAC aleatòria, tallafocs.
- Fase posterior: icona d'estat a la safata del sistema i gestor de permisos d'aplicacions (càmera, micròfon, ubicació).

### 3.3 Antivirus

- Protecció lleugera per defecte: escaneig de descàrregues i dispositius USB (base ClamAV), amb interfície senzilla.
- Anàlisi profunda dins del meta-paquet de malware, sempre en entorn aïllat.
- Pendent: decidir si l'antivirus tindrà marca i nom propis.

### 3.4 Eines de ciberseguretat (meta-paquets)

Prioritat decidida:

1. **Privacitat i anonimat** (Tor, metadades, OSINT, neteja de rastres). És el que us diferencia de Kali.
2. **Enginyeria inversa i anàlisi de malware** (Ghidra, radare2/Cutter, YARA). Ha de viure en un entorn aïllat (VM o contenidor).
3. **Wi-Fi i xarxes sense fil** (depèn d'adaptadors amb mode monitor; cal definir quins xipsets es garanteixen).

Auditoria de xarxes i web queda per a una segona fase. Idea d'estructura: `privux-pentest-privacitat`, `privux-pentest-malware`, `privux-pentest-wifi`. Començar amb 30-50 eines ben integrades, no competir en volum.

### 3.5 VPN d'Orimpo

- Protocol: **WireGuard**.
- Client: app gràfica pròpia, integrada al panell, que connecta als servidors d'Orimpo i també accepta configuracions externes.
- Servidor: un servidor antic **només per a proves**. L'allotjament definitiu queda pendent.
- Monetització: pendent. El codi (client i backend) serà obert; el que es cobraria, si es fa, és l'operació dels servidors.

### 3.6 Infraestructura

- **GitHub** per al codi, issues i releases.
- **GitHub Actions** per a builds automàtiques i reproduïbles de la ISO.
- **Repositori APT propi i signat** (`aptly` o `reprepro`).
- **Claus de signatura:** fora de GitHub, protegides amb contrasenya i amb còpia de seguretat, en poques mans. Idealment YubiKey quan hi hagi pressupost.
- Web amb domini propi per a presentació, descàrregues, documentació i reports de vulnerabilitats.

## 4. Equip i recursos

- 4 persones, estudiants d'ASIX: 2 de sistemes i 2 de VPN.
- Dedicació en estones lliures, pressupost nul, treball sense cobrar com a start-up.
- Nivell de Linux encara en construcció (un membre amb més experiència en Debian, Kali, Fedora, Omarchy i Arch).
- El cicle no exigeix cap entrega: no hi ha data límit externa.
- Ambició: start-up real on dedicar-s'hi professionalment en el futur.
- Acord d'equip creat i signat (cobreix rols, dedicació i sortida de membres).

## 5. Full de ruta proposat

> Proposta confirmada per l'equip: s'accepta aquest ordre.

1. **Prova de concepte (sense ISO).** Debian 13 amb Plasma instal·lat a mà, més el meta-paquet `privux` (hardening) i l'eina de terminal. *Responsables: equip de sistemes.*
2. **Client VPN.** App WireGuard contra el servidor de proves, independent del sistema; després s'empaqueta en `.deb`. *Responsables: equip de VPN.*
3. **Panell de configuració.** Integració dels apartats VPN, xarxa, actualitzacions i antivirus.
4. **ISO amb Calamares.** Builds a GitHub Actions i repositori APT signat.
5. **Meta-paquets de pentest, web i llançament públic.**

Cada fase ha de funcionar per si sola, per mantenir la motivació amb resultats visibles aviat.

## 6. Riscos detectats

| Risc | Detall | Mitigació |
|---|---|---|
| **Manteniment a llarg termini** | Les distros noves moren més per manca de manteniment que per manca d'idees | Debian estable, capa fina de paquets propis, automatitzar proves |
| **Motivació desigual** | Dos membres més implicats que els altres | Resultats visibles aviat, repartiment clar de tasques, acord d'equip ja signat |
| **Servei VPN comercial sense pressupost** | Servidors 24/7, abusos, requeriments legals, cobrament sense lligar identitat, auditoria de no-logs | Client des del primer dia, servei propi en fase posterior, servidor antic només per a proves |
| **Sense mode live** | L'usuari no pot comprovar drivers, Wi-Fi o trackpad abans d'instal·lar; en VM no es poden provar mode monitor ni drivers | Documentar maquinari provat; afegir mode live més endavant és barat |
| **NVIDIA amb drivers oberts** | Rendiment inferior, sobretot en portàtils amb gràfica híbrida | Dir-ho a la web com a limitació coneguda |
| **Mida de la ISO** | Una ISO amb Plasma i Calamares pot passar dels 2 GB (límit per fitxer a GitHub Releases) | Reduir la ISO o allotjar-la fora (SourceForge, torrent, bucket) |
| **Barreja amb Kali** | Els repositoris de Kali no es poden afegir a Debian estable | Empaquetar eines pròpies o usar pipx, Go o contenidors |
| **Falsa sensació de seguretat** | Sense VPN, l'operador veu les connexions | Model d'amenaça públic i honest |
| **Robatori de claus de signatura** | Permetria publicar actualitzacions falses | Guardar-les fora de GitHub, còpia de seguretat, YubiKey més endavant |
| **Instantànies ≠ còpia de seguretat** | Btrfs/Snapper viuen al mateix disc | Dir-ho a la documentació; eina de còpies a disc extern més endavant |
| **Reinicis per actualitzacions** | Kernel o microcodi demanen reiniciar | El panell avisa de manera discreta, sense forçar |
| **Element i metadades** | Element (Matrix) xifra el contingut, però el servidor veu metadades; el servidor per defecte és un tercer | Documentar-ho; valorar un servidor Matrix propi a llarg termini |
| **Quad9 filtra dominis maliciosos** | Protegeix, però és un filtre | Documentar-ho; canviable des del panell |

## 7. Decisions pendents

- **Verificar nom i marca:** confirmar que "Privux" i "Orimpo" no estan agafats ni són massa propers a una marca existent (registre de marques de l'UE, domini, repositoris, cerca web). Heu decidit mantenir-los; queda pendent la comprovació.
- **Llicència concreta:** proposta GPLv3 per a la distro i possiblement AGPLv3 per al backend del VPN.
- **Monetització del VPN:** de pagament, parcial o gratuït.
- **Allotjament definitiu del servei VPN** i, més endavant, auditoria externa del no-logs.
- **Distribució de la ISO:** només GitHub, o mirrors i torrent segons la mida final.
- **Maquinari Wi-Fi garantit** per al bloc de pentest (llista d'adaptadors provats).
- **Marca de l'antivirus:** producte visible amb nom propi o peça integrada.
- **Navegador:** confirmar Firefox ESR endurit com a únic per defecte, i com s'ofereix Tor Browser (`torbrowser-launcher`).
- **Perfils futurs** (Estàndard, Paranoia) i la fase de la icona de safata.
- **Model de negoci d'Orimpo:** detall de l'oferta de suport i serveis per a empreses.

## 8. Propers passos immediats

1. Instal·lar Debian 13 amb Plasma en una màquina de proves (idealment maquinari real, no VM).
2. Crear el repositori a GitHub amb estructura inicial (`privux` meta-paquet, eina de terminal, docs).
3. Definir la llista d'opcions de hardening (cada una amb valor per defecte) i implementar-les amb `privux`.
4. En paral·lel, l'equip de VPN comença el client WireGuard contra el servidor de proves.
5. Redactar el model d'amenaça públic (1-2 pàgines).
6. Verificar nom, marca i domini.
