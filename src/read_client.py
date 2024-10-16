# read_client.py
import grpc
import sys
import proxy_db_comm_pb2
import proxy_db_comm_pb2_grpc

def send_read_request(node_address, id):
    with grpc.insecure_channel(node_address) as channel:
        stub = proxy_db_comm_pb2_grpc.ProxyDatabaseCommunicationStub(channel)
        request = proxy_db_comm_pb2.ReadRequest(id=id)
        response = stub.ReadData(request)
        if response.status == proxy_db_comm_pb2.OK:
            print(f'Data at ID {id}: {response.data}')
        else:
            print(f'Error: {response.error}')

if __name__ == '__main__':
    node_address = sys.argv[1]  # e.g., 'localhost:5001'
    id = int(sys.argv[2])
    send_read_request(node_address, id)
