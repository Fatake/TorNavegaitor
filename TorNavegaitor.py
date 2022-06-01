#!/usr/bin/python3
import os
import sys
import getopt
from requests import get
import subprocess
import time
import signal
from stem import Signal
from stem.control import Controller
from packaging import version

IP_API = "https://api.ipify.org/?format=json"

class bcolors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[31m'
    YELLOW = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    BGRED = '\033[41m'
    WHITE = '\033[37m'

# Dissplay Current Time
def t():
    current_time = time.localtime()
    ctime = time.strftime('%H:%M:%S', current_time)
    return '[' + ctime + ']'

def sigint_handler(signum, frame):
    print("User interrupt ! shutting down")
    stop_tor()

def logo():
    print(bcolors.RED + bcolors.BOLD)
    print("""
     _  ____  __   ____   __    _  _  ____ 
    / )( ___)/__\ (_  _) /__\  ( )/ )( ___)
   / /  )__)/(__)\  )(  /(__)\  )  (  )__) 
()(_/  (__)(__)(__)(__)(__)(__)(_)\_)(____)

    """)
    print(bcolors.ENDC)

def usage():
    logo()
    print("""
    usage:
    -s    --start       Start Tor browsing
    -r    --switch      Request new tor exit node
    -x    --stop        Stop service
    -h    --help        print(this help and exit)
    """)
    sys.exit()

def ip():
    while True:
        try:
            jsonRes = get(IP_API).json()
            ipTxt = jsonRes["ip"]
        except:
            continue
        break
    return ipTxt


def check_root():
    if os.geteuid() != 0:
        print("You must be root; Use 'sudo'")
        sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)

TorrcCfgString = \
    """
VirtualAddrNetwork 10.0.0.0/10
AutomapHostsOnResolve 1
TransPort 9040
DNSPort 5353
ControlPort 9051
RunAsDaemon 1
"""

resolvString = 'nameserver 127.0.0.1'

Torrc = '/etc/tor/fatakeTor'
resolv = '/etc/resolv.conf'


def start_torbrowsing():
    os.system('sudo cp /etc/resolv.conf /etc/resolv.conf.bak')
    if os.path.exists(Torrc) and TorrcCfgString in open(Torrc).read():
        print(t() + ' Torrc file already configured')
    else:

        with open(Torrc, 'w') as myfile:
            print(t() + ' Writing torcc file ')
            myfile.write(TorrcCfgString)
            print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    if resolvString in open(resolv).read():
        print(t() + ' DNS resolv.conf file already configured')
    else:
        with open(resolv, 'w') as myfile:
            print(t() + ' Configuring DNS resolv.conf file.. '),
            myfile.write(resolvString)
            print(bcolors.GREEN + '[done]' + bcolors.ENDC)

    print(t() + ' Stopping tor service '),
    os.system('sudo systemctl stop tor')
    os.system('sudo fuser -k 9051/tcp > /dev/null 2>&1')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Starting new tor daemon '),
    os.system('sudo -u debian-tor tor -f /etc/tor/fatakeTor > /dev/null')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' setting up iptables rules'),

    iptables_rules = \
        """
	NON_TOR="192.168.1.0/24 192.168.0.0/24"
	TOR_UID=%s
	TRANS_PORT="9040"

	iptables -F
	iptables -t nat -F

	iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
	iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353
	for NET in $NON_TOR 127.0.0.0/9 127.128.0.0/10; do
	 iptables -t nat -A OUTPUT -d $NET -j RETURN
	done
	iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT

	iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
	for NET in $NON_TOR 127.0.0.0/8; do
	 iptables -A OUTPUT -d $NET -j ACCEPT
	done
	iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
	iptables -A OUTPUT -j REJECT
	""" \
        % subprocess.getoutput('id -ur debian-tor')

    os.system(iptables_rules)
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Fetching current IP...')
    print(t() + ' CURRENT IP : ' + bcolors.GREEN + ip() + bcolors.ENDC)


def stop_tor():
    print(bcolors.RED + t() + 'STOPPING...' + bcolors.ENDC)
    print(t() + ' Flushing iptables, resetting to default'),
    os.system('mv /etc/resolv.conf.bak /etc/resolv.conf')
    IpFlush = \
        """
	iptables -P INPUT ACCEPT
	iptables -P FORWARD ACCEPT
	iptables -P OUTPUT ACCEPT
	iptables -t nat -F
	iptables -t mangle -F
	iptables -F
	iptables -X
	"""
    os.system(IpFlush)
    os.system('sudo fuser -k 9051/tcp > /dev/null 2>&1')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Restarting Network manager'),
    os.system('service network-manager restart')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Fetching current IP...')
    time.sleep(3)
    print(t() + ' CURRENT IP : ' + bcolors.GREEN + ip() + bcolors.ENDC)


def switch_tor():
    print(t() + ' Please wait...')
    time.sleep(7)
    print(t() + ' Requesting new circuit...'),
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Fetching current IP...')
    print(t() + ' CURRENT IP : ' + bcolors.GREEN + ip() + bcolors.ENDC)


def main():
    check_root()
    if len(sys.argv) <= 1:
        usage()
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'srxh', [
            'start', 'stop', 'switch', 'help'])
    except (getopt.GetoptError):
        usage()
        sys.exit(2)
    for (o, a) in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-s', '--start'):
            logo()
            start_torbrowsing()
        elif o in ('-x', '--stop'):
            logo()
            stop_tor()
        elif o in ('-r', '--switch'):
            logo()
            switch_tor()
        else:
            usage()

if __name__ == '__main__':
    main()
