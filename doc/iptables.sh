iptables -t nat -A PREROUTING -i br-lan -p udp --dport 53 -j DNAT --to $(uci get network.lan.ipaddr):53
iptables -t nat -A PREROUTING -i br-lan -p tcp --dport 53 -j DNAT --to $(uci get network.lan.ipaddr):53



 以下规则是屏蔽以 youtube.com 为主的所有一级 二级 三级等域名。

iptables -A OUTPUT -m string --string "youtube.com" --algo bm --to 65535 -j DROP
 # 添加屏蔽规则

iptables -D OUTPUT -m string --string "youtube.com" --algo bm --to 65535 -j DROP
 # 删除屏蔽规则，上面添加的代码是什么样，那么删除的代码就是把 -A 改成 -D
