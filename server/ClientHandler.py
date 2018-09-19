import threading
import time
import hashlib
import subprocess
import math
import os
import shutil
import GlobalVars
import pipes

MD5SUM_BITSIZE = 128
lock = threading.Lock()

#This is a thread class serving requests for each client
class ClientHandler (threading.Thread):
    def __init__(self, threadID, name, conn):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.conn = conn

    def run(self):
        try:
            self.readData(self.name)
        except Exception as e:
            print (self.name,"-->Error in reading data " + str(e))
        if self.conn:
            self.conn.close()
        print ("Exiting ", self.name)

    #This function runs until client break the connection by sending quit command or some exception occurs
    def readData(self, threadName):
        while True:
            data = self.conn.recv(1024).decode()
            if "quit" == data:
                break
            
            if GlobalVars.machineDownFlag == True:
                with GlobalVars.heartBeatLock:
                    print("$$$$$$$$$$$$$$")
                    for items in GlobalVars.machineDownList:
                        self.removeHardDisk("remove "+items, False)
                    GlobalVars.machineDownList = []
                    GlobalVars.machineDownFlag = False
            
            if data.startswith("download "):
                 self.downloadFile(data)
            elif data.startswith("list "):
                 self.listUserFile(data)
            elif data.startswith("upload "):
                 self.uploadFile(data)
            elif data.startswith("delete "):
                 self.deleteFile(data)
            elif data.startswith("add "):
                 self.addHardDisk(data)
            elif data.startswith("remove "):
                 self.removeHardDisk(data)
            else:
                 print("Lost Connection to client ", self.name,". Exiting")
                 break

    # This function finds the disk location for a user/object and returns to the client for file download operation
    def downloadFile(self, message):
        try:
            userName = message.split(" ")[1].split("/")[0]
            fileName = message.split(" ")[1].split("/")[1]
            filePath = message.split(" ")[1]
            print(self.name,"--->downloading object ",filePath)
            key = self.keyGenerator(filePath)
            data = "Disk:"
            for i in range(0, GlobalVars.noOfReplicas):
                disk = GlobalVars.lookUpTable[i][key]
                data = data + GlobalVars.indexToHardDiskMap[disk] + " "
            if GlobalVars.metaData[filePath][1]:
                data = data + GlobalVars.metaData[filePath][1]
            else:
                data = "Error in operation: Corrupted file"
            self.conn.send(data.encode())
            message = self.conn.recv(1024).decode()
            print (self.name,"-->",message)
        except Exception as e:
            data = "Error in operation: "+str(e)
            print(self.name,"-->",data)
            if self.conn:
                self.conn.send(data.encode())

    #This function checks if a folder exists for  current user at disks.
    #If folder exists it fetches the file names available in the folder using command ls -lrt.
    #It removes the backup files and return the list of main files to user.
    def listUserFile(self, message):
        try:
            print(self.name,"--> listing user ",message.split(" ")[1])
            userName = message.split(" ")[1]
            fileNameList = []
            missingFileList = []
            sendData = ""
            for key, value in GlobalVars.indexToHardDiskMap.items():
                #flag = self.checkFileExistsOnHardDisk(GlobalVars.loginName+"@"+value, GlobalVars.diskFilePath+userName)
                #if flag:
                data = self.getFileListForUserFromHardDisk(GlobalVars.loginName+"@"+value, GlobalVars.diskFilePath+userName)
                if "" == data:
                    continue
                splitData = data.split("\n")
                splitData = [x for x in splitData if x]
                for i in range(1,len(splitData)):
                    fileInList = splitData[i].split(" ")[-1]
                    if fileInList not in missingFileList:
                        missingFileList.append(fileInList)
                    else:
                        missingFileList.remove(fileInList)
                    if fileInList not in fileNameList:
                        fileNameList.append(fileInList)
                        sendData = sendData + splitData[i]+"\n"

            #restoring lost files from either main disk or backup
            for item in missingFileList:
                objectName = userName + "/" + item
                key = self.keyGenerator(objectName)
                disk1 = GlobalVars.indexToHardDiskMap[GlobalVars.lookUpTable[0][key]]
                disk2 = GlobalVars.indexToHardDiskMap[GlobalVars.lookUpTable[1][key]]
                flag = self.checkFileExistsOnHardDisk(GlobalVars.loginName+"@"+disk1, GlobalVars.diskFilePath+objectName)
                if flag == False:
                    self.copyFilesToHardDisk(GlobalVars.loginName+"@"+disk2+":"+GlobalVars.diskFilePath+objectName, \
                                        GlobalVars.loginName+"@"+disk1+":"+GlobalVars.diskFilePath+objectName, False)

                else:
                    self.copyFilesToHardDisk(GlobalVars.loginName+"@"+disk1+":"+GlobalVars.diskFilePath+objectName, \
                                        GlobalVars.loginName+"@"+disk2+":"+GlobalVars.diskFilePath+objectName, False)

            if sendData == "":
                sendData = "No file present for user "
            else:
                sendData = userName + " contains the following files: \n" + sendData
            print (self.name + "--> " + sendData)
            self.conn.send(sendData.encode())
        except Exception as e:
            data = "Error in operation: "+str(e)
            print(self.name,"-->",data)
            if self.conn:
                self.conn.send(data.encode())
            
    #This function finds the disk location for a given user/object and returns the details to client for file upload operation
    #This function also checks if file already exists at hard disk
    def uploadFile(self, message):
        try:
            userName = message.split(" ")[1].split("/")[0]
            fileName = message.split(" ")[1].split("/")[1]
            filePath = message.split(" ")[1]
            print(self.name,"--->uploading object ",filePath)
            key = self.keyGenerator(filePath)
            data = ""
            flag = []
            for i in range(0, GlobalVars.noOfReplicas):
                disk = GlobalVars.lookUpTable[i][key]
                data = data  + GlobalVars.indexToHardDiskMap[disk] + " "
                flag.append(self.checkFileExistsOnHardDisk(GlobalVars.loginName+"@"+GlobalVars.indexToHardDiskMap[disk],\
                                                      GlobalVars.diskFilePath+filePath))

            if(flag[0] == False and flag[1] == False):
                data = "File absent:" + data
            else:
                data = "File present:" + data

            self.conn.send(data.encode())
            message = self.conn.recv(1024).decode()
            retData = message.split(":$")
            if( len(retData) == 2):
                GlobalVars.metaData[filePath] = [key,retData[1]]
            print (self.name,"-->",retData[0])
        except Exception as e:
            err = "Error in operation "+str(e)
            print (self.name,"-->",err)
            if self.conn:
                self.conn.send(err.encode())

    #This function first finds the disks for a given user/object.
    #If file not present at any disk it returns false, else ask for confirmation from client
    #If client cancels the delete operation, process is terminated.
    #Else we deletes the file from first harddisk, If it fails process terminates with error
    #If pass, we delete the file from second disk, If successful, success message if delivered to client
    #Else we copy the file to main disk, list message and return.
    def deleteFile(self, message):
        try:
            filePath = message.split(" ")[1]
            key = self.keyGenerator(filePath)
            print(self.name,"--->deleting object ",filePath)
            disk1 = GlobalVars.indexToHardDiskMap[GlobalVars.lookUpTable[0][key]]
            disk2 = GlobalVars.indexToHardDiskMap[GlobalVars.lookUpTable[1][key]]
            disk1Flag = self.checkFileExistsOnHardDisk(GlobalVars.loginName+"@"+disk1, GlobalVars.diskFilePath+filePath)
            disk2Flag = self.checkFileExistsOnHardDisk(GlobalVars.loginName+"@"+disk2, GlobalVars.diskFilePath+filePath)
            
            if disk1Flag == False and disk2Flag == False:
                data = "Error in operation: File not present at server"
                self.conn.send(data.encode())
                print(self.name,"-->",data)
                return

            data = "File found on server"
            self.conn.send(data.encode())
            data = self.conn.recv(1024).decode()
            if "" == data:
                return
            if data.startswith("Error in operation"):
                print(self.name,"-->",data)
                return
            else:
                flag = self.deleteFilesFromHardDisk(disk1, filePath)
                if not flag:
                    return
                flag = self.deleteFilesFromHardDisk(disk2, filePath)
                if not flag:
                    self.copyFilesToHardDisk(GlobalVars.loginName+"@"+disk2+":"+GlobalVars.diskFilePath+filePath, \
                                             GlobalVars.loginName+"@"+disk1+":"+GlobalVars.diskFilePath+filePath, False)
                    return
                retMesg = "File Deleted Successfully."
                GlobalVars.metaData.pop(filePath)
                self.conn.send(retMesg.encode())
                print (self.name,"-->",retMesg)
        except Exception as e:
            err = "Error in operation "+str(e)
            print (self.name,"-->",err)
            if self.conn:
                self.conn.send(err.encode())


    def addHardDisk(self, message):
        try:
            #print("before0--------------------")
            #for i in range(0,2):
            #    print(GlobalVars.lookUpTable[i])
            #print("--------GlobalVars.noOfHardDisks--",GlobalVars.noOfHardDisks)
            #print("------GlobalVars.diskPartCountMap---",GlobalVars.diskPartCountMap)
            #print("---indexToHardDiskMap---",GlobalVars.indexToHardDiskMap)
            #print("---metaData---",GlobalVars.metaData)
            hardDisk = message.split(" ")[1]
            if hardDisk in GlobalVars.indexToHardDiskMap.values():
                sendData = "Disk already present in system"
                print (sendData)
                self.conn.send(sendData.encode())
                return
            print(self.name,"--> adding hard disk ", hardDisk)
            prog = subprocess.Popen(["ssh","-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", hardDisk,\
                                     "rm -rf", GlobalVars.diskFilePath+"*"], stderr=subprocess.PIPE)
            stdout, stderr = prog.communicate()
            newNoOfHardDisk = GlobalVars.noOfHardDisks + 1
            minDiskPartCount = min(GlobalVars.diskPartCountMap.items(), key=lambda x: x[1])[1]
            partitionToSwap = int(minDiskPartCount/GlobalVars.noOfHardDisks)
            if (partitionToSwap < 1):
                sendData = "Partition size threshold reached. Run server with increased partition power to add more disks"
                print (sendData)
                self.conn.send(sendData.encode())
                return
            diskIndexList = sorted(GlobalVars.indexToHardDiskMap)
            maxDiskNo = diskIndexList[-1]
            diskIndexMap = {}
            for i in range(0, len(diskIndexList)-1):
                diskIndexMap[diskIndexList[i]] = diskIndexList[i+1]
            diskIndexMap[diskIndexList[-1]] = diskIndexList[0]
            GlobalVars.diskPartCountMap[maxDiskNo+1] = 0
            for hdNum, hdIp in GlobalVars.indexToHardDiskMap.items():
                diskPartition = [index for index, value in enumerate(GlobalVars.lookUpTable[0]) if value == hdNum]
                reAssignDiskPartition = diskPartition[-1*partitionToSwap:]
                backupNew = GlobalVars.indexToHardDiskMap[diskIndexMap[maxDiskNo]]
                backupOld = GlobalVars.indexToHardDiskMap[diskIndexMap[hdNum]]
                backupPartitions = []
                if(hdNum == maxDiskNo):
                    backupPartitions = diskPartition[:(len(diskPartition) - partitionToSwap)]
                for obj, keyList in GlobalVars.metaData.items():
                    key = keyList[0]
                    if key in reAssignDiskPartition: 
                        if(hardDisk != backupOld and hardDisk != hdIp):
                            self.movingFilesInUpdateInNoOfHardDisks(hardDisk, backupOld,  obj, hdIp)
                        if( backupNew != backupOld and backupNew != hardDisk):
                            self.movingFilesInUpdateInNoOfHardDisks(backupNew, hardDisk, obj, backupOld)
                    if(hdNum == maxDiskNo):
                        if key in backupPartitions:
                            if(hardDisk != backupOld and hardDisk != hdIp):
                                self.movingFilesInUpdateInNoOfHardDisks(hardDisk, hdIp, obj, backupOld)
                for item in reAssignDiskPartition:
                    GlobalVars.lookUpTable[0][item] = maxDiskNo + 1
                    GlobalVars.lookUpTable[1][item] = diskIndexMap[maxDiskNo]
                for item in backupPartitions:
                    GlobalVars.lookUpTable[1][item] = maxDiskNo + 1
                GlobalVars.diskPartCountMap[hdNum] = GlobalVars.diskPartCountMap[hdNum]-len(reAssignDiskPartition)
                GlobalVars.diskPartCountMap[maxDiskNo+1] = GlobalVars.diskPartCountMap[maxDiskNo+1]+len(reAssignDiskPartition)

            GlobalVars.noOfHardDisks = newNoOfHardDisk
            GlobalVars.indexToHardDiskMap[maxDiskNo + 1] = hardDisk

            retData = ""
            for hdNum, hdIp in GlobalVars.indexToHardDiskMap.items():
                retData = retData + "\n\n" + hdIp + "\n"
                sendData = self.getFileListFromHardDisk(GlobalVars.loginName+"@"+hdIp, GlobalVars.diskFilePath)
                retData = retData + sendData.split('\n\n', 1)[-1]

            print (self.name + "--> " + retData)
            self.conn.send(retData.encode())
            #print("after--------------")
            #for i in range(0,2):
            #    print(GlobalVars.lookUpTable[i])
            #print("--------GlobalVars.noOfHardDisks--",GlobalVars.noOfHardDisks)
            #print("------GlobalVars.diskPartCountMap---",GlobalVars.diskPartCountMap)
            #print("---indexToHardDiskMap---",GlobalVars.indexToHardDiskMap)
        except Exception as e:
            data = "Error in operation: "+str(e)
            print(self.name,"-->",data)
            if self.conn:
                self.conn.send(data.encode())
            

    def movingFilesInUpdateInNoOfHardDisks(self,hardDisk, backupOld, obj, hdIp): 
        flag = self.createFolderOnHardDisk(GlobalVars.loginName+"@"+hardDisk, GlobalVars.diskFilePath+obj.split("/")[0], False)
        flag = self.copyFilesToHardDisk(GlobalVars.loginName+"@"+hdIp+":"+GlobalVars.diskFilePath+obj, \
                                        GlobalVars.loginName+"@"+hardDisk+":"+GlobalVars.diskFilePath+obj, False)
        if not flag:
            flag = self.copyFilesToHardDisk(GlobalVars.loginName+"@"+backupOld+":"+GlobalVars.diskFilePath+obj, \
                                            GlobalVars.loginName+"@"+hardDisk+":"+GlobalVars.diskFilePath+obj, False)
        
        flag = self.deleteFilesFromHardDisk(hdIp, obj, False)

                 
    def removeHardDisk(self, message, opTypeFlag=True):
        try:
            hardDisk = message.split(" ")[1]

            #print("before0--------------------")
            #for i in range(0,2):
            #    print(GlobalVars.lookUpTable[i])
            #print("--------GlobalVars.noOfHardDisks--",GlobalVars.noOfHardDisks)
            #print("------GlobalVars.diskPartCountMap---",GlobalVars.diskPartCountMap)
            #print("---indexToHardDiskMap---",GlobalVars.indexToHardDiskMap)
            #print("---metaData---",GlobalVars.metaData)
            if GlobalVars.noOfHardDisks == 1:
                sendData = "Only one disk present in the system. Cannot perform the delete operation"
                if opTypeFlag:
                    self.conn.send(sendData.encode())
                print (sendData)
                return
            if hardDisk not in GlobalVars.indexToHardDiskMap.values():
                sendData = "Disk not being used in the system"
                print (sendData)
                if opTypeFlag:
                    self.conn.send(sendData.encode())
                return

            print(self.name,"--> removing hard disk ", hardDisk)

            indList = [index for index, value in GlobalVars.indexToHardDiskMap.items() if value == hardDisk]
            indexToHD = indList[0]
            partitionToReloc = [index for index, value in enumerate(GlobalVars.lookUpTable[0]) if value == indexToHD]
            partAssignPerDisk = int(GlobalVars.diskPartCountMap[indexToHD] / (GlobalVars.noOfHardDisks-1))
            partToAssignToLastDisk = int(partAssignPerDisk + (GlobalVars.diskPartCountMap[indexToHD] % (GlobalVars.noOfHardDisks-1)))
            GlobalVars.indexToHardDiskMap.pop(indexToHD)
            diskIndexList = sorted(GlobalVars.indexToHardDiskMap)
            diskIndexMap = {}
            
            for i in range(0, len(diskIndexList)-1):
                diskIndexMap[diskIndexList[i]] = diskIndexList[i+1]
            diskIndexMap[diskIndexList[-1]] = diskIndexList[0]
            bkDiskIndex = GlobalVars.lookUpTable[1][partitionToReloc[0]]
            backupDisk = GlobalVars.indexToHardDiskMap[bkDiskIndex]
            objList = self.getFolderAndFilesFromHardDisk(GlobalVars.loginName+"@"+backupDisk, GlobalVars.diskFilePath)
            partNo = 0
            counter = 1
            for hdNum, hdIp in GlobalVars.indexToHardDiskMap.items():
                end = partAssignPerDisk
                if counter == GlobalVars.noOfHardDisks - 1:     
                    end = partToAssignToLastDisk
                counter = counter + 1
                for i in range(0, end):
                    GlobalVars.lookUpTable[0][partitionToReloc[partNo]] = hdNum
                    GlobalVars.lookUpTable[1][partitionToReloc[partNo]] = diskIndexMap[hdNum]
                    partNo = partNo + 1
                GlobalVars.diskPartCountMap[hdNum] = GlobalVars.diskPartCountMap[hdNum] + end
           
            backupPartToReloc = [index for index, value in enumerate(GlobalVars.lookUpTable[1]) if value == indexToHD]
            for i in range(0,len(backupPartToReloc)):
                GlobalVars.lookUpTable[1][backupPartToReloc[i]] = bkDiskIndex
            bkDisk = GlobalVars.indexToHardDiskMap[GlobalVars.lookUpTable[0][backupPartToReloc[0]]]

            for obj, keyList in GlobalVars.metaData.items():
                key = keyList[0]
                if key in partitionToReloc:
                    mainDisk = GlobalVars.indexToHardDiskMap[GlobalVars.lookUpTable[0][key]]
                    newBackupDisk = GlobalVars.indexToHardDiskMap[GlobalVars.lookUpTable[1][key]]
                    if (backupDisk != mainDisk):
                        self.createFolderOnHardDisk(GlobalVars.loginName+"@"+mainDisk, GlobalVars.diskFilePath+obj.split("/")[0], False)
                        self.copyFilesToHardDisk(GlobalVars.loginName+"@"+backupDisk+":"+GlobalVars.diskFilePath+obj, \
                                                 GlobalVars.loginName+"@"+mainDisk+":"+GlobalVars.diskFilePath+obj, False)
                    if( backupDisk != newBackupDisk):
                        self.createFolderOnHardDisk(GlobalVars.loginName+"@"+newBackupDisk, GlobalVars.diskFilePath+obj.split("/")[0], False)
                        self.copyFilesToHardDisk(GlobalVars.loginName+"@"+backupDisk+":"+GlobalVars.diskFilePath+obj, \
                                                 GlobalVars.loginName+"@"+newBackupDisk+":"+GlobalVars.diskFilePath+obj, False)
                    if (backupDisk != mainDisk) and ( backupDisk != newBackupDisk):
                        self.deleteFilesFromHardDisk(backupDisk, obj, False)
            
                if key in backupPartToReloc:
                    if(bkDisk != backupDisk):
                        self.createFolderOnHardDisk(GlobalVars.loginName+"@"+backupDisk, GlobalVars.diskFilePath+obj.split("/")[0], False)
                        self.copyFilesToHardDisk(GlobalVars.loginName+"@"+bkDisk+":"+GlobalVars.diskFilePath+obj, \
                                                 GlobalVars.loginName+"@"+backupDisk+":"+GlobalVars.diskFilePath+obj, False)
            
            GlobalVars.noOfHardDisks = GlobalVars.noOfHardDisks - 1
            GlobalVars.diskPartCountMap.pop(indexToHD)
          
            retData = ""
            for hdNum, hdIp in GlobalVars.indexToHardDiskMap.items():
                retData = retData + "\n\n" + hdIp + "\n"
                sendData = self.getFileListFromHardDisk(GlobalVars.loginName+"@"+hdIp, GlobalVars.diskFilePath)
                retData = retData + sendData.split('\n\n', 1)[-1]

            print (self.name + "--> " + retData)
            if opTypeFlag:
                self.conn.send(retData.encode())
            #print("after--------------")
            #for i in range(0,2):
            #    print(GlobalVars.lookUpTable[i])
            #print("--------GlobalVars.noOfHardDisks--",GlobalVars.noOfHardDisks)
            #print("------GlobalVars.diskPartCountMap---",GlobalVars.diskPartCountMap)
            #print("---indexToHardDiskMap---",GlobalVars.indexToHardDiskMap)
        except Exception as e:
            data = "Error in operation: "+str(e)
            print(self.name,"-->",data)
            if opTypeFlag:
                if self.conn:
                    self.conn.send(data.encode())

    def getFolderAndFilesFromHardDisk(self, hostName, userFolder):
        try:
            prog = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", hostName,\
                                     "find",userFolder,"-print"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = prog.communicate()
            tempList = stdout.decode().split("\n")
            retList = []
            for i in range(0, len(tempList)):
                tempStr = tempList[i][len(userFolder):]
                count = tempStr.count("/")
                if tempStr != "" and count == 1:
                    retList.append(tempStr)
            return retList
        except Exception as e:
            return []

    #This function creates a folder on remote machine
    def createFolderOnHardDisk(self, hostName, folder, flag = False):
        prog = subprocess.Popen( ['ssh',"-o", "StrictHostKeyChecking=no","-o","BatchMode=yes", hostName, \
                                "mkdir","-p", folder], stderr=subprocess.PIPE)
        errdata = prog.communicate()[1].decode()
        print(errdata)
        if prog.returncode and errdata != "":
            data = "Error in operation:"+errdata
            print(data)
            if flag:
                self.conn.send(data.encode())
            return False
        return True



    #this function copies file from one machine to other
    def copyFilesToHardDisk(self, source, destination, flag=True):
        prog = subprocess.Popen(["scp", "-r", source, destination], stderr=subprocess.PIPE)
        errdata = prog.communicate()[1].decode()
        print (self.name,"-->",errdata)
        if prog.returncode and errdata != "":
            if flag:
                data = "Error in operating on object: cannot access file"
                self.conn.send(data.encode())
            return False
        return True

    #this function deletes files from remote machine
    def deleteFilesFromHardDisk(self, disk, fileName, flag=True):
        prog = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", GlobalVars.loginName+"@"+disk,\
                                "rm", GlobalVars.diskFilePath+fileName], stderr=subprocess.PIPE)
        errdata = prog.communicate()[1].decode()
        print (self.name,"-->",errdata)
        if prog.returncode and errdata != "":
            if flag:
                data = "Error in operating on object: Error deleting file"
                self.conn.send(data.encode())
            return False
        return True

    #This function generates the key for each user/object values
    def keyGenerator(self, message):
        keyIntermediate = int(hashlib.md5(message.encode('utf-8')).hexdigest(), 16)
        key = (keyIntermediate >> (MD5SUM_BITSIZE - GlobalVars.noOfPartitions))%int(math.pow(2,GlobalVars.noOfPartitions))
        return key

    #this function returns true if a file/folder exists on a retmote machine else returns false
    def checkFileExistsOnHardDisk(self, hostName, fileName):
        resp = subprocess.call( ['ssh',"-o", "StrictHostKeyChecking=no","-o","BatchMode=yes", hostName, 'test -e ' + pipes.quote(fileName)])
        if resp == 0:
            return True
        else:
            return False

    #this function fetches the file list present at a particular path in remote machine in ls -lrt format
    def getFileListForUserFromHardDisk(self, hostName, userFolder):
        try:
            prog = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", hostName,\
                                     "ls","-p","-lrt", userFolder], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = prog.communicate()
            return stdout.decode()
        except Exception as e:
            return ""

    #this function fetches the file list present at a particular path in remote machine in ls -lrt format
    def getFileListFromHardDisk(self, hostName, userFolder):
        try:
            prog = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", hostName,\
                                     "ls","-R","-lrt", userFolder], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = prog.communicate()
            return stdout.decode()
        except Exception as e:
            return ""

