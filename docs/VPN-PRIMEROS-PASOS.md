# Privux VPN: primera versión de pruebas

Cliente WireGuard de Orimpo para Debian 13 y KDE Plasma 6. La instalación no
conecta ni habilita el kill switch. Todavía no existe un servicio público de
Orimpo: cada servidor se configura expresamente. No es una auditoría de seguridad
ni una afirmación de que el servicio no guarda registros.

## Qué incluye

- Aplicación Qt 6 con selección de perfiles, conectar/desconectar, importar
  `.conf`, kill switch y estado real de interfaz/último handshake.
- Entrada en Configuración del sistema → Red que abre la aplicación propia
  mediante el mecanismo de módulos externos de Plasma. No es un KCM embebido.
- Backend privilegiado reducido, autenticación Polkit, rutas fijas y archivos
  privados con permisos 0600. La interfaz gráfica nunca se ejecuta como root.
- Comandos `privux vpn status`, `connect NOMBRE`, `disconnect`,
  `kill-switch on|off`, `import NOMBRE` (configuración por entrada estándar).
  También `privux-vpnctl` con las mismas órdenes, compatible con la CLI antigua
  de una ISO anterior cuando se utiliza el instalador directo.
- Paquete Debian `privux-vpn`, integración en el preparador de ISO y servidor
  de pruebas de un cliente. La licencia sigue la decisión provisional GPL-3+
  del repositorio; confirmar la licencia definitiva antes de publicar un servicio.

## Instalar en tu Privux actual

Desde la carpeta del código:

```sh
sudo sh scripts/install-vpn-client.sh
privux-vpn
```

El instalador directo añade exclusivamente los módulos VPN a la instalación
existente; no ejecuta `privux apply` ni cambia el cortafuegos de entrada.
En una sesión live, estos cambios desaparecen al reiniciar si no hay persistencia.

Si tienes los paquetes construidos, instala solo el CLI y el cliente VPN:

```sh
sudo apt install ./privux-cli_0.2.0_all.deb ./privux-vpn_0.2.0_all.deb
```

El paquete CLI conserva su mecanismo existente de aplicación del perfil de
privacidad. No instales el meta-paquete de escritorio para añadir solo la VPN.

## Servidor sin comprar hardware

Prepara una segunda VM **dedicada**, con Debian 13, 1–2 GB de RAM y dos tarjetas:
tarjeta 1 NAT para descargar paquetes y salir a Internet; tarjeta 2 red interna
`orimpo-lab`, compartida con una segunda tarjeta de la VM Privux.

En el servidor asigna `192.168.77.1/24` a la tarjeta interna y en Privux
`192.168.77.2/24`, sin puerta de enlace ni DNS en esas tarjetas. Comprueba los
nombres reales con `ip -br address`; no supongas que se llaman `enp0s8`.
La ruta predeterminada de ambas VMs sigue siendo la tarjeta NAT.

En el Debian dedicado, desde el código del proyecto:

```sh
sudo bash scripts/setup-vpn-server.sh 192.168.77.1
sudo wg show orimpo0
```

Genera un perfil único en `/root/privux-lab.conf`. Transfiérelo a Privux mediante
un medio local seguro y abre **Importar .conf**. Es un secreto: contiene la clave
privada del cliente. No lo subas a GitHub, chats, capturas ni carpetas públicas.
Solo importa el perfil en un dispositivo; cada dispositivo necesita claves propias.

No ejecutes el preparador de servidor en tu escritorio ni en un servidor con
contenedores u otros servicios: su política de reenvío está diseñada para una VM
dedicada. Si añades un cortafuegos de entrada, autoriza UDP 51820. Si usas Privux
como servidor en vez de Debian, su cortafuegos de entrada necesita también una
regla explícita para ese puerto; una regla de otra tabla no anula un DROP previo.

Este laboratorio ofrece salida **IPv4**. El cliente envía IPv6 al túnel para
evitar escapes, pero el servidor de pruebas no proporciona salida IPv6.
Para un servidor remoto posterior necesitarás una IP alcanzable, UDP 51820
permitido y, si procede, reenvío en el router. El alojamiento definitivo está pendiente.

## Perfiles externos admitidos

