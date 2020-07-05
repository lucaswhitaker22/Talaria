from blocksim.models.permissioned_node import Node
from blocksim.models.pbft_network import Network
from blocksim.models.chain import Chain
from blocksim.models.consensus import Consensus
from blocksim.models.db import BaseDB
from blocksim.models.transaction_queue import TransactionQueue
from blocksim.utils import time, get_random_values
from blocksim.models.block import Block, BlockHeader
from blocksim.models.pbft.message import Message
from collections import defaultdict


class PBFTNode(Node):

    def __init__(self,
                 env,
                 network: Network,
                 location: str,
                 address: str,
                 replica_id, 
                 is_authority=False,
                 ):
        # Jiali: This function is borrowed from ethereum/node.py, without any change actually.
        # Create the PoA genesis block and init the chain
        genesis = Block(BlockHeader())
        consensus = Consensus(env)
        chain = Chain(env, self, consensus, genesis, BaseDB())
        # TODO: determine f (#malicious_nodes) outside this file
        self.f = 3
        self.is_authority = is_authority
        super().__init__(env,
                         network,
                         location,
                         address,
                         chain,
                         consensus,
                         is_authority)
        self.temp_headers = {}
        self.network_message = Message(self)
        if is_authority:
            self.current_view = 0
            self.current_sequence = 0
            # Transaction Queue to store the transactions
            self.transaction_queue = TransactionQueue(
                env, self, self.consensus)
        self._handshaking = env.event()
        self.replica_id = replica_id
        # Jiali: a dict for logging msg/prepare/commit
        self.log = {
            'block': {},
            'prepare': defaultdict(set),
            'prepared': defaultdict(bool),
            'committed': defaultdict(bool),
        }

    def build_new_block(self):
        """Builds a new candidate block and propagate it to the network

        Jiali: This function is borrowed from bitcoin/node.py, without too much change."""
        if self.is_authority is False:
            raise RuntimeError(f'Node {self.location} is not a authority')
        block_size = self.env.config['poa']['block_size_limit_mb']
        transactions_per_block_dist = self.env.config[
            'poa']['number_transactions_per_block']
        transactions_per_block = int(
            get_random_values(transactions_per_block_dist)[0])
        pending_txs = []
        tx_left = True
        for i in range(transactions_per_block * block_size):
            if self.transaction_queue.is_empty():
                print(
                    f'{self.address} at {time(self.env)}: No more transactions queued.')
                # Jiali: stop simulation when tx are done, in order to know whether/when it happens
                # raise Exception('TX all processed')
                tx_left = False
                break
            pending_tx = self.transaction_queue.get()
            pending_txs.append(pending_tx)
        candidate_block = self._build_candidate_block(pending_txs)
        print(
            f'{self.address} at {time(self.env)}: New candidate block #{candidate_block.header.number} created {candidate_block.header.hash[:8]} with difficulty {candidate_block.header.difficulty}')
        # Add the candidate block to the chain of the authority node
        self.chain.add_block(candidate_block)
        # We need to broadcast the new candidate block across the network
        self.broadcast_pre_prepare([candidate_block])
        return tx_left

    def _build_candidate_block(self, pending_txs):
        # Jiali: This function is borrowed from bitcoin/node.py, without any change actually.
        # Get the current head block
        prev_block = self.chain.head
        coinbase = self.address
        timestamp = self.env.now
        difficulty = self.consensus.calc_difficulty(prev_block, timestamp)
        block_number = prev_block.header.number + 1
        candidate_block_header = BlockHeader(
            prev_block.header.hash,
            block_number,
            timestamp,
            coinbase,
            difficulty)
        return Block(candidate_block_header, pending_txs)

    def _read_envelope(self, envelope):
        # Jiali: This function is borrowed from ethereum/node.py, with minor changes.
        super()._read_envelope(envelope)
        if envelope.msg['id'] == 'status':
            self._receive_status(envelope)
            # Only do these if you are authority
            if self.is_authority:
                if envelope.msg['id'] == 'pre-prepare':
                    self._receive_pre_prepare(envelope)
                if envelope.msg['id'] == 'transactions':
                    self._receive_full_transactions(envelope)
                if envelope.msg['id'] == 'prepare':
                    self._receive_prepare(envelope)
                if envelope.msg['id'] == 'commit':
                    self._receive_commit(envelope)

    ##              ##
    ## Handshake    ##
    ##              ##

    def connect(self, nodes: list):
        super().connect(nodes)
        for node in nodes:
            self._handshake(node.address)

    def _handshake(self, destination_address: str):
        """Handshake inform a node of its current ethereum state, negotiating network, difficulties,
        head and genesis blocks
        This message should be sent after the initial handshake and prior to any ethereum related messages."""
        status_msg = self.network_message.status()
        print(
            f'{self.address} at {time(self.env)}: Status message sent to {destination_address}')
        self.env.process(self.send(destination_address, status_msg))

    def _receive_status(self, envelope):
        print(
            f'{self.address} at {time(self.env)}: Receive status from {envelope.origin.address}')
        node = self.active_sessions.get(envelope.origin.address)
        node['status'] = envelope.msg
        self.active_sessions[envelope.origin.address] = node
        self._handshaking.succeed()
        self._handshaking = self.env.event()

    ##              ##
    ## Transactions ##
    ##              ##

    def broadcast_transactions(self, transactions: list):
        """Broadcast transactions to all nodes with an active session and mark the hashes
        as known by each node"""
        yield self.connecting  # Wait for all connections
        yield self._handshaking  # Wait for handshaking to be completed
        for node_address, node in self.active_sessions.items():
            for tx in transactions:
                # Checks if the transaction was previous sent
                if any({tx.hash} & node.get('knownTxs')):
                    print(
                        f'{self.address} at {time(self.env)}: Transaction {tx.hash[:8]} was already sent to {node_address}')
                    transactions.remove(tx)
                else:
                    self._mark_transaction(tx.hash, node_address)
        # Only send if it has transactions
        if transactions:
            print(
                f'{self.address} at {time(self.env)}: {len(transactions)} transactions ready to be sent')
            transactions_msg = self.network_message.transactions(transactions)
            self.env.process(self.broadcast(transactions_msg))

    def _receive_full_transactions(self, envelope):
        """Handle full tx received. If node is authority store transactions in a pool (ordered by the gas price)"""
        transactions = envelope.msg.get('transactions')
        valid_transactions = []
        for tx in transactions:
            if self.is_authority:
                self.transaction_queue.put(tx)
            else:
                valid_transactions.append(tx)
        # self.env.process(self.broadcast_transactions(valid_transactions))

    ##              ##
    ## Blocks       ##
    ##              ##

    def broadcast_pre_prepare(self, new_blocks: list):
        # Jiali: Here I renamed broadcast_new_blocks to broadcast_pre_prepare......
        """Specify one or more new blocks which have appeared on the network.
        To be maximally helpful, nodes should inform peers of all blocks that
        they may not be aware of."""
        new_blocks_hashes = {}
        for block in new_blocks:
            new_blocks_hashes[block.header.hash] = block.header

        block_bodies = {}
        for block_hash in new_blocks_hashes:
            block = self.chain.get_block(block_hash)
            block_bodies[block.header.hash] = block.transactions

        new_blocks_msg = self.network_message.pre_prepare(new_blocks_hashes, block_bodies)
        # TODO: only broadcast to authorities!
        self.env.process(self.broadcast(new_blocks_msg))

    def _receive_pre_prepare(self, envelope):
        new_blocks = envelope.msg['new_blocks']
        block_bodies = envelope.msg.get('block_bodies')

        print(f'{self.address} at {time(self.env)}: In pre-prepare phase, new blocks received {new_blocks}')
        # If the block is already known by a node, it does not need to prepare again.
        block_numbers = []
        for block_hash, block_header in new_blocks.items():
            if self.chain.get_block(block_hash) is None:
                block_numbers.append(block_header.number)
                self._send_prepare()
                # Jiali: store the block in the log for future commit
                new_block = Block(block_header, block_bodies[block_hash])
                self.log['block'][block_hash] = new_block

    def _send_prepare(self):
        # Send prepare
        # TODO: add attributes to prepare msg, a PREPARE should have <v, n, d, i>,
        #  where the seqno should be attached to block not per node! (so can not be self.seqno?)
        print(
            f'{self.address} at {time(self.env)}: Prepare prepared to multicast.')
        prepare_msg = self.network_message.prepare()
        self.env.process(self.broadcast(prepare_msg))

    def _receive_prepare(self, envelope):
        """Handle prepare received"""
        seqno = envelope.msg.get('seqno')
        self.log['prepare'][seqno].add(envelope.origin.address)
        if len(self.log['prepare'][seqno]) >= 2*self.f:
            self.log['prepared'][seqno] = True
            self._send_commit()

    def _send_commit(self):
        """Request a node (identified by the `destination_address`) to return block bodies.
        Specify a list of `hashes` that we're interested in.
        """
        commit_msg = self.network_message.commit()
        self.env.process(self.broadcast(commit_msg))

    def _receive_commit(self, envelope):
        """Handle block bodies received
        Assemble the block header in a temporary list with the block body received and
        insert it in the blockchain"""
        seqno = envelope.msg.get('seqno')
        if self.log['prepared'][seqno] and self.log['committed'][seqno]:
            # TODO: retrive the block from log['block']
            #  but how? Can it be done with only the seqno?
            self.chain.add_block(new_block)
            print(
                f'{self.address} at {time(self.env)}: Block assembled and added to the tip of the chain  {new_block.header}')
