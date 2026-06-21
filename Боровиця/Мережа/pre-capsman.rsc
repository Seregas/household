# 2026-06-08 11:58:50 by RouterOS 7.22.1
# software id = Y7AP-1H76
#
# model = L41G-2axD
# serial number = HES09AY188T
/interface bridge
add admin-mac=78:9A:18:19:AF:AD auto-mac=no comment=defconf name=bridge \
    port-cost-mode=short vlan-filtering=yes
/interface wifi
set [ find default-name=wifi1 ] channel.band=2ghz-ax .skip-dfs-channels=\
    10min-cac .width=20/40mhz configuration.country=Ukraine .mode=ap .ssid=\
    Fubar disabled=no security.authentication-types=wpa2-psk,wpa3-psk \
    .connect-priority=0
/interface pppoe-client
add add-default-route=yes disabled=no interface=ether1 name=alden \
    use-peer-dns=yes user=bor_zger7_c2
/interface vlan
add interface=bridge name=vlan10-mgmt vlan-id=10
add interface=bridge name=vlan20-fubar vlan-id=20
add interface=bridge name=vlan50-guest vlan-id=50
/interface list
add comment=defconf name=WAN
add comment=defconf name=LAN
/ip pool
add name=pool-mgmt ranges=10.20.10.100-10.20.10.150
add name=pool-fubar ranges=10.20.20.100-10.20.20.200
add name=pool-guest ranges=10.20.50.100-10.20.50.200
/ip dhcp-server
add address-pool=pool-mgmt interface=vlan10-mgmt lease-time=1d name=dhcp-mgmt
add address-pool=pool-fubar interface=vlan20-fubar lease-time=1d name=\
    dhcp-fubar
add address-pool=pool-guest interface=vlan50-guest lease-time=4h name=\
    dhcp-guest
/zerotier
set zt1 disabled=no disabled=no
/zerotier interface
add allow-default=no allow-global=no allow-managed=yes comment=\
    "Borovytsya Router" disabled=no instance=zt1 name=zt_borovytsya network=\
    632ea29085a92081
/interface bridge port
add bridge=bridge comment=defconf interface=ether2 internal-path-cost=10 \
    path-cost=10
add bridge=bridge comment=defconf interface=ether3 internal-path-cost=10 \
    path-cost=10
add bridge=bridge comment=defconf interface=ether4 internal-path-cost=10 \
    path-cost=10 pvid=20
add bridge=bridge comment=defconf interface=wifi1 internal-path-cost=10 \
    path-cost=10 pvid=20
/ip firewall connection tracking
set udp-timeout=10s
/ip neighbor discovery-settings
set discover-interface-list=LAN
/interface bridge vlan
add bridge=bridge tagged=bridge,ether2,ether3 vlan-ids=10
add bridge=bridge tagged=bridge,ether2,ether3 untagged=ether4,wifi1 vlan-ids=\
    20
add bridge=bridge tagged=bridge,ether2,ether3 vlan-ids=50
/interface list member
add comment=defconf interface=bridge list=LAN
add comment=defconf interface=ether1 list=WAN
add interface=alden list=WAN
add interface=vlan10-mgmt list=LAN
add interface=vlan20-fubar list=LAN
/interface ovpn-server server
add mac-address=FE:32:2B:DF:7F:06 name=ovpn-server1
/ip address
add address=10.20.10.1/24 interface=vlan10-mgmt network=10.20.10.0
add address=10.20.20.1/24 interface=vlan20-fubar network=10.20.20.0
add address=10.20.50.1/24 interface=vlan50-guest network=10.20.50.0
/ip dhcp-client
add comment=defconf interface=ether1 name=client1
/ip dhcp-server network
add address=10.20.10.0/24 dns-server=10.20.10.1 gateway=10.20.10.1
add address=10.20.20.0/24 dns-server=10.20.20.1 gateway=10.20.20.1
add address=10.20.50.0/24 dns-server=10.20.50.1 gateway=10.20.50.1
/ip dns
set allow-remote-requests=yes
/ip firewall filter
add action=accept chain=input comment="SSH via ZT (Mac mini)" dst-port=22 \
    in-interface=zt_borovytsya protocol=tcp src-address=10.242.124.88
add action=accept chain=input comment="SSH via ZT (macbook)" dst-port=22 \
    in-interface=zt_borovytsya protocol=tcp src-address=10.242.88.65
add action=accept chain=input comment=\
    "defconf: accept established,related,untracked" connection-state=\
    established,related,untracked
add action=drop chain=input comment="defconf: drop invalid" connection-state=\
    invalid
add action=accept chain=input comment="defconf: accept ICMP" protocol=icmp
add action=accept chain=input comment=\
    "defconf: accept to local loopback (for CAPsMAN)" dst-address=127.0.0.1
