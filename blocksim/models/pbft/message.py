from blocksim.utils import kB_to_MB
from blocksim.models.pbft_network import MaliciousModel

class Message:
    # Jiali: Copied from Ethereum
    # Defines a model for the network messages of the PBFT blockchain.

    def __init__(self, origin_node):
        self.origin_node = origin_node
        _env = origin_node.env
        self._message_size = _env.config['pbft']['message_size_kB']

        # Digest is 1 meaning correct/valid, 0 is malicious and modified/invalid message.
        self.digest = 0 if self.origin_node.is_malicious == MaliciousModel.ACTIVE else 1

    def status(self):
        """ Inform a peer of its current PoA state.
        This message should be sent `after` the initial handshake and `prior` to any PoA related messages.
        """
        return {
            'id': 'status',
            'protocol_version': 'ONE',
            'network': self.origin_node.network.name,
            'td': self.origin_node.chain.head.header.difficulty,
            'best_hash': self.origin_node.chain.head.header.hash,
            'genesis_hash': self.origin_node.chain.genesis.header.hash,
            'size': kB_to_MB(self._message_size['status'])
        }

    def transactions(self, transactions: list):
        """ Specify (a) transaction(s) that the peer should make sure is included on its
        transaction queue. Nodes must not resend the same transaction to a peer in the same session.
        This packet must contain at least one (new) transaction.
        """
        num_txs = len(transactions)
        transactions_size = num_txs * self._message_size['tx']
        return {
            'id': 'transactions',
            'transactions': transactions,
            'size': kB_to_MB(transactions_size)
        }
    
    # Ryan: Reformat messages to hold info
    def pre_prepare(self, seqno, new_blocks: dict, block_bodies: dict, new_view):
        # Jiali: pre-prepare should be similar to newblock, so I migrate newblock to here.
        """Advertises one or more new blocks which have appeared on the network"""
        # Jiali: we can use the number of last block in one message (assume multiple blocks in one pre-prepare is
        # possible) as seqno!

        if new_view:
            
            return {
                'id': 'pre-prepare',
                'view': self.origin_node.network.view + 1,
                'seqno': seqno,
                'digest': self.digest,
                'new_blocks': new_blocks,
                'block_bodies': block_bodies,
                'size': kB_to_MB(self._message_size['tx'])
                }
        else:
            
            num_new_block_hashes = len(new_blocks)
            new_blocks_size = num_new_block_hashes * \
                          self._message_size['hash_size']

            txsCount = 0
            for block_hash, block_txs in block_bodies.items():
                txsCount += len(block_txs)
            message_size = (txsCount * self._message_size['tx']) + self._message_size['block_bodies']
            return {
                'id': 'pre-prepare',
                'view': self.origin_node.network.view,
                'seqno': seqno,
                'digest': self.digest,
                'new_blocks': new_blocks,
                'block_bodies': block_bodies,
                'size': kB_to_MB(message_size+new_blocks_size)
                }
    
    def prepare(self, seqno):

        return {
            'id': 'prepare',
            'view': self.origin_node.network.view,
            'seqno': seqno,
            'digest': self.digest,
            'replica_id': self.origin_node.replica_id,
            'size': kB_to_MB(self._message_size['prepare'])
        }
    
    # Originally copied from "block_bodies()" in the ETH version of message.py
    def commit(self, seqno):

        return {
            'id': 'commit',
            'view': self.origin_node.network.view,
            'seqno': seqno,
            'digest': self.digest,
            'replica_id': self.origin_node.replica_id,
            'size': kB_to_MB(self._message_size['commit'])
        }
    
    def client_reply(self, new_block):
        return {
            'id': 'reply',
            'view': self.origin_node.network.view,
            'timestamp': new_block.header.timestamp,  
            'client': self.origin_node.network.view % len(self.origin_node.network._list_authority_nodes), 
            'replica_id': self.origin_node.replica_id,  
            'result': new_block,
            'size': kB_to_MB(self._message_size['reply']) #TODO: Will need to add block size
        }

    def checkpoint(self, seqno, replica_id):

        return {
            'id': 'checkpoint',
            'seqno': seqno,
            'digest': self.digest,
            'replica_id': replica_id,
            'size': kB_to_MB(self._message_size['checkpoint'])
        }
    
    def view_change(self, ckpt_seqno, checkpoint_msg, prepare_msg):
        return {
           'id': "viewchange",
           'nextview': self.origin_node.network.view + 1,
           'checkpoint_seqno': ckpt_seqno,
           'checkpoint_messages': checkpoint_msg,
           'prepare_messages': prepare_msg,
           'replica_id': self.origin_node.replica_id,
           'size': kB_to_MB(self._message_size['viewchange_base']) + (len(checkpoint_msg) * kB_to_MB(self._message_size['checkpoint'])) + \
            (len(prepare_msg) * kB_to_MB(self._message_size['prepare']))
            }
    
    def new_view(self, viewchange_msg, preprepare_msg):
        # Jiali: the following line is redundant as per line 425 in node.py: self.network.view += 1
        # self.origin_node.network.view = self.origin_node.network.view + 1
        return {
            'id': "newview",
            'newview': self.origin_node.network.view + 1,
            'viewchange_messages': viewchange_msg,
            'preprepare_messages': preprepare_msg,
            'size': kB_to_MB(self._message_size['newview_base']) + (len(viewchange_msg) * kB_to_MB(self._message_size['viewchange_base'])) + \
            (len(preprepare_msg) * kB_to_MB(self._message_size['tx']))
            }