```ini
[Interface]
PrivateKey = CLAVE_PRIVADA_CLIENTE_BASE64
Address = 10.77.0.2/32
DNS = 9.9.9.9
MTU = 1380

[Peer]
PublicKey = CLAVE_PUBLICA_SERVIDOR_BASE64
PresharedKey = CLAVE_COMPARTIDA_OPCIONAL_BASE64
Endpoint = 192.168.77.1:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
```

Es una plantilla explicativa, no un perfil utilizable. Debes generar las claves.
La versión inicial admite un Peer, IP numérica en Endpoint, DNS numérico y
túnel completo IPv4/IPv6. Rechaza hooks `PreUp/PostUp/PreDown/PostDown`,
`SaveConfig`, rutas personalizadas, dominios en Endpoint y túneles divididos.
Esas restricciones impiden ejecutar órdenes importadas como administrador.
No cambies simplemente un dominio por una IP sin comprobarla con tu proveedor.

## Comprobar que funciona

1. Importar perfil, activar kill switch y conectar. Generar tráfico
   (`ping -c 3 10.77.0.1` en este laboratorio) y actualizar estado: debe haber
   respuesta reciente del servidor. Interfaz activa no equivale a conexión verificada.
2. Abrir una web y comprobar la salida por el servidor. En dos VMs con NAT en el
   mismo ordenador, la IP pública puede coincidir antes y después: no basta como prueba.
   Confirma handshake y contadores con `sudo wg show pvpn` en el cliente y
   `sudo wg show orimpo0` en el servidor.
3. Revisar DNS con `resolvectl status pvpn`: DNS del perfil y dominio `~.`.
   El DNS sale dentro del túnel; esta versión no usa DoT adicional en el enlace VPN.
4. Apagar el servidor: con kill switch activo no debe funcionar la salida directa,
   incluyendo IPv6 ni consultas DNS fuera del túnel.
5. Desconectar: Internet sigue bloqueado hasta desactivar el kill switch.
6. Reiniciar el cliente con kill switch activo: debe continuar bloqueado, sin
   reconexión automática. Validar este caso en la VM real antes de distribución pública.

## Recuperar Internet

En la aplicación desactiva Kill switch, o ejecuta desde la consola local:

```sh
sudo /usr/lib/privux/vpn-helper disconnect
sudo /usr/lib/privux/vpn-helper kill-switch off
```

Estas órdenes solo gestionan la VPN y su tabla `inet privux_vpn`. No vacíes el
cortafuegos completo. Activar el kill switch bloquea también las conexiones LAN,
máquinas virtuales/contenedores reenviados y sesiones remotas fuera del túnel.
Haz la primera prueba desde la consola local de Privux.

## Alcance y límites de la comprobación

Las pruebas de red crean dos espacios de red Linux aislados, generan claves
efímeras y prueban WireGuard real, nftables, handshake, tráfico cifrado, bloqueo
IPv4/IPv6, caída de interfaz, restauración del bloqueo y recuperación explícita.
El componente resolved se simula en ese laboratorio porque no tiene su propio
servicio systemd. Las pruebas gráficas crean la ventana Qt real sin pantalla.

Pendiente de validar en tu VM: integración visible de Plasma, autenticación
Polkit, resolución DNS real, salida web y orden de arranque tras reinicio.
Un administrador que vacía las reglas de nftables puede retirar la protección;
el cliente detecta la ausencia de tabla al actualizar estado, pero no impide cambios
privilegiados ni protege otras interfaces WireGuard creadas fuera de esta aplicación.

## Desarrollo

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
sudo python3 scripts/vpn-netns-test.py
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 scripts/vpn-gui-smoke.py
dpkg-buildpackage -us -uc -b
```

Usa la prueba de red en una máquina de desarrollo desechable, nunca en producción.
Los trabajos existentes construyen los `.deb`; `VPN validation` añade pruebas de
red y de escritorio. La ISO incorpora el cliente cuando se vuelve a compilar;
editar el preparador no actualiza una ISO ya descargada.

Fuentes: [especificación de Privux](https://github.com/Orimpo-Linux/privux/blob/main/docs/Privux-resum-del-projecte.md),
[WireGuard oficial](https://www.wireguard.com/quickstart/),
[módulos externos de Plasma](https://github.com/KDE/systemsettings/blob/master/app/kcmmetadatahelpers.h).
