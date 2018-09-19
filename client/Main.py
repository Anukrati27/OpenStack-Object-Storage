import Client
import sys
import time

#help function to understand the command structure
def help():
    print("\n*************************************************")
    print("download <user/object> - to download an object")
    print("list <user>            - display the user objects")
    print("upload <user/object>   - uplod file to server")
    print("delete <user/object>   - delete the object")
    print("add <disk>             - add a new disk")
    print("remove <disk>          - remove a disk")
    print("*************************************************")

#Main function, It starts the client and then continue processing messages sent by user.
if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            print ("Please Provide input in this form: ")
            print ("python Main.py ip-address port")
            exit(0)
        host = sys.argv[1]
        port = int(sys.argv[2])
        client = Client.Client(host, port)
        client.startClient()
        print("\n    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        print("    Welcome To Programming Assignment 2")
        print("    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        while 1:
            print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            command = input("Please Enter a command[type 'help' for help or 'quit' to exit]:")
            if( command.lower() == "help" ):
                help()
            else:
                client.sendMessage(command)
            if( command.lower() == "quit"):
                print ("Client exited successfully!!!")
                exit(1)
    except Exception as e:
        print("Error in running client: ", str(e))
        exit(0)
