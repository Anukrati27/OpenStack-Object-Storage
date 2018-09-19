import socket
import ClientHandler
import GlobalVars
import HeartBeat

#Server class listens for client requests and create a separate thread to handle each client
class Server:

    def __init__(self):
        self.host = socket.gethostname()
        self.port = 0
        self.mySocket = None
        #for mapping hostname and ip address
        for key, value in GlobalVars.indexToHardDiskMap.items():
            GlobalVars.indexToHardDiskMap[key] = socket.gethostbyname(value)

    def startServer(self):
        try:
            self.mySocket = socket.socket()
            self.mySocket.bind((self.host,self.port))
            heartBeatChecker = HeartBeat.HeartBeat(1, "HeartBeatChecker")
            heartBeatChecker.daemon = True
            heartBeatChecker.start()
            print ("Please connect to server at: ",self.mySocket.getsockname())
            counter = 0
            while 1:
                self.mySocket.listen(1)
                conn, addr = self.mySocket.accept()
                print ("Connection from: " + str(addr) + "---> Thread-" + str(counter))
                clientHandler = ClientHandler.ClientHandler(counter+2, "Thread-"+str(counter), conn)
                clientHandler.daemon = True
                counter = counter+1
                clientHandler.start()
        except KeyboardInterrupt:
            print("\nServer Closed Successfully.\n")
            exit(0)
        except Exception as e:
            print ("Error in Running Server " + str(e))
            exit(0)

    def __del__(self):
        self.mySocket.close()
