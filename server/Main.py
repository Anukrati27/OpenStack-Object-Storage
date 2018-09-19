import Server
import sys
import os
import shutil
import subprocess
import GlobalVars
import math
import hashlib
import getpass

MD5SUM_BITSIZE = 128

#creating directories at hardDisks
def initialiseDirectory():
    try:
        for key, value in GlobalVars.indexToHardDiskMap.items():
            prog = subprocess.Popen(["ssh","-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", value,\
                                     "rm -rf", GlobalVars.diskFilePath], stderr=subprocess.PIPE)
            errdata = prog.communicate()[1]
            if errdata:
                print (errdata)
        '''
        if os.path.isdir(GlobalVars.diskFilePath):
            shutil.rmtree(GlobalVars.diskFilePath)
        os.makedirs(GlobalVars.diskFilePath)
        os.chmod(GlobalVars.diskFilePath, 0o777)

        for key, value in GlobalVars.indexToHardDiskMap.items():
            prog = subprocess.Popen(["scp", "-r", "-B", GlobalVars.diskFilePath,  value+":/tmp"], stderr=subprocess.PIPE)
            errdata = prog.communicate()[1]
            if errdata:
                print (errdata)

        shutil.rmtree(GlobalVars.diskFilePath)
        '''
    except Exception as e:
        print ("Cannot start server. Error in creating directories ",str(e))

#setting global variables to be shared between different client threads
def initialisingVariables(argv):
    GlobalVars.noOfPartitions = int(argv[1])
    GlobalVars.lookUpTable = [ [-1] * int(math.pow(2, GlobalVars.noOfPartitions)) for _ in range(GlobalVars.noOfReplicas)]
    mapkey = 0
    for i in range(2, len(sys.argv)):
        GlobalVars.indexToHardDiskMap[mapkey] = sys.argv[i]
        mapkey = mapkey + 1
    GlobalVars.noOfHardDisks = len(GlobalVars.indexToHardDiskMap)
    factor = int(math.pow(2,GlobalVars.noOfPartitions)) / GlobalVars.noOfHardDisks
    factor = int(factor)
    for i in range(0, GlobalVars.noOfHardDisks):
        start = factor*i
        if (i == GlobalVars.noOfHardDisks-1):
            end = int(math.pow(2,GlobalVars.noOfPartitions))
        else:
            end = factor*(i+1)
        for index in range(start, end):
            GlobalVars.lookUpTable[0][index] = i
            GlobalVars.lookUpTable[1][index] = (i+1)%GlobalVars.noOfHardDisks
        GlobalVars.diskPartCountMap[i] = end-start



#Main function for starting server, setting global parameters and creating directories
if __name__ == '__main__':
    try:
        #checking if required parameters are present
        if len(sys.argv) < 4:
            print ("Provide input in following form")
            print ("python Main.py partition-size hard-disk1 hard-disk2...")
            exit(0)
        GlobalVars.loginName = getpass.getuser()
        GlobalVars.diskFilePath = "/tmp/"+GlobalVars.loginName+"/"
        #initialising server
        initialisingVariables(sys.argv)
        initialiseDirectory()
        server = Server.Server()
        server.startServer()
    except Exception as e:
        print("Error while running server: ",str(e))
        exit(0)
