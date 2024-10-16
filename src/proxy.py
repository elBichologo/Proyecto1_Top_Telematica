import grpc
from concurrent import futures
import proxy_db_comm_pb2
import proxy_db_comm_pb2_grpc
import client_proxy_comm_pb2
import client_proxy_comm_pb2_grpc
import os

class ProxyDatabaseCommunicationServicer(proxy_db_comm_pb2_grpc.ProxyDatabaseCommunicationServicer):
    def __init__(self, leader_address, follower_addresses):
        self.leader_address = leader_address
        self.follower_addresses = follower_addresses
        self.follower_index = 0

    def ChangeLeader(self, request, context):
        with grpc.insecure_channel(self.leader_address) as channel:
            stub = proxy_db_comm_pb2_grpc.ProxyDatabaseCommunicationStub(channel)
            response = stub.ChangeLeader(request)
        return response

    def SendLogEntry(self, request, context):
        with grpc.insecure_channel(self.leader_address) as channel:
            stub = proxy_db_comm_pb2_grpc.ProxyDatabaseCommunicationStub(channel)
            response = stub.SendLogEntry(request)
        return response

    def ReadData(self, request, context):
        follower_address = self.follower_addresses[self.follower_index]
        self.follower_index = (self.follower_index + 1) % len(self.follower_addresses)
        try:
            with grpc.insecure_channel(follower_address) as channel:
                stub = proxy_db_comm_pb2_grpc.ProxyDatabaseCommunicationStub(channel)
                response = stub.ReadData(request)
            # Check if the response status is FAILED, return specific error message
            if response.status == proxy_db_comm_pb2.Status.FAILED:
                return client_proxy_comm_pb2.ReadResponse(
                    status=client_proxy_comm_pb2.ReadResponse.Status.FAILED,
                    data="",
                    error=f"Nodo seguidor en {follower_address} no pudo leer el archivo"
                )
            return client_proxy_comm_pb2.ReadResponse(
                status=client_proxy_comm_pb2.ReadResponse.Status.OK,
                data=response.data,
                error=""
            )
        except grpc.RpcError as e:
            # Log the error and return a FAILED status
            return client_proxy_comm_pb2.ReadResponse(
                status=client_proxy_comm_pb2.ReadResponse.Status.FAILED,
                data="",
                error=f"Error de conexión con el nodo en {follower_address}: {e}"
            )
        
    def process_request(self, operation, value):
        try:
            response = self.apply_entry(operation, value)
            return response
        except Exception as e:
            return f"Error processing request: {e}"


class ClientProxyCommunicationServicer(client_proxy_comm_pb2_grpc.ClientProxyCommunicationServicer):
    def __init__(self, proxy_servicer):
        self.proxy_servicer = proxy_servicer

    def WriteData(self, request, context):
        log_entry = proxy_db_comm_pb2.LogEntry(log=request.log)
        response = self.proxy_servicer.SendLogEntry(log_entry, context)
        return client_proxy_comm_pb2.Confirmation(status=response.status, error=response.error)

    def ReadData(self, request, context):
        read_request = proxy_db_comm_pb2.ReadRequest(id=request.id)
        response = self.proxy_servicer.ReadData(read_request, context)
        return client_proxy_comm_pb2.ReadResponse(status=response.status, data=response.data, error=response.error)

def serve():
    leader_address = '127.0.0.1:5003'  # Replace with actual leader address
    follower_addresses = ['127.0.0.1:5001', '127.0.0.1:5002']  # Replace with actual follower addresses

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    proxy_servicer = ProxyDatabaseCommunicationServicer(leader_address, follower_addresses)
    proxy_db_comm_pb2_grpc.add_ProxyDatabaseCommunicationServicer_to_server(proxy_servicer, server)
    client_proxy_comm_pb2_grpc.add_ClientProxyCommunicationServicer_to_server(ClientProxyCommunicationServicer(proxy_servicer), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()