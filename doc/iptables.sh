iptables -t nat -A PREROUTING -i br-lan -p udp --dport 53 -j DNAT --to $(uci get network.lan.ipaddr):53
iptables -t nat -A PREROUTING -i br-lan -p tcp --dport 53 -j DNAT --to $(uci get network.lan.ipaddr):53
