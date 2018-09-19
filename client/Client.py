import socket
import subprocess
import time
import getpass
import pipes
import errno
import hashlib
import os

#You can update these 2 variables to change the upload and download path
uploadPath = "./"
downloadPath = "./"
loginName = getpass.getuser()
path = "/tmp/"+loginName+"/"

class Client:

    def __init__(self, host, port):
        self.host = socket.gethostbyname(host)
        self.port = port
        self.mySocket = None

    def startClient(self):
        try:
            self.mySocket = socket.socket()
            self.mySocket.connect((self.host, self.port))
            #self.mySocket.settimeout(10)
        except Exception as e:
             print ("Error in connection to server " + str(e))
             print ("Please check the ip-address or Port Number!!")
             exit(0)

    #This function parses all the inputs provided by user, verifies them
    #if invalid input, client logs the error,
    #if valid, client sends the command to server for processing
    def sendMessage(self, message):
        try:
            if "quit" == message.lower():
                self.stopClient(message)
                return
            messWordArr = message.strip(' ').split(" ")
            messWordArr = [x.strip(' ') for x in messWordArr]
            messWordArr = [x for x in messWordArr if x]
            count = message.count('/')
            if len(messWordArr) != 2:
                print("Invalid command entered. Please type help for details")
                return
            objDetails = messWordArr[1].split("/")
            objDetails = [x.strip(' ') for x in objDetails]
            objDetails = [x for x in objDetails if x]
            if len(objDetails) == 1:
                message = messWordArr[0] + " " + objDetails[0]
            elif len(objDetails) == 2:
                message = messWordArr[0] + " " + objDetails[0] + "/" + objDetails[1]
           
            if("download" == messWordArr[0] and len(objDetails) == 2 and count == 1):
                self.downloadFile(message)
            elif("list"== messWordArr[0] and len(objDetails) == 1 and count == 0):
                self.listUserFiles(message)
            elif("upload" == messWordArr[0] and len(objDetails) == 2 and count == 1):
                self.uploadUserFiles(message)
            elif("delete" == messWordArr[0] and len(objDetails) == 2 and count == 1):
                self.deleteUserFiles(message)
            elif("add"== messWordArr[0] and len(objDetails) == 1 and count == 0):
                self.addHardDisk(message)
            elif("remove"== messWordArr[0] and len(objDetails) == 1 and count == 0):
                self.removeHardDisk(message)
            else:
                print("Invalid command entered. Please type help for details")
        except Exception as e:
            print ("Error in parsing message " + str(e))
            exit(0)

    #This function sends download request to server and recieves the disk address from server
    #It then checks if object is present at any disk, if not it logs error if object missing(both main and backup)
    #It copies object if it is missing at any disk(main or backup)
    #It then copies file first from main disk to client. If error copies from backup machine
    #If error in copying from both main and backup, it logs error, else shows the download path for object
    def downloadFile(self, message):
        try:
            self.mySocket.send(message.encode())
            data = self.mySocket.recv(1024).decode()
            if data.startswith("Error in operation"):
                print (data)
                return
            if "" == data:
                print("Connection to Server Broken. Exiting!!")
                exit(0) 
            fileName = message.split(" ")[1].split("/")[1]
            userName = message.split(" ")[1].split("/")[0]
            filePath = message.split(" ")[1]

            disk1 = data.split(":")[1].split(" ")[0].strip(" ")
            disk2 = data.split(":")[1].split(" ")[1].strip(" ")
            metaData = data.split(":")[1].split(" ")[2].strip(" ")
            disk1Flag = self.checkFileExistsOnHardDisk(loginName+"@"+disk1, path+filePath)
            disk2Flag = self.checkFileExistsOnHardDisk(loginName+"@"+disk2, path+filePath)
            if disk1Flag == False and disk2Flag == False:
                message = "Object not present at any hardDisk."
                print(message)
                self.mySocket.send(message.encode())
                return

            if not disk1Flag:
                self.copyFilesToHardDisk(loginName+"@"+disk2+":"+path+filePath,\
                                                    loginName+"@"+disk1+":"+path+filePath, False)
            elif not disk2Flag:
                self.copyFilesToHardDisk(loginName+"@"+disk1+":"+path+filePath,\
                                                    loginName+"@"+disk2+":"+path+filePath, False)

            flag = self.copyFilesToHardDisk(loginName+"@"+disk1+":"+path+filePath, downloadPath, False)
            copy = ""
            with open(downloadPath+fileName, encoding="utf8", errors='ignore') as f:
                copy = f.read()

            if not flag or self.hashingData(copy) != metaData:
                flag = self.copyFilesToHardDisk(loginName+"@"+disk2+":"+path+filePath, downloadPath, False)
                copy = ""
                with open(downloadPath+fileName, encoding="utf8", errors='ignore') as f:
                    copy = f.read()

                if not flag:
                    message = "Error in copying object from server."
                    print(message)
                    self.mySocket.send(message.encode())
                    return
                elif self.hashingData(copy) != metaData:
                    message = "File corrupted."
                    print(message)
                    self.mySocket.send(message.encode())
                    return
                else:
                    self.copyFilesToHardDisk(loginName+"@"+disk2+":"+path+filePath,\
                                                    loginName+"@"+disk1+":"+path+filePath, False)
                finalCopy = copy
            else:
                finalCopy = copy
                flag = self.copyFilesToHardDisk(loginName+"@"+disk2+":"+path+filePath, downloadPath+"_temp_.txt", False)
                copy = ""
                with open(downloadPath+"_temp_.txt", encoding="utf8", errors='ignore') as f:
                    copy = f.read()
                if not flag or self.hashingData(copy) != metaData:
                    self.copyFilesToHardDisk(loginName+"@"+disk1+":"+path+filePath,\
                                                     loginName+"@"+disk2+":"+path+filePath, False)
                os.remove(downloadPath+"_temp_.txt")



            
            message = fileName+ ' is stored at ' + downloadPath
            self.mySocket.send(message.encode())
            print (message + "\n File is: \n" + finalCopy)
        except IOError as e:
            if e.errno == errno.EPIPE:
                print("Connection to Server broken. Exiting.")
                exit(0)
        except Exception as e:
            err = "Error in operation " + str(e)
            print (err)
            if self.mySocket:
                self.mySocket.send(message.encode())
            else:
                exit(0)

    #This function sents list command to server and displays the data received from client
    def listUserFiles(self, message):
        try:
            self.mySocket.send(message.encode())
            data = self.mySocket.recv(1024).decode()
            if "" == data:
                print("Connection to Server Broken. Exiting!!")
                exit(0) 
            print (data)
        except IOError as e:
            if e.errno == errno.EPIPE:
                print("Connection to Server broken. Exiting.")
                exit(0)
        except Exception as e:
            err = "!!Error in operation: "+str(e)
            print (err)


    #This function sends upload request to server, which returns the disk address and check if file already presents
    #if file already presentat disk, client asks confirmation for overriding the file.
    #If user cancels the operation, client logs message and return
    #Else client tries creating "loginName" folders at disks and return if error in creating folders
    #Then client transfer file from client machine to main disk, If error it returns logging error
    #If successful, it copies file to backup machine. If successful logs message
    #If backup fails, we delete file from the main machine and log error
    def uploadUserFiles(self, message):
        try:
            self.mySocket.send(message.encode())
            data = self.mySocket.recv(1024).decode()
            if data.startswith("Error in operation"):
                print (data)
                return
            if "" == data:
                print("Connection to Server Broken. Exiting!!")
                exit(0)
            result = data.split(":")[0]
            if "File present" == result:
                confirm = ""
                while (confirm.lower() != "n" and confirm.lower() != "y"):
                    confirm = input("File present at disk. Press Y to override file, N to cancel upload: ")
                if "n" == confirm.lower():
                    message = "Operation cancelled by user"
                    print (message)
                    self.mySocket.send(message.encode())
                    return
            fileName = message.split(" ")[1].split("/")[1]
            userName = message.split(" ")[1].split("/")[0]
            filePath = message.split(" ")[1]

            disk1 = data.split(":")[1].split(" ")[0].strip(" ")
            disk2 = data.split(":")[1].split(" ")[1].strip(" ")
            flag = self.createFolderOnHardDisk(loginName+"@"+disk1, path+userName)
            if not flag:
                return

            flag = self.createFolderOnHardDisk(loginName+"@"+disk2, path+userName)
            if not flag:
                return

            flag = self.copyFilesToHardDisk(uploadPath+fileName, loginName+"@"+disk1+":"+path+filePath)
            if not flag:  
                return

            flag = self.copyFilesToHardDisk(uploadPath+fileName, loginName+"@"+disk2+":"+path+filePath)
            if not flag:
                flag = self.deleteFilesFromHardDisk(disk1, path+filePath, False)
                return
            copy = ""
            with open(uploadPath+fileName, encoding="utf8", errors='ignore') as f:
                copy = f.read()
            retData = self.hashingData(copy)

            message = "Data copied successfully to "+ disk1 + " " + disk2
            self.mySocket.send((message+":$"+retData).encode())
            print(message)
        except IOError as e:
            if e.errno == errno.EPIPE:
                print("Connection to Server broken. Exiting.")
                exit(0) 
        except Exception as e:
            err = "Error in operation "+str(e)
            print (err)
            if self.mySocket:
                self.mySocket.send(err.encode())
            else:
                exit(0)

    #This function sends delete command to server. 
    #If file present at disks, server asks for confirmation.
    #On confirmation, client sends delete request back to server which deletes the file and returns success or failure message
    def deleteUserFiles(self, message):
        try:
            self.mySocket.send(message.encode())
            data = self.mySocket.recv(1024).decode()
            if data.startswith("Error in operation"):
                print (data)
                return
            if "" == data:
                print("Connection to Server Broken. Exiting!!")
                exit(0)

            confirm = ""
            while (confirm.lower() != "n" and confirm.lower() != "y"):
                confirm = input("Are you sure to delete file. Press Y/N: ")       
            if "n" == confirm.lower():
                data = "Error in operation. User cancelled the operation."
                print ("User cancelled the operation")
                self.mySocket.send(data.encode())
                return
            else:
                data = "Delete File"
                self.mySocket.send(data.encode())
            data = self.mySocket.recv(1024).decode()
            if "" == data:
                print("Connection to Server Broken. Exiting!!")
                exit(0)
            print(data)
        except IOError as e:
            if e.errno == errno.EPIPE:
                print("Connection to Server broken. Exiting.")
                exit(0)
        except Exception as e:
            err = "Error in operation "+str(e)
            print (err)
            if self.mySocket:
                self.mySocket.send(err.encode())
            else:
                exit(0)

    def addHardDisk(self, message):
        try:
            sock = socket.gethostbyname(message.split(" ")[1])
            prog = subprocess.Popen( ['ssh',"-o", "ConnectTimeout=2", "-o StrictHostKeyChecking=no","-o","BatchMode=yes", sock, "exit"], stderr=subprocess.PIPE)
            errdata = prog.communicate()[1].decode()
            if (prog.returncode and errdata != ""):
                print("Invalid Ip address provided")
                return
            message = "add " + str(sock)
            self.mySocket.send(message.encode())
            data = self.mySocket.recv(1024).decode()
            if "" == data:
                print("Connection to Server Broken. Exiting!!")
                exit(0)
            print(data)
        except IOError as e:
            if e.errno == errno.EPIPE:
                print("Connection to Server broken. Exiting.")
                exit(0)
        except Exception as e:
            err = "Error in operation "+str(e)
            print (err)


    def removeHardDisk(self, message):
        try:
            sock = socket.gethostbyname(message.split(" ")[1])
            prog = subprocess.Popen( ['ssh',"-o", "ConnectTimeout=2", "-o StrictHostKeyChecking=no","-o","BatchMode=yes", sock, "exit"], stderr=subprocess.PIPE)
            errdata = prog.communicate()[1].decode()
            if (prog.returncode and errdata != ""):
                print("Invalid Ip address provided")
                return
            message = "remove " + str(sock)
            self.mySocket.send(message.encode())
            data = self.mySocket.recv(1024).decode()
            if "" == data:
                print("Connection to Server Broken. Exiting!!")
                exit(0)
            print(data)
        except IOError as e:
            if e.errno == errno.EPIPE:
                print("Connection to Server broken. Exiting.")
                exit(0)
        except Exception as e:
            err = "Error in operation "+str(e)
            print (err)


    #close client socket
    def stopClient(self, message):
        self.mySocket.send(message.encode())
        self.mySocket.close()
 
    #This function copies file from one machine to other
    def copyFilesToHardDisk(self, source, destination, flag=True):
        prog = subprocess.Popen(["scp", "-r", "-B", source, destination], stderr=subprocess.PIPE)
        errdata = prog.communicate()[1].decode()
        if prog.returncode and errdata != "":
            data = "Error in operation:"+errdata
            print(data)
            if flag:
                if self.mySocket:
                    self.mySocket.send(data.encode())
                else:
                    exit(0)
            return False
        return True

    #This function checks if file exists on hard disk
    def checkFileExistsOnHardDisk(self, hostName, fileName):
        resp = subprocess.call( ['ssh',"-o", "StrictHostKeyChecking=no","-o","BatchMode=yes", hostName, 'test -e ' + pipes.quote(fileName)])
        if resp == 0:
            return True
        else:
            return False

    #This function creates a folder on remote machine
    def createFolderOnHardDisk(self, hostName, folder, flag = False):
        prog = subprocess.Popen( ['ssh',"-o", "StrictHostKeyChecking=no","-o","BatchMode=yes", hostName, \
                                "mkdir","-p", folder], stderr=subprocess.PIPE)
        errdata = prog.communicate()[1].decode()
        if prog.returncode and errdata != "":
            data = "Error in operation:"+errdata
            print(data)
            if flag:
                if self.mySocket:
                    self.mySocket.send(data.encode())
                else:
                    exit(0)
            return False
        return True

    #This function deletes file from specified disk
    def deleteFilesFromHardDisk(self, disk, fileName, flag=True):
        prog = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", loginName+"@"+disk,\
                                "rm", fileName], stderr=subprocess.PIPE)
        errdata = prog.communicate()[1].decode()
        print (errdata)
        if prog.returncode and errdata != "":
            if flag:
                data = "Error in operation: Error deleting file"
                self.conn.send(data.encode())
            return False
        return True

    def hashingData(self, message):
        key = hashlib.md5(message.encode('utf-8')).hexdigest()
        return key
