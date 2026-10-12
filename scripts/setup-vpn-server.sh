#!/bin/bash
# Dedicated Debian 13 test server only. Creates one client, never prints keys.
set -euo pipefail
umask 077
if [[ $EUID != 0 || $# != 1 ]]; then
    echo 'Usage: sudo bash scripts/setup-vpn-server.sh SERVER_IPV4' >&2
    exit 2
fi
SERVER_IP=$(python3 -c 'import ipaddress,sys; print(ipaddress.IPv4Address(sys.argv[1]))' "$1")
if [[ -e /etc/wireguard/orimpo0.conf || -e /etc/nftables.d/orimpo-vpn.nft || -e /root/privux-lab.conf ]]; then
    echo 'Existing Orimpo server/profile found; refusing to overwrite.' >&2
    exit 1
fi
apt-get update
apt-get install -y wireguard-tools nftables iproute2 python3 procps
UPLINK=$(ip -4 route show default | awk 'NR==1 {print $5}')
[[ $UPLINK =~ ^[a-zA-Z0-9_.:-]+$ ]] || { echo 'Cannot detect uplink' >&2; exit 1; }
install -d -m 700 /etc/wireguard
install -d /etc/nftables.d /etc/sysctl.d
SERVER_KEY=$(wg genkey)
SERVER_PUBLIC=$(printf '%s' "$SERVER_KEY" | wg pubkey)
CLIENT_KEY=$(wg genkey)
CLIENT_PUBLIC=$(printf '%s' "$CLIENT_KEY" | wg pubkey)
PSK=$(wg genpsk)
cat > /etc/wireguard/orimpo0.conf <<EOF
[Interface]
Address = 10.77.0.1/24
ListenPort = 51820
PrivateKey = $SERVER_KEY

[Peer]
PublicKey = $CLIENT_PUBLIC
PresharedKey = $PSK
AllowedIPs = 10.77.0.2/32
EOF
cat > /root/privux-lab.conf <<EOF
[Interface]
PrivateKey = $CLIENT_KEY
Address = 10.77.0.2/32
DNS = 9.9.9.9
MTU = 1380

[Peer]
PublicKey = $SERVER_PUBLIC
PresharedKey = $PSK
Endpoint = $SERVER_IP:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF
unset SERVER_KEY CLIENT_KEY PSK
cat > /etc/nftables.d/orimpo-vpn.nft <<EOF
table ip orimpo_vpn
delete table ip orimpo_vpn
table ip orimpo_vpn {
    chain forward {
        type filter hook forward priority filter; policy drop;
        iifname "orimpo0" oifname "$UPLINK" ip saddr 10.77.0.2 accept
        iifname "$UPLINK" oifname "orimpo0" ip daddr 10.77.0.2 ct state established,related accept
    }
    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        ip saddr 10.77.0.2 oifname "$UPLINK" masquerade
    }
}
EOF
cat > /etc/systemd/system/orimpo-vpn-firewall.service <<'EOF'
[Unit]
Description=Orimpo test VPN forwarding rules
After=nftables.service
Before=wg-quick@orimpo0.service
[Service]
Type=oneshot
ExecStart=/usr/sbin/nft -f /etc/nftables.d/orimpo-vpn.nft
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
install -d /etc/systemd/system/wg-quick@orimpo0.service.d
cat > /etc/systemd/system/wg-quick@orimpo0.service.d/firewall.conf <<'EOF'
[Unit]
Requires=orimpo-vpn-firewall.service
After=orimpo-vpn-firewall.service
EOF
printf '%s\n' 'net.ipv4.ip_forward=1' > /etc/sysctl.d/80-orimpo-vpn.conf
sysctl -p /etc/sysctl.d/80-orimpo-vpn.conf
systemctl daemon-reload
systemctl enable --now orimpo-vpn-firewall.service wg-quick@orimpo0.service
echo 'Server ready. Client profile: /root/privux-lab.conf (private; transfer securely).'
echo 'Allow inbound UDP 51820 in any additional firewall. IPv6 Internet is blocked in this lab.'
