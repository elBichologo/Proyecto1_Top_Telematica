# src/node.py
import os

import grpc
from concurrent import futures
import threading
import time
import random
import logging
import json

# Import generated classes
import db_comm_pb2
import db_comm_pb2_grpc
import proxy_db_comm_pb2_grpc
import proxy_db_comm_pb2


class Node(db_comm_pb2_grpc.ProxyDatabaseCommunicationServicer,
           proxy_db_comm_pb2_grpc.ProxyDatabaseCommunicationServicer):
    def __init__(self, node_id, peers, data_file):
        self.actual_operations = ['W', 'D', 'U']
        self.node_id = node_id
        self.peers = peers  # List of peer addresses
        self.data_file = data_file
        self.current_term = 0
        self.voted_for = None
        self.log = []
        self.commit_index = 0
        self.last_applied = 0
        self.state = 'Follower'  # 'Follower', 'Candidate', or 'Leader'
        self.leader = None
        self.election_timeout = self.reset_election_timeout()
        self.last_heartbeat = time.time()
        self.lock = threading.Lock()

        # Setup logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(f'Node{self.node_id}')

        self.load_state()
        self.load_log()
        self.recover_state_machine()

        # Start gRPC server
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        db_comm_pb2_grpc.add_ProxyDatabaseCommunicationServicer_to_server(self, self.server)
        proxy_db_comm_pb2_grpc.add_ProxyDatabaseCommunicationServicer_to_server(self, self.server)
        self.server.add_insecure_port(f'[::]:{self.node_id}')
        self.server.start()

        self.logger.info(f'Server started at port {self.node_id}')

        # Start background threads
        threading.Thread(target=self.run_election_timer, daemon=True).start()

    def reset_election_timeout(self):
        return time.time() + random.uniform(5, 10)

    def run_election_timer(self):
        while True:
            time.sleep(0.1)
            if self.state != 'Leader' and time.time() >= self.election_timeout:
                self.logger.info('Election timeout reached, starting election')
                self.start_election()

    def start_election(self):
        with self.lock:
            self.state = 'Candidate'
            self.current_term += 1
            self.voted_for = self.node_id
            self.persist_state()
            self.election_timeout = self.reset_election_timeout()
            self.logger.info(f'Starting election for term {self.current_term}')

        votes_received = 1  # Vote for self
        total_peers = len(self.peers)

        def send_request_vote(peer):
            nonlocal votes_received
            try:
                with grpc.insecure_channel(peer) as channel:
                    stub = db_comm_pb2_grpc.ProxyDatabaseCommunicationStub(channel)
                    print()
                    request = db_comm_pb2.voteRequest(
                        term=self.current_term,
                        candidateId=int(self.node_id),
                        lastLogIndex=self.get_last_log_index(),
                        lastLogTerm=self.get_last_log_term()
                    )
                    response = stub.requestVote(request)
                    if response.voteGranted:
                        self.logger.debug(f'Received vote from {peer}')
                        votes_received += 1
                    else:
                        self.logger.debug(f'Vote denied by {peer}')
                        if response.term > self.current_term:
                            self.current_term = response.term
                            self.state = 'Follower'
                            self.persist_state()
            except grpc.RpcError as e:
                self.logger.error(f'RPC error when requesting vote from {peer}: {e}')

        threads = []
        for peer in self.peers:
            t = threading.Thread(target=send_request_vote, args=(peer,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        with self.lock:
            if self.state == 'Candidate' and votes_received > total_peers // 2:
                self.logger.info('Won election, becoming leader')
                self.state = 'Leader'
                self.leader_address = f'localhost:{self.node_id}'
                self.voted_for = None
                self.next_index = {peer: self.get_last_log_index() + 1 for peer in self.peers}
                self.match_index = {peer: 0 for peer in self.peers}
                # Start sending heartbeats
                threading.Thread(target=self.send_heartbeats, daemon=True).start()
            else:
                self.logger.info('Election lost or timed out, remaining follower')
                self.state = 'Follower'
                self.voted_for = None

    # Implement RPC methods
    def AppendEntries(self, request, context):
        with self.lock:
            response = db_comm_pb2.LogEntryAnswer(term=self.current_term)

            if request.term < self.current_term:
                response.success = False
                self.logger.debug('AppendEntries term is less than current term, rejecting')
                return response

            self.current_term = request.term
            self.persist_state()
            self.state = 'Follower'
            self.leader_address = f'localhost:{request.leaderId}'
            self.election_timeout = self.reset_election_timeout()
            self.last_heartbeat = time.time()

            # Check if log contains an entry at prevLogIndex with term matching prevLogTerm
            if request.prevLogIndex >= 0 and (len(self.log) <= request.prevLogIndex or self.log[request.prevLogIndex][
                'term'] != request.prevLogTerm):
                response.success = False
                self.logger.debug('Log inconsistency detected, rejecting AppendEntries')
                return response

            # Append any new entries not already in the log
            index = request.prevLogIndex + 1
            for entry_json in request.entries:
                entry = json.loads(entry_json)  # Convert string back to dictionary
                if len(self.log) > index and self.log[index]['term'] != entry['term']:
                    # Delete the existing entry and all that follow it
                    self.log = self.log[:index]
                    self.persist_log()
                    self.logger.debug('Conflict in log, truncating log from index {}'.format(index))
                if len(self.log) == index:
                    self.log.append(entry)
                    self.persist_log()

                index += 1

            # Update commit index
            if request.leaderCommit > self.commit_index:
                self.commit_index = min(request.leaderCommit, len(self.log) - 1)
                self.apply_entries()
                self.persist_state()

            response.success = True
            return response

    def apply_entries(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self.apply_entry(entry)
            self.persist_state()

    def apply_entry(self, entry):
        entry = None  # Inicializar entry
        try:
            if operation == "W":
                # Operación de escritura
                with open(self.log_file_path, 'a') as file:
                    entry = f"{value}\n"
                    file.write(entry)
                return "Write successful"

            elif operation == "D":
                # Operación de eliminación
                index = int(value)  # Convierte value a índice
                with open(self.log_file_path, 'r') as file:
                    lines = file.readlines()

                if 0 <= index < len(lines):
                    entry = lines[index]  # Definir entry antes de borrar
                    lines[index] = '\n'  # Opción de borrado
                    with open(self.log_file_path, 'w') as file:
                        file.writelines(lines)
                    return "Delete successful"
                else:
                    return "Index out of range"

            elif operation == "U":
                # Operación de actualización
                index, new_value = map(str.strip, value.split())
                index = int(index)
                with open(self.log_file_path, 'r') as file:
                    lines = file.readlines()

                if 0 <= index < len(lines):
                    entry = lines[index]  # Definir entry antes de actualizar
                    lines[index] = f"{new_value}\n"
                    with open(self.log_file_path, 'w') as file:
                        file.writelines(lines)
                    return "Update successful"
                else:
                    return "Index out of range"

            else:
                return "Unknown operation"

        except Exception as e:
            return f"Error: {e}"


    def requestVote(self, request, context):
        with self.lock:
            self.logger.debug(f'Received requestVote from {request.candidateId} for term {request.term}')
            response = db_comm_pb2.voteRequestAnswer(term=self.current_term)

            # If the term in the request is less than current term, reject the request
            if request.term < self.current_term:
                response.voteGranted = False
                self.logger.debug('Request term is less than current term, vote not granted')
                return response

            # If we haven't voted yet or voted for this candidate, and candidate's log is at least as up-to-date, grant vote
            up_to_date = (request.lastLogTerm > self.get_last_log_term()) or \
                         (
                                 request.lastLogTerm == self.get_last_log_term() and request.lastLogIndex >= self.get_last_log_index())

            if (self.voted_for is None or self.voted_for == request.candidateId) and up_to_date:
                self.voted_for = request.candidateId
                self.current_term = request.term
                self.persist_state()
                self.election_timeout = self.reset_election_timeout()
                response.voteGranted = True
                self.logger.debug('Vote granted to candidate')
            else:
                response.voteGranted = False
                self.logger.debug('Vote not granted')

            return response

    def get_last_log_index(self):
        return len(self.log) - 1

    def get_last_log_term(self):
        if self.log:
            return self.log[-1]['term']
        else:
            return 0

    def send_heartbeats(self):
        while self.state == 'Leader':
            for peer in self.peers:
                threading.Thread(target=self.replicate_log, args=(peer,), daemon=True).start()
            time.sleep(1)  # Heartbeat interval

    def replicate_log(self, peer):
        with self.lock:
            prev_log_index = self.next_index[peer] - 1
            prev_log_term = self.log[prev_log_index]['term'] if prev_log_index >= 0 else 0
            entries = self.log[self.next_index[peer]:]
            entries_json = [json.dumps(entry) for entry in entries]
            request = db_comm_pb2.LogEntry(
                term=self.current_term,
                leaderId=int(self.node_id),
                prevLogIndex=prev_log_index,
                prevLogTerm=prev_log_term,
                entries=entries_json,
                leaderCommit=self.commit_index
            )

        try:
            with grpc.insecure_channel(peer) as channel:
                stub = db_comm_pb2_grpc.ProxyDatabaseCommunicationStub(channel)
                response = stub.AppendEntries(request)
                with self.lock:
                    if response.success:
                        self.next_index[peer] = len(self.log)
                        self.match_index[peer] = self.next_index[peer] - 1
                    else:
                        self.next_index[peer] -= 1  # Decrement next_index and retry
        except grpc.RpcError as e:
            self.logger.error(f'RPC error when sending AppendEntries to {peer}: {e}')

    def SendLogEntry(self, request, context):

        with self.lock:
            if self.state != 'Leader':
                response = proxy_db_comm_pb2.Confirmation(
                    status=proxy_db_comm_pb2.FAILED,
                    error=f'Not the leader. Current leader is at {self.leader_address}'
                )
                return response
            else:
                # Verify if the command is valid
                try:
                    command = request.log.split(' ', 2)
                    if command[0] not in self.actual_operations or len(command) < 2:
                        # Error: operación o formato inválido
                        response = proxy_db_comm_pb2.Confirmation(
                            status=proxy_db_comm_pb2.FAILED,
                            error=f'The command should be between {self.actual_operations} and include an ID'
                        )
                        return response
                    try:
                        id = int(command[1])
                        if command[0] in ['W', 'U'] and len(command) < 3:
                            raise ValueError("Missing data for write or update command")
                    except ValueError as e:
                        response = proxy_db_comm_pb2.Confirmation(
                            status=proxy_db_comm_pb2.FAILED,
                            error=str(e)
                        )
                        return response
                    int(command[1])
                except Exception as e:
                    self.logger.error(f'Command {request.log} is not valid')
                    response = proxy_db_comm_pb2.Confirmation(
                        status=proxy_db_comm_pb2.FAILED,
                        error=str(e)
                    )
                    return response

                # Append the command to the log
                self.log.append(entry)
                self.persist_log()
                self.logger.debug(f'Appended new entry to log: {entry}')
                entry_index = len(self.log) - 1

                # Initialize replication state for the new entry
                self.match_index[self.node_id] = entry_index  # Leader's own match_index

        # Start the replication process
        self.replicate_new_entry(entry_index)

        try:
            # Asegúrate de definir entry aquí
            entry = request.entry  # O la asignación correcta según el valor recibido

            # Verifica y procesa entry como sea necesario
            self.log.append(entry)  # Almacena la entrada en el log del nodo
            return Response(status=1, message="Log entry appended")
        except Exception as e:
            return Response(status=0, message=f"Error: {e}")

        # Wait until the entry is committed
        while True:
            with self.lock:
                if self.commit_index >= entry_index:
                    break
            time.sleep(0.1)

        # Respond to the client
        response = proxy_db_comm_pb2.Confirmation(
            status=proxy_db_comm_pb2.OK,
            error=''
        )
        return response

    def replicate_new_entry(self, entry_index):
        for peer in self.peers:
            threading.Thread(target=self.send_append_entries, args=(peer,), daemon=True).start()

    def send_append_entries(self, peer):
        with self.lock:
            prev_log_index = self.next_index[peer] - 1
            prev_log_term = self.log[prev_log_index]['term'] if prev_log_index >= 0 else 0
            entries = self.log[self.next_index[peer]:]
            entries_json = [json.dumps(entry) for entry in entries]
            request = db_comm_pb2.LogEntry(
                term=self.current_term,
                leaderId=int(self.node_id),
                prevLogIndex=prev_log_index,
                prevLogTerm=prev_log_term,
                entries=entries_json,
                leaderCommit=self.commit_index
            )
        try:
            with grpc.insecure_channel(peer) as channel:
                stub = db_comm_pb2_grpc.ProxyDatabaseCommunicationStub(channel)
                response = stub.AppendEntries(request)
                with self.lock:
                    if response.success:
                        self.next_index[peer] = len(self.log)
                        self.match_index[peer] = self.next_index[peer] - 1
                        # Check if we can commit entries
                        self.update_commit_index()
                    else:
                        # Decrement next_index and retry
                        self.next_index[peer] = max(0, self.next_index[peer] - 1)
                        self.send_append_entries(peer)
        except grpc.RpcError as e:
            self.logger.error(f'RPC error when sending AppendEntries to {peer}: {e}')

    def update_commit_index(self):
        for index in range(len(self.log) - 1, self.commit_index, -1):
            count = 1  # Start with leader's own match
            for peer in self.peers:
                if self.match_index.get(peer, 0) >= index:
                    count += 1
            if count > (len(self.peers) + 1) // 2:
                self.commit_index = index
                self.apply_entries()
                self.persist_state()
                break

    def persist_state(self):
        state = {
            'current_term': self.current_term,
            'voted_for': self.voted_for,
            'commit_index': self.commit_index,
            'last_applied': self.last_applied
        }
        try:
            with open(f'state_{self.node_id}.json', 'w') as f:
                json.dump(state, f)
        except Exception as e:
            self.logger.error(f'Error persisting state: {e}')

    def load_state(self):
        try:
            with open(f'state_{self.node_id}.json', 'r') as f:
                state = json.load(f)
                self.current_term = state.get('current_term', 0)
                self.voted_for = state.get('voted_for', None)
                self.commit_index = state.get('commit_index', 0)
                self.last_applied = state.get('last_applied', -1)
        except FileNotFoundError:
            self.current_term = 0
            self.voted_for = None
            self.commit_index = 0
            self.last_applied = -1
        except Exception as e:
            self.logger.error(f'Error loading state: {e}')

    def persist_log(self):
        try:
            with open(f'log_{self.node_id}.json', 'w') as f:
                json.dump(self.log, f)
        except Exception as e:
            self.logger.error(f'Error persisting log: {e}')

    def load_log(self):
        try:
            with open(f'log_{self.node_id}.json', 'r') as f:
                self.log = json.load(f)
        except FileNotFoundError:
            self.log = []

    def ReadData(self, request, context):
        with self.lock:
        # Read the data from the file
            try:
                with open(self.data_file, 'r') as f:
                    lines = f.readlines()
                    index = request.id - 1  # Convert to 0-based index
                    if 0 <= index < len(lines):
                        data = lines[index].strip()
                        response = proxy_db_comm_pb2.ReadResponse(
                            status=proxy_db_comm_pb2.OK,
                            data=data,
                            error=''
                        )
                    else:
                        response = proxy_db_comm_pb2.ReadResponse(
                            status=proxy_db_comm_pb2.FAILED,
                            data='',
                            error='Data not found'
                        )
            except FileNotFoundError:
                response = proxy_db_comm_pb2.ReadResponse(
                    status=proxy_db_comm_pb2.FAILED,
                    data='',
                    error='File not found'
                )
            except Exception as e:
                response = proxy_db_comm_pb2.ReadResponse(
                    status=proxy_db_comm_pb2.FAILED,
                    data='',
                    error=str(e)
                )
        return response

    def recover_state_machine(self):
        if len(self.log) == 0: return
        # Load the data file into memory (if necessary)
        # Ensure that entries from last_applied + 1 to commit_index are applied
        for index in range(self.last_applied + 1, self.commit_index + 1):
            entry = self.log[index]
            self.apply_entry(entry)


if __name__ == '__main__':
    import sys

    node_id = sys.argv[1]
    peers = ["localhost:" + peer for peer in sys.argv[2:]]
    for peer in peers:
        print(peer)
    data_file = f'data/node_{node_id}.txt'
    node = Node(node_id=node_id, peers=peers, data_file=data_file)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.logger.info('Shutting down server')
        node.server.stop(0)
