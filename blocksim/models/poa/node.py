from blocksim.models.permissioned_node import PermNode as Node
from blocksim.models.permissioned_network import Network
from blocksim.models.chain import Chain
from blocksim.models.consensus import Consensus
from blocksim.models.db import BaseDB
from blocksim.models.permissoned_transaction_queue import TransactionQueue
from blocksim.utils import time, get_random_values
from blocksim.models.block import Block, BlockHeader
from blocksim.models.poa.message import Message


class POANode(Node):

    def __init__(self,
                 env,
                 network: Network,
                 location: str,
                 address: str,
                 is_authority=False,
                 verbose=False):
        # Jiali: This function is borrowed from ethereum/node.py, without any change actually.
        # Create the PoA genesis block and init the chain
        genesis = Block(BlockHeader())
        consensus = Consensus(env)
        chain = Chain(env, self, consensus, genesis, BaseDB())
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
            # Transaction Queue to store the transactions
            self.transaction_queue = TransactionQueue(
                env, self, self.consensus)
        self._handshaking = env.event()

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
                if self.verbose:
                    print(
                        f'{self.address} at {time(self.env)}: No more transactions queued.')
                # Jiali: stop simulation when tx are done, in order to know whether/when it happens
                if i == 0:
                    tx_left = False
                break
            pending_tx = self.transaction_queue.get()
            pending_txs.append(pending_tx)
        candidate_block = self._build_candidate_block(pending_txs)
        if self.verbose:
            print(
                f'{self.address} at {time(self.env)}: New candidate block #{candidate_block.header.number} created {candidate_block.header.hash[:8]} with difficulty {candidate_block.header.difficulty}')
        # Add the candidate block to the chain of the authority node
        self.chain.add_block(candidate_block)
        # We need to broadcast the new candidate block across the network
        self.broadcast_new_blocks([candidate_block])
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
        # Jiali: This function is borrowed from ethereum/node.py, without any change actually.
        super()._read_envelope(envelope)
        if envelope.msg['id'] == 'status':
            self._receive_status(envelope)
        if envelope.msg['id'] == 'new_blocks':
            self._receive_new_blocks(envelope)
        if envelope.msg['id'] == 'transactions':
            self._receive_full_transactions(envelope)
        if envelope.msg['id'] == 'get_headers':
            self._send_block_headers(envelope)
        if envelope.msg['id'] == 'block_headers':
            self._receive_block_headers(envelope)
        if envelope.msg['id'] == 'get_block_bodies':
            self._send_block_bodies(envelope)
        if envelope.msg['id'] == 'block_bodies':
            self._receive_block_bodies(envelope)

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
        if self.verbose:
            print(
                f'{self.address} at {time(self.env)}: Status message sent to {destination_address}')
        self.env.process(self.send(destination_address, status_msg))

    def _receive_status(self, envelope):
        if self.verbose:
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
        # yield self._handshaking  # Wait for handshaking to be completed
        for node_address, node in self.active_sessions.items():
            for tx in transactions:
                # Checks if the transaction was previous sent
                if any({tx.hash} & node.get('knownTxs')):
                    if self.verbose:
                        print(
                            f'{self.address} at {time(self.env)}: Transaction {tx.hash[:8]} was already sent to {node_address}')
                    transactions.remove(tx)
                else:
                    self._mark_transaction(tx.hash, node_address)
        # Only send if it has transactions
        if transactions:
            if self.verbose:
                print(
                    f'{self.address} at {time(self.env)}: {len(transactions)} transactions ready to be sent')
            transactions_msg = self.network_message.transactions(transactions)
            # Jiali: I think node should also add tx to their own queue before they broadcast the txs
            if self.is_authority:
                self.transaction_queue.add_txs(transactions)
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

    def broadcast_new_blocks(self, new_blocks: list):
        """Specify one or more new blocks which have appeared on the network.
        To be maximally helpful, nodes should inform peers of all blocks that
        they may not be aware of."""
        new_blocks_hashes = {}
        for block in new_blocks:
            new_blocks_hashes[block.header.hash] = block.header.number
        new_blocks_msg = self.network_message.new_blocks(new_blocks_hashes)
        self.env.process(self.broadcast(new_blocks_msg))

    def _receive_new_blocks(self, envelope):
        """Handle new blocks received.
        The destination only receives the hash and number of the block. It is needed to
        ask for the header and body.
        If node is a authority, we need to interrupt the current candidate block mining process"""
        new_blocks = envelope.msg['new_blocks']
        if self.verbose:
            print(f'{self.address} at {time(self.env)}: New blocks received {new_blocks}')
        # If the block is already known by a node, it does not need to request the block again
        block_numbers = []
        for block_hash, block_number in new_blocks.items():
            if self.chain.get_block(block_hash) is None:
                block_numbers.append(block_number)
        lowest_block_number = min(block_numbers)
        self.request_headers(
            lowest_block_number, len(new_blocks), envelope.origin.address)

    def request_headers(self, block_number: int, max_headers: int, destination_address: str):
        """Request a node (identified by the `destination_address`) to return block headers.
        At most `max_headers` items.
        """
        get_headers_msg = self.network_message.get_headers(
            block_number, max_headers)
        self.env.process(self.send(destination_address, get_headers_msg))

    def _send_block_headers(self, envelope):
        """Send block headers for any node that request it, identified by the `destination_address`"""
        block_number = envelope.msg.get('block_number', 0)
        max_headers = envelope.msg.get('max_headers', 1)
        block_hash = self.chain.get_blockhash_by_number(block_number)
        block_hashes = self.chain.get_blockhashes_from_hash(
            block_hash, max_headers)
        block_headers = []
        for _block_hash in block_hashes:
            block_header = self.chain.get_block(_block_hash).header
            block_headers.append(block_header)
        if self.verbose:
            print(
                f'{self.address} at {time(self.env)}: {len(block_headers)} Block header(s) preapred to send')
        block_headers_msg = self.network_message.block_headers(block_headers)
        self.env.process(self.send(envelope.origin.address, block_headers_msg))

    def _receive_block_headers(self, envelope):
        """Handle block headers received"""
        block_headers = envelope.msg.get('block_headers')
        # Save the header in a temporary list
        hashes = []
        for header in block_headers:
            self.temp_headers[header.hash] = header
            hashes.append(header.hash)
        self.request_bodies(hashes, envelope.origin.address)

    def request_bodies(self, hashes: list, destination_address: str):
        """Request a node (identified by the `destination_address`) to return block bodies.
        Specify a list of `hashes` that we're interested in.
        """
        get_block_bodies_msg = self.network_message.get_block_bodies(hashes)
        self.env.process(self.send(destination_address, get_block_bodies_msg))

    def _send_block_bodies(self, envelope):
        """Send block bodies for any node that request it, identified by the `envelope.origin.address`.

        In `envelope.msg.hashes` we obtain a list of hashes of block bodies being requested.
        """
        block_bodies = {}
        for block_hash in envelope.msg.get('hashes'):
            block = self.chain.get_block(block_hash)
            block_bodies[block.header.hash] = block.transactions
        if self.verbose:
            print(
                f'{self.address} at {time(self.env)}: {len(block_bodies)} Block bodies(s) preapred to send')
        block_bodies_msg = self.network_message.block_bodies(block_bodies)
        self.env.process(self.send(envelope.origin.address, block_bodies_msg))

    def _receive_block_bodies(self, envelope):
        """Handle block bodies received
        Assemble the block header in a temporary list with the block body received and
        insert it in the blockchain"""
        block_hashes = []
        block_bodies = envelope.msg.get('block_bodies')
        for block_hash, block_txs in block_bodies.items():
            block_hashes.append(block_hash[:8])
            if block_hash in self.temp_headers:
                header = self.temp_headers.get(block_hash)
                new_block = Block(header, block_txs)
                if self.chain.add_block(new_block):
                    # Jiali: now we are ready to remove from queue all the txs received from new block.
                    if self.is_authority:
                        self.transaction_queue.remove_txs(block_txs)

                    del self.temp_headers[block_hash]
                    if self.verbose:
                        print(
                            f'{self.address} at {time(self.env)}: Block assembled and added to the tip of the chain  {new_block.header}')
