import random
class Node(object):
    
    def __init__(self, dpid=-1, lchild=None, rchild=None):
        self.ancestor=None
        self.dpid = dpid
        self.lchild = lchild
        self.rchild = rchild
    def show(self):
        print(self.dpid,self.lchild,self.rchild,self.ancestor)
class Tree(object):
   
    def __init__(self):
        self.root = Node()
        self.myQueue = []
        self.traverse=[]
        self.path=[]
        self.ancestors=[]
    def add(self, dpid):
        
        node = Node(dpid)
        if self.root.dpid == -1: 
            self.root = node
            self.myQueue.append(self.root)
        else:
            treeNode = self.myQueue[0] 
            if treeNode.lchild == None:
                treeNode.lchild = node
                self.myQueue.append(treeNode.lchild)
            else:
                treeNode.rchild = node
                self.myQueue.append(treeNode.rchild)
                self.myQueue.pop(0) 
    def rootfirstrecurse(self, root):
        if root==None:
            return
        self.traverse.append(root)
        self.rootfirstrecurse(root.lchild)
        self.rootfirstrecurse(root.rchild)
    
    def middle_digui(self, root):
        
        if root == None:
            return
        self.middle_digui(root.lchild)
        print(root.elem,)
        self.middle_digui(root.rchild)
    
    def later_digui(self, root):
        
        if root == None:
            return
        self.later_digui(root.lchild)
        self.later_digui(root.rchild)
        print(root.elem,)
    
    def gentreenodelist(self, nodes={},links={}):
        # the format of nodes is {dpid,totalport}, format of links is {(dpid,port):(dpid:port)}
        # if the link start at port 1, it must be a lchild, port 2 is rchild
        nodelist=[]
        list1=[]
        # create all the tree node store in a list
        for dpid in nodes:
            node=Node(dpid=dpid)
            nodelist.append(node)
        # create root
        for node in nodelist:
            if node.dpid==1:# 1 means root, so just add in queue as the root
                self.myQueue.append(node)
        for i in range(0,len(nodelist)):
            treenode=self.myQueue[0]
            lflag=False
            rflag=False            
            dpid=treenode.dpid
            # find its childs
            for key in links:
                # find is lchild and rchild
                if key[0]==dpid and key[1]==1:
                    lchilddpid=links[key][0]
                    for node in nodelist:
                        if node.dpid==lchilddpid:
                            node.ancestor=treenode
                            treenode.lchild=node
                            self.myQueue.append(node)
                            lflag=True
                if key[0]==dpid and key[1]==2:
                    rchilddpid=links[key][0]
                    for node in nodelist:
                        if node.dpid==rchilddpid:
                            node.ancestor=treenode
                            treenode.rchild=node
                            self.myQueue.append(node)
                            rflag=True                                   
            # add its in list1 and remove from myqueue
            list1.append(treenode)
            self.myQueue.pop(0)
        return list1
    
    def genpath(self,start,end):
        # this fun is used to gen a path from start to end
        # start and end are all tree node
        if start.dpid==end.dpid:
            print('Start and End are the same')
            return [start.dpid]
        path1=[]
        while True:
            path1.append(start.dpid)
            if start.ancestor!=None:
                start=start.ancestor
            else:
                break
        
        print('path1 is ',path1)
        path2=[]
        while True:
            path2.append(end.dpid)
            if end.ancestor!=None:
                end=end.ancestor
            else:
                break   
        print('path2 is ',path2)
        # find the same nearest ancestor of start and end
        junction=0
        for dpid in path1:
            if dpid in path2:
                # this dpid is the junction
                junction=dpid
                break
        #print('junction is ',junction)
        print('Junction is ', junction)
        path2.reverse()
        junctionindex1=path1.index(junction)
        junctionindex2=path2.index(junction)
        return path1[0:junctionindex1]+path2[junctionindex2:]        
        
        
            
        
            


            
    
                    
                
def rootfirst(depth):
    if depth==1:
        return [1]
    if depth==2:
        return [1,2,3]
    if depth==3:
        return [1,2,5,3,4,6,7]
    if depth==4:
        return [1,2,9,3,6,10,13,4,5,7,8,11,12,14,15]
    if depth==5:
        return [1,2,17,3,10,18,25,4,7,11,14,19,22,26,29,5,6,8,9,12,13,15,16,20,21,22,23,27,28,30,31]

def eachlayer(depth):
    # this fun is use to get each layer, then we can get the path from start to end
    layers=[]
    tree=rootfirst(depth)
    i=1
    while i<=depth:
        layers.append(tree[2**(i-1)-1:2**(i)-1])
        i=i+1
    return layers
    
def genpath(depth,start,end):
    # this fun is used to get a path from start to end in a bin tree
    # path is a list link [3,5,7]
    startlayer=0
    endlayer=0
    layers=eachlayer(depth)
    for layer in layers:
        if start in layer:
            sindex=layer.index(start)
            startlayer=layers.index(layer)
        if end in layer:
            eindex=layer.index(end)
            endlayer=layers.index(layer)        
    
    # for start node
    spath=[]
    spath.append(start)
    while startlayer>=0:
        if startlayer==0:
            break
        else:
            # find index
            startlayer=startlayer-1
            sindex=sindex/2
            node=layers[startlayer][sindex]
            spath.append(node)
    # for end node
    epath=[]
    epath.append(end)
    while endlayer>=0:
        if endlayer==0:
            break
        else:
            # find index
            endlayer=endlayer-1
            eindex=eindex/2
            node=layers[endlayer][eindex]
            epath.append(node)    
    # find the biggest same node in two path, use it as the junction
    flag=False
    for s in spath:
        for e in epath:
            if s==e:
                junction=s
                flag=True
        if flag:
            break
    if not flag:  # no junction, stop and return 
        return []
    path1=[]
    path2=[]
    for item in spath:
        if item!=junction:
            path1.append(item)
        else:
            break
    for item in epath:
        if item!=junction:
            path2.append(item)
        else:
            break
    path2.reverse()
    path=path1+[junction]+path2
    return path

def pathtolink(path):
    # we use this fun to convert path to multi edge:
    links=[]
    for i in range(0,len(path)-1):
        edge=(path[i],path[i+1])
        links.append(edge)
    return links

def gendepth(numoflinks):
    # this fun is used to calculate the depth of a tree base on its count of links
    i=0
    while True:
        i=i+1
        if 2**i>numoflinks:
            break


def genrandmac(num=1):
    # this fun is used to gen a rand mac, the format is 'ff:ff:ff:ff:ff:ff'
    list1=['1','2','3','4','5','6','8','9','a','b','c','d','e','f']
    mac=''
    for i in range(0,12):
        mac=mac+random.sample(list1,1)[0]
    # format the mac
    fmac=mac[0:2]+':'+mac[2:4]+':'+mac[4:6]+':'+mac[6:8]+':'+mac[8:10]+':'+mac[10:12]
    return fmac

def countframe(swichtype=0,path=[]):
    # this fun is used to count frame, 0 mean normal switch
    # 1 mean mspg, path is a ovs list
    count=1
    if swichtype==0:
        for item in range(1,len(path)):
            count=count*23
            return count+1
    if swichtype==1:
        for item in range(1,len(path)):
            count=count+2
            return count+1        
        
    
if __name__=='__main__':

    t1=Tree()
    tree=t1.gentree(nodes, links)
    for node in tree:
        node.show()
    
        