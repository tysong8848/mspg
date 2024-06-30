import scapy.all as capy
import mspgbasefun
from multiprocessing import Process,Event
import os,time
TIMES=10
Flag=False
Count=0
def rec(pkt,time,f):
    if pkt.haslayer(capy.Padding):
	pad=pkt[capy.Padding]
	
	old_dstmac=pad.load[0:17]
	print(type(old_dstmac),old_dstmac)
	f.write(str(old_dstmac))
	f.write(str(time)+'\n')

def sniffandrec(result='timetest.txt',event=None):
    time.sleep(1)
    
    f2=open(os.getcwd()+'/'+'randsrcmac','w')
    capy.sniff(filter="ether src 00:00:00:00:00:aa and icmp",
               prn=lambda x:rec(x,time.time(),f2),count=TIMES)
    f2.close()
    print('[*]File is closed',event.is_set())
    return 0    

if __name__=='__main__': 
    e=Event()
    p_record=Process(target=sniffandrec,args=('timetest.txt',e,))
    p_record.start()   	
    f1=open(os.getcwd()+'/'+'randdstmac','w')
    
    for i in range(0,TIMES):  	
	dstmac=mspgbasefun.genrandmac()
	f1.write(dstmac)
	f1.write(str(time.time())+'\n')
        msg=mspgbasefun.buildrandicmp(dstip='10.0.0.2',dstmac=dstmac)
        capy.sendp(msg,1)
	print('[*]Sending %d msg!'%i)
    f1.close()
    print('[*]Finishing, total send %d msg!'%TIMES)
    time.sleep(3)
    e.set()
    
