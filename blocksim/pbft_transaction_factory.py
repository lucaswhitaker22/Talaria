import json
import string
from pathlib import Path
from random import choices, randint, random
import simpy
import numpy as np
from blocksim.utils import time
from blocksim.permissioned_transaction_factory import PermTransactionFactory
from blocksim.models.ethereum.transaction import Transaction as ETHTransaction
from blocksim.models.transaction import Transaction


class PBFTTransactionFactory(PermTransactionFactory):
    """ Responsible to create batches of random transactions. Depending on the blockchain
    being simulated, transaction factory will create transactions according to the
    transaction model. Moreover, the created transactions will be broadcasted when simulation
    is running by a random node on a list. Additionally, the user needs to specify the
    number of batches, number of transactions per batch and the interval in seconds between each batch.
    """

    def __init__(self, world):
        super().__init__(world)

    def broadcast(self, json_file_name, interval, nodes_list):
        self.verbose = self._world.env.config["verbose"]
        path = Path.cwd() / 'supply-chain-input-data' / json_file_name
        if not path.exists():
            raise Exception('Wrong working dir. Should be blocksim-dlasc')

        all_days = True
        with path.open() as f:
            all_days_tx = json.load(f)
            if all_days:
                today = 'All Days'
                # only one day's tx is too little...
                # Thus I decide to use all tx from 180 days,
                # but that turns out to be too much, so I add only every ten days
                # '''
                node_tx = []
                for key, value in all_days_tx.items():
                    # This part sums tx every ten days, e.g., 10, 20, 30 etc., to make tx larger, but not too large
                    node_tx.append(all_days_tx[key][1:])
                    # if int(key[-2:-1]) < 9:
                    #     pass
                node_tx_array = np.array(node_tx)
                # '''
                sum_tx = np.sum(node_tx_array, axis=0)
            else:
                today = self._world.env.data['day']
                sum_tx = all_days_tx[today][1:]

        # Jiali: Here we implement the paired transaction dictionary to count international tx.
        paired = False
        dict_path = Path.cwd() / 'supply-chain-input-data' / 'tx_dict.json'
        with dict_path.open() as df:
            paired_tx = json.load(df)

        blockchain_switcher = {
            'poa': self._generate_poa_tx,
            'pbft': self._generate_pbft_tx,
            'bitcoin': self._generate_bitcoin_tx,
            'ethereum': self._generate_ethereum_tx
        }

        if paired:
            international_tx = 0
            for sender in paired_tx.keys():
                transactions = []
                for j in paired_tx[sender].keys():
                    n_tx = paired_tx[sender][j]
                    i = int(sender)
                    j = int(j)
                    j = min(j, len(nodes_list) - 1)
                    for _i in range(n_tx):
                        sign = '-'.join([nodes_list[i].address, nodes_list[j].address, str(_i)])
                        tx = blockchain_switcher.get(self._world.blockchain, lambda: "Invalid blockchain")(sign, i)
                        transactions.append(tx)

                    if nodes_list[i].address[7] != nodes_list[j].address[7]:
                        self._world.env.data['international_transactions'] += n_tx

                self._world.env.process(self._set_interval(nodes_list[i], transactions, interval * i))
        else:
            for i in range(min(len(nodes_list), len(sum_tx))):
                transactions = []
                for _i in range(sum_tx[i]):
                    # Generate a random string to a transaction be distinct from others
                    # rand_sign = ''.join(
                    #     choices(string.ascii_letters + string.digits, k=20))
                    sign = '- '.join(
                        [today, nodes_list[i].address, str(_i), str(self._world.env.data['created_transactions'])])

                    tx = blockchain_switcher.get(self._world.blockchain, lambda: "Invalid blockchain")(sign, i)
                    transactions.append(tx)

                self._world.env.process(self._set_interval(nodes_list[i], transactions, interval * i))

    def _set_interval(self, node, tx, interval):
        event = simpy.events.Timeout(self._world.env, delay=interval, value=interval)
        value = yield event
        self._world.env.process(
            node.broadcast_transactions(tx))
        if self.verbose:
            print(f'{time(self._world.env)}, now {value} seconds have passed')
        self._world.env.data['created_transactions'] += len(tx)
        # yield self._world.env.timeout(interval)

    def _generate_pbft_tx(self, rand_sign, i):
        tx = Transaction('address', 'address', 140, rand_sign, 50)
        return tx
