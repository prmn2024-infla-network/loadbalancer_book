import os
import time
from ipmininet.iptopo import IPTopo
from ipmininet.ipnet import IPNet
from ipmininet.cli import IPCLI
from ipmininet.router.config import BGP

class GSLBHubSpokeTopo(IPTopo):
    def build(self, *args, **kwargs):
        # ルータ定義 
        r1 = self.addRouter("r1")
        r2 = self.addRouter("r2")
        bg_jp = self.addRouter("bg_jp")
        bg_us = self.addRouter("bg_us")
        global1 = self.addRouter("global1")
        global2 = self.addRouter("global2")

        # ホスト定義
        client1 = self.addHost("client1", ip="192.168.1.10/24", defaultRoute="via 192.168.1.1")
        client2 = self.addHost("client2", ip="192.168.2.10/24", defaultRoute="via 192.168.2.1")
        gslb_dns = self.addHost("gslb_dns", ip="192.168.1.100/24", defaultRoute="via 192.168.1.1")
        server1 = self.addHost("server1", ip="10.0.1.10/24", defaultRoute="via 10.0.1.1")
        server2 = self.addHost("server2", ip="10.0.2.10/24", defaultRoute="via 10.0.2.1")

        # AS割り当て
        self.addAS(200, (bg_jp, r1))       # AS200: 日本サイト
        self.addAS(201, (bg_us, r2))       # AS201: 米国サイト
        self.addAS(100, (global1, global2)) # AS100: グローバル/サーバサイト

        # リンク定義 
        # サイト内LANの構築
        s1 = self.addSwitch("s1")
        self.addLink(r1, s1, params1={"ip": "192.168.1.1/24"})
        self.addLink(client1, s1)
        self.addLink(gslb_dns, s1)
        self.addLink(client2, r2, params2={"ip": "192.168.2.1/24"})

        # Webサーバの接続
        self.addLink(server1, global1, params2={"ip": "10.0.1.1/24"})
        self.addLink(server2, global2, params2={"ip": "10.0.2.1/24"})

        # ルータ間接続 (iBGPおよびeBGP)
        self.addLink(r1, bg_jp, subnet="172.16.10.0/24")
        self.addLink(r2, bg_us, subnet="172.16.11.0/24")
        self.addLink(global1, global2, subnet="10.1.0.0/24")
        self.addLink(bg_jp, bg_us, subnet="172.16.200.0/24")
        self.addLink(bg_jp, global1, subnet="10.100.1.0/24")
        self.addLink(bg_us, global2, subnet="10.100.2.0/24")

        # BGPデーモン設定
        for r_name in ("r1", "r2", "bg_jp", "bg_us", "global1", "global2"):
            self.addDaemon(r_name, BGP)

        super().build(*args, **kwargs)

