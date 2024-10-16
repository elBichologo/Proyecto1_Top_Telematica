import grpc
import client_proxy_comm_pb2
import client_proxy_comm_pb2_grpc

def write_data(stub, log):
    request = client_proxy_comm_pb2.WriteRequest(log=log)
    response = stub.WriteData(request)
    print(f"WriteData response: {response.status}, {response.error}")

def read_data(stub, id):
    request = client_proxy_comm_pb2.ReadRequest(id=id)
    response = stub.ReadData(request)
    print(f"ReadData response: {response.status}, {response.data}, {response.error}")

def main():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = client_proxy_comm_pb2_grpc.ClientProxyCommunicationStub(channel)
        
        while True:
            action = input("Enter 'write' to write data or 'read' to read data (or 'exit' to quit): ").strip().lower()
            if action == 'write':
                log = input("Enter the log entry to write: ").strip()
                write_data(stub, log)
            elif action == 'read':
                id = int(input("Enter the ID to read: ").strip())
                read_data(stub, id)
            elif action == 'exit':
                break
            else:
                print("Invalid input. Please enter 'write', 'read', or 'exit'.")

if __name__ == '__main__':
    main()