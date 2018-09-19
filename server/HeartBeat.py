import GlobalVars
import subprocess
import threading
import time

GlobalVars.heartBeatLock = threading.RLock()

class HeartBeat (threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        try:
            self.checkIfMachineIsAlive(self.name)
        except Exception as e:
            print (self.name," error--> " + str(e))
        print ("Exiting ", self.name)

    def checkIfMachineIsAlive(self, threadName):
        try:
            while(1):
                with GlobalVars.heartBeatLock:
                    localMap = GlobalVars.indexToHardDiskMap
                    counterList = []
                    for i in range(0, len(localMap)):
                        counterList.append(0)
                    while(1):
                        counter = 0
                        for hdNum, hdIp in localMap.items():
                            output = subprocess.Popen(["ping", hdIp],stdout = subprocess.PIPE).communicate()[0]
                            print(output) 
                            if ('unreachable' in output):
                                counterList[counter] = counterList[counter] + 1
                            if counterList[counter] > 3:
                                GlobalVars.machineDownList.append(hdIp)
                                GlobalVars.machineDownFlag = True
                        
                            counter = counter + 1
                        if GlobalVars.machineDownFlag == True:
                            time.sleep(4)
                            break
                        time.sleep(1)
        except Exception as e:
            print("Exception is----> " , str(e))
            pass



