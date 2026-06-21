/caps-man security
add name=sec-fubar authentication-types=wpa2-psk encryption=aes-ccm
add name=sec-guest authentication-types=wpa2-psk encryption=aes-ccm
/caps-man datapath
add name=dp-fubar local-forwarding=yes vlan-mode=use-tag vlan-id=20
add name=dp-guest local-forwarding=yes vlan-mode=use-tag vlan-id=50
/caps-man channel
add name=ch-2g band=2ghz-b/g/n frequency=2412,2437,2462
add name=ch-5g band=5ghz-a/n/ac frequency=5180,5220,5240
/caps-man configuration
add name=cfg-fubar-2g ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-2g
add name=cfg-fubar-5g ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-5g
add name=cfg-guest ssid=Chinazes country=ukraine security=sec-guest datapath=dp-guest
/caps-man manager set enabled=yes
