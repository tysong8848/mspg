import scapy.all as capy
import random
def genrandmac(num=1):
    # this fun is used to gen a rand mac, the format is 'ff:ff:ff:ff:ff:ff'
    list1=['1','2','3','4','5','6','8','9','a','b','c','d','e','f']
    mac=''
    for i in range(0,12):
        mac=mac+random.sample(list1,1)[0]
    # format the mac
    fmac=mac[0:2]+':'+mac[2:4]+':'+mac[4:6]+':'+mac[6:8]+':'+mac[8:10]+':'+mac[10:12]
    return fmac

def buildrandicmp(dstip='10.0.0.2',dstmac='ff:ff:ff:ff:ff:ff'):
    
    ping=capy.ICMP()
    pad=capy.Padding('1234567890abcdef1234567890')
    ping=ping/pad
    ip=capy.IP()/ping
    ip.src='10.0.0.1'
    ip.dst=dstip
    ether=capy.Ether()/ip
    ether.src='00:00:00:00:00:01'
    ether.dst=dstmac
    return ether

def buildnormalicmp(srcmac='00:00:00:00:00:aa',dstmac='00:00:00:00:00:01',
                    srcip='127.0.0.1',dstip='127.0.0.1',pad=''):
    ping=capy.ICMP()
    ping.type='echo-reply'
    pad=capy.Padding(pad)
    ping=ping/pad
    ip=capy.IP()/ping
    ip.src=srcip
    ip.dst=dstip
    ether=capy.Ether()/ip
    ether.src=srcmac
    ether.dst=dstmac
    return ether

'''
if __name__=='__main__':
    msg=buildrandicmp()
    msg.show()
    print len(msg)
    re=capy.sendp(msg)
'''