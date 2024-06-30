# this app has three func: (1)switch (2)flow stat; (3) topo discovery

from __future__ import division
from operator import attrgetter  # in order to use sorted()
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER,DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib import hub
from ryu.topology import event
from ryu.topology import switches
import time
import basefun
from mspgtopo import *
import scapy.all as capy
import random
from multiprocessing import Process,Event
from get_cpu_mem import *
class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS={'switches':switches.Switches,}
    
    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.mac_to_time = {}
        self.nodes={}
        self.links={}
        self.monitor_thread = hub.spawn(self._monitor)  
        self.mspgtest_thread = hub.spawn(self._mspgtest)  
    

    # (1)switch function ;
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        
        # add a flow for table missing, it can match all the frame
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        '''
        # add a flow for flood frame, so as to avoid packet in 
        match = parser.OFPMatch(eth_dst='ff:ff:ff:ff:ff:ff')
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 2, match, actions)        
        '''
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, idle_timeout=60,buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            # if priority is 1, we set its idle timeout 60
            if priority==1:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                   match=match, instructions=inst,idle_timeout=60)            
            else:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)    
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        #self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port
        # multi-table search
        start=dpid 
        enddpid,out_port=self.multitablesearch(datapath,dst)
        end=enddpid
        if start!=end:
            # gen a tree for the network topo
            t1=basefun.Tree()
            treenodelist=t1.gentreenodelist(self.nodes, self.links)
            # find tree's root and recurse
            if len(treenodelist)>0:
                root=treenodelist[0]
                t1.rootfirstrecurse(root)
            # gen path for start and end 
            for item in t1.traverse:
                if item.dpid==start:
                    startdp=item
                if item.dpid==end:
                    enddp=item
            if len(t1.traverse)>=6:
                path=t1.genpath(startdp, enddp)
                print('[***]',startdp.dpid,enddp.dpid,path)
        else:
            #print '[*]No need to gen a path! '
            pass
        actions = [parser.OFPActionOutput(out_port)]
        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                try:
                    self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                    print('[*] New flow is added to %d'%end)
                except:
                    print('[*]Flow add error,',start,dst,end)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)    
    
    def multitablesearch(self,datapath,dstmac):
        # we use this fun to search dstmac in multi dpid, it return (dpid,port)
        # if dstmac is a broadcast, like ff:ff:ff.....or 33:33:33..., it must be a broadcast
        if dstmac[0:2]=='33' or dstmac[0:2]=='ff':
            # flood frame
            return datapath.id,datapath.ofproto.OFPP_FLOOD
        print('Packet in happened, dstman is %s'%dstmac)
        #print '[*]mactoport ',self.mac_to_port
        
        # single search, if dstmac in ovs itself's mac table, then forward it
        if dstmac in self.mac_to_port[datapath.id]:
            out_port = self.mac_to_port[datapath.id][dstmac]     
            return  datapath.id,out_port
        
        # use a list to store all the (dpid, port) for dstmac
        print('Multi-table searching... ',dstmac)
        forwardlist=[]
        for dpid in self.mac_to_port:
            if dstmac in self.mac_to_port[dpid]:
                forwardlist.append((dpid,dstmac,self.mac_to_port[dpid][dstmac]))
        print('[*] Forwardlist is ',forwardlist)
          
        # now we get a forwardlist, we need to find a dpid that nearest to the dstmac
        maxduration=0
        nearest=None
        for item in forwardlist:
            for key in self.mac_to_time:
                if item ==key:
                    dtime=self.mac_to_time[key]
                    if dtime>maxduration:
                        nearest=key # the format of key is (dpid,mac,port)
                        maxduration=dtime
        #print '[*] mac to time: ',self.mac_to_time  
    
        if maxduration>0: # it means we find an dpid that contain the dstmac
            dpid=nearest[0]
            port=[2]
            print('==multi table rusult is ', dstmac ,dpid, port)
            return dpid,port
        else: # dstmac is fully missing, no dp contain it
            return datapath.id,datapath.ofproto.OFPP_FLOOD    
    
    # (2) flow stats function;
    # record ovs get in and leave
    @set_ev_cls(ofp_event.EventOFPStateChange,
             [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id] 
                keys=self.mac_to_time.keys()
                for key in keys:
                    if datapath.id in key:
                        del self.mac_to_time[key]
            
    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            # we define a new fun to gen random path and add flow
            print('[Query] totally %d ovses'%len(self.datapaths.values()))
            print(len(self.nodes),len(self.links))
            hub.sleep(10)
    def _mspgtest(self):
        # this fun is used to simulate mac missing 
        print('[*]MSPG test start!')
        hub.sleep(15) # wait for nodes and links
        t1=basefun.Tree()
        if len(self.nodes)!=0 and len(self.links)!=0:
            treenodelist=t1.gentreenodelist(self.nodes, self.links)
            # find tree's root and recurse
            while True:
                if len(treenodelist)>0:
                    root=treenodelist[0]
                    t1.rootfirstrecurse(root)
                # gen path for start and end 
                startdp=random.sample(t1.traverse,1)[0]
                enddp=random.sample(t1.traverse,1)[0]
                if len(t1.traverse)>=2:
                    path=t1.genpath(startdp, enddp)
                    print('[***]Path is: ',startdp.dpid,enddp.dpid,path)
                self.addrandflow(path)
                hub.sleep(1) 
    def _request_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
   
    def addrandflow(self,path):
        # add flows to the path, path is a list
        for dpid in path:
            datapath=self.datapaths[dpid]
            ofproto=datapath.ofproto
            parser=datapath.ofproto_parser
            randmac=basefun.genrandmac(num=1)
            
            match = parser.OFPMatch(eth_dst=randmac)
            
            actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                                  ofproto.OFPCML_NO_BUFFER)]            
            
            self.add_flow(datapath=datapath, priority=1, match=match, actions=actions)
            
   
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info('dpid|'
                     '     eth-dst    |out_port| '
                     'duration')
        self.logger.info(' --- '
                     ' ------------------ '
                     '  --------  '
                     '-------- ')
        dpid=ev.msg.datapath.id
        # we del all the item releated to the dpid, then update 
        dellist=[]
        for key in self.mac_to_time:
            if dpid == key[0]:
                dellist.append(key)
        for key in dellist:
            del self.mac_to_time[key]
        
        for stat in sorted([flow for flow in body if flow.priority == 1],
                       key=lambda flow: (flow.match['eth_dst'])):
            dpid=ev.msg.datapath.id
            dstmac=stat.match['eth_dst']
            outport=stat.instructions[0].actions[0].port
            duration=stat.duration_sec+stat.duration_nsec/10**9
            self.logger.info('%d %s %d  %f',dpid,dstmac,outport,duration)  
            # update datastruct {(dpid,mac,port):duration} 
            self.mac_to_time[(dpid,dstmac,outport)]=duration
        print '++++++++++++++++++++++++++++++++++++++++++++++++++'
        #print self.mac_to_time
       
    
    # (3)topo discovery function;
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        #LOG.debug(ev)
        # this fun is used to get the ovs's dpid and total ports
        # and we store them to a dic {dpid: ports}
        dpid=ev.switch.dp.id
        print('[*]OVS %d get in'%dpid)
        ports=len(ev.switch.ports)
        # update dic
        self.nodes[dpid]=ports
    
    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        dpid=ev.switch.dp.id
        print('OVS %d is leaving'%dpid )
        
        # update dic
        del self.nodes[dpid]
        
        # remove related link in links
        list1=[]
        for item in self.links.items():
            if dpid in item[0] or dpid in item[1]:
                list1.append(item[0])
        for key in list1:
            del self.links[key]
    
    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        #LOG.debug(ev)
        # the ev.link.src is an instance of switches.Port
        srcdpid=ev.link.src.dpid
        srcport=ev.link.src.port_no
        dstdpid=ev.link.dst.dpid
        dstport=ev.link.dst.port_no  
        start=(srcdpid,srcport)
        end=(dstdpid,dstport)
        #if not self.links.has_key(start) and not self.links.has_key(end):
        self.links[start]=end
        #print self.links    
        
        
    
    
    