def setup_environment(net):
    print("[INFO] Setting up GSLB environment...")
    routers = ["r1", "r2", "bg_jp", "bg_us", "global1", "global2"]
    for r_name in routers:
        node = net.get(r_name)
        node.cmd("sleep 1")
        node.cmd(f"cp frr_gslb_configs/{r_name}.conf /etc/frr/frr.conf")
        node.cmd("chown frr:frr /etc/frr/frr.conf")
        node.cmd("/etc/init.d/frr restart", shell=True)

    print("[INFO] Waiting for BGP to converge..."); time.sleep(15)
    # Webサーバーの起動と確認 
    print("[INFO] Starting web servers...")
    for s_name in ("server1", "server2"):
        server = net.get(s_name)
        server_ip = server.IP()
        server.cmd(f"echo 'Hello from {s_name} ({server_ip})' > index.html")
        server.cmd(f"python3 -m http.server 80 --bind {server_ip} &")

    print("[INFO] Waiting for web servers to start..."); time.sleep(3)

    # 疎通確認（HTTP）
    print("[INFO] Performing HTTP connectivity checks...")
    gslb_dns = net.get("gslb_dns")
    if gslb_dns.cmd(f"curl --connect-timeout 2 http://10.0.1.10") and gslb_dns.cmd(f"curl --connect-timeout 2 http://10.0.2.10"):
        print("[SUCCESS] HTTP connectivity from gslb_dns to web servers is OK.")
    else:
        print("[FATAL] HTTP connectivity check failed. gslb_dns cannot reach web servers via HTTP.")
        print("--- Curl to server1 (10.0.1.10) ---")
        print(gslb_dns.cmd(f"curl -v http://10.0.1.10"))
        print("\n--- Netstat on server1 ---")
        print(net.get("server1").cmd("netstat -tulpn"))
        return False

    # BIND9のセットアップ
    print("[INFO] Installing BIND9, Python3 and utilities on DNS server...")
    gslb_dns.cmd("DEBIAN_FRONTEND=noninteractive apt-get -qq update && apt-get -qq install -y python3 bind9 bind9utils iptables curl > /dev/null")
    gslb_dns.cmd("pkill -9 -f named || true"); gslb_dns.cmd("sleep 1")
    gslb_dns.cmd("iptables -I INPUT 1 -p udp --dport 53 -j ACCEPT")
    gslb_dns.cmd("iptables -I INPUT 1 -p tcp --dport 53 -j ACCEPT")
    
    print("[INFO] Preparing all BIND9 configuration files...")
    gslb_dns.cmd("echo 'include \"/etc/bind/named.conf.options\";' > /etc/bind/named.conf")
    gslb_dns.cmd("echo 'include \"/etc/bind/named.conf.local\";' >> /etc/bind/named.conf")
    gslb_dns.cmd("echo 'include \"/etc/bind/rndc.key\";' >> /etc/bind/named.conf")
    gslb_dns.cmd("cp dns_configs/named.conf.options /etc/bind/named.conf.options")
    gslb_dns.cmd("cp dns_configs/named.conf.local /etc/bind/named.conf.local")
    gslb_dns.cmd("cp dns_configs/rndc.key /etc/bind/rndc.key")
    gslb_dns.cmd("cp dns_configs/db.service.example.jp /etc/bind/db.service.example.jp")
    gslb_dns.cmd("cp dns_configs/db.service.example.us /etc/bind/db.service.example.us")
    gslb_dns.cmd("cp dns_configs/db.service.example.jp.template /etc/bind/db.service.example.jp.template")
    gslb_dns.cmd("cp dns_configs/db.service.example.us.template /etc/bind/db.service.example.us.template")
    gslb_dns.cmd("cp /usr/share/dns/root.hints /etc/bind/db.root")
    gslb_dns.cmd("cp /etc/bind/db.local /etc/bind/db.local", check=False)
    gslb_dns.cmd("cp /etc/bind/db.127 /etc/bind/db.127", check=False)
    gslb_dns.cmd("chown -R bind:bind /etc/bind")
    gslb_dns.cmd("chmod 755 /etc/bind")
    gslb_dns.cmd("chmod 644 /etc/bind/*")
    
    print("[INFO] Starting BIND9 daemon directly")
    gslb_dns.cmd("named -c /etc/bind/named.conf -u bind &"); gslb_dns.cmd("sleep 3")
    if not gslb_dns.cmd("ps aux | grep '[n]amed'"):
        print("[FATAL] BIND9 failed to start.")
        print(gslb_dns.cmd("tail -n 20 /var/log/syslog"))
        return False
        
    print("[SUCCESS] BIND9 is running!")
    
    print("[INFO] Starting health checker...")
    gslb_dns.cmd("cp health_checker.py /root/health_checker.py")
    gslb_dns.cmd("python3 /root/health_checker.py > /var/log/health_checker.log 2>&1 &")

    for c_name in ("client1", "client2"):
        client = net.get(c_name)
        client.cmd(f"echo 'nameserver {gslb_dns.IP()}' > /etc/resolv.conf")
    print("[INFO] Environment setup complete.")
    return True

if __name__ == "__main__":
    os.system("sudo mn -c")
    if not os.path.exists("bind_log"):
        os.makedirs("bind_log")
    net = IPNet(topo=GSLBHubSpokeTopo(), use_v4=True)
    try:
        net.start()
        success = setup_environment(net)
        if success:
            IPCLI(net)
    finally:
        print("[INFO] Stopping network...")
        net.stop()