add action=accept chain=input comment="guest dns+dhcp" dst-port=53,67 \
    in-interface=vlan50-guest protocol=udp
add action=accept chain=input dst-port=53 in-interface=vlan50-guest protocol=\
    tcp
add action=drop chain=input comment="defconf: drop all not coming from LAN" \
    in-interface-list=!LAN
add action=accept chain=forward comment="defconf: accept in ipsec policy" \
    ipsec-policy=in,ipsec
add action=accept chain=forward comment="defconf: accept out ipsec policy" \
    ipsec-policy=out,ipsec
add action=fasttrack-connection chain=forward comment="defconf: fasttrack" \
    connection-state=established,related
add action=accept chain=forward comment=\
    "defconf: accept established,related, untracked" connection-state=\
    established,related,untracked
add action=drop chain=forward comment="defconf: drop invalid" \
    connection-state=invalid
add action=drop chain=forward comment="guest only internet" in-interface=\
    vlan50-guest out-interface-list=!WAN
add action=drop chain=forward comment=\
    "defconf: drop all from WAN not DSTNATed" connection-nat-state=!dstnat \
    connection-state=new in-interface-list=WAN
/ip firewall nat
add action=masquerade chain=srcnat comment="defconf: masquerade" \
    ipsec-policy=out,none out-interface-list=WAN
/ip ipsec profile
set [ find default=yes ] dpd-interval=2m dpd-maximum-failures=5
/ipv6 firewall address-list
add address=::/128 comment="defconf: unspecified address" list=bad_ipv6
add address=::1/128 comment="defconf: lo" list=bad_ipv6
add address=fec0::/10 comment="defconf: site-local" list=bad_ipv6
add address=::ffff:0.0.0.0/96 comment="defconf: ipv4-mapped" list=bad_ipv6
add address=::/96 comment="defconf: ipv4 compat" list=bad_ipv6
add address=100::/64 comment="defconf: discard only " list=bad_ipv6
add address=2001:db8::/32 comment="defconf: documentation" list=bad_ipv6
add address=2001:10::/28 comment="defconf: ORCHID" list=bad_ipv6
add address=3ffe::/16 comment="defconf: 6bone" list=bad_ipv6
/ipv6 firewall filter
add action=accept chain=input comment=\
    "defconf: accept established,related,untracked" connection-state=\
    established,related,untracked
add action=drop chain=input comment="defconf: drop invalid" connection-state=\
    invalid
add action=accept chain=input comment="defconf: accept ICMPv6" protocol=\
    icmpv6
add action=accept chain=input comment="defconf: accept UDP traceroute" port=\
    33434-33534 protocol=udp
add action=accept chain=input comment=\
    "defconf: accept DHCPv6-Client prefix delegation." dst-port=546 protocol=\
    udp src-address=fe80::/10
add action=accept chain=input comment="defconf: accept IKE" dst-port=500,4500 \
    protocol=udp
add action=accept chain=input comment="defconf: accept ipsec AH" protocol=\
    ipsec-ah
add action=accept chain=input comment="defconf: accept ipsec ESP" protocol=\
    ipsec-esp
add action=accept chain=input comment=\
    "defconf: accept all that matches ipsec policy" ipsec-policy=in,ipsec
add action=drop chain=input comment=\
    "defconf: drop everything else not coming from LAN" in-interface-list=\
    !LAN
add action=accept chain=forward comment=\
    "defconf: accept established,related,untracked" connection-state=\
    established,related,untracked
add action=drop chain=forward comment="defconf: drop invalid" \
    connection-state=invalid
add action=drop chain=forward comment=\
    "defconf: drop packets with bad src ipv6" src-address-list=bad_ipv6
add action=drop chain=forward comment=\
    "defconf: drop packets with bad dst ipv6" dst-address-list=bad_ipv6
add action=drop chain=forward comment="defconf: rfc4890 drop hop-limit=1" \
    hop-limit=equal:1 protocol=icmpv6
add action=accept chain=forward comment="defconf: accept ICMPv6" protocol=\
    icmpv6
add action=accept chain=forward comment="defconf: accept HIP" protocol=139
add action=accept chain=forward comment="defconf: accept IKE" dst-port=\
    500,4500 protocol=udp
add action=accept chain=forward comment="defconf: accept ipsec AH" protocol=\
    ipsec-ah
add action=accept chain=forward comment="defconf: accept ipsec ESP" protocol=\
    ipsec-esp
add action=accept chain=forward comment=\
    "defconf: accept all that matches ipsec policy" ipsec-policy=in,ipsec
add action=drop chain=forward comment=\
    "defconf: drop everything else not coming from LAN" in-interface-list=\
    !LAN
/system clock
set time-zone-name=Europe/Kyiv
/system identity
set name=MikroTik-Boro
/tool mac-server
set allowed-interface-list=LAN
/tool mac-server mac-winbox
set allowed-interface-list=LAN
