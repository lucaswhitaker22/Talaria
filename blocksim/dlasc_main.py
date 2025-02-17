import time
import json
from blocksim.world import SimulationWorld
from blocksim.dlasc_node_factory import NodeFactory
from blocksim.dlasc_transaction_factory import TransactionFactory
from blocksim.models.network import Network


def write_report(world):
    with open('output/report.json', 'w') as f:
        # f.write(dump_json(world.env.data))
        json.dump(world.env.data, f, indent=2)


def report_node_chain(world, nodes_list):
    for node in nodes_list:
        head = node.chain.head
        chain_list = []
        num_blocks = 0
        for i in range(head.header.number):
            b = node.chain.get_block_by_number(i)
            chain_list.append(str(b.header))
            num_blocks += 1
        chain_list.append(str(head.header))
        key = f'{node.address}_chain'
        world.env.data[key] = {
            'head_block_hash': f'{head.header.hash[:8]} #{head.header.number}',
            'number_of_blocks': num_blocks,
            'chain_list': chain_list
        }


def run_model():
    now = int(time.time())  # Current time
    duration = 180*24*3600  # seconds

    world = SimulationWorld(
        duration,
        now,
        'dlasc-input-parameters/config.json',
        'dlasc-input-parameters/latency.json',
        'dlasc-input-parameters/throughput-received.json',
        'dlasc-input-parameters/throughput-sent.json',
        'dlasc-input-parameters/delays.json')

    # Create the network
    network = Network(world.env, 'NetworkXPTO')

    miners = {
        '5': {
            'how_many': 1,
            'mega_hashrate_range': "(20, 40)"
        },
        '1': {
            'how_many': 1,
            'mega_hashrate_range': "(20, 40)"
        }
    }
    non_miners = {
        '1': {
            'how_many': 1
        },
        '4': {
            'how_many': 1
        }
    }

    node_factory = NodeFactory(world, network)
    # Create all nodes
    # Notice that the miner/non_miners this useless here, they're specified in
    # dlasc_node_factory
    nodes_list = node_factory.create_nodes(miners, non_miners)
    # Start the network heartbeat
    world.env.process(network.start_heartbeat())
    # Full Connect all nodes
    for node in nodes_list:
        node.connect(nodes_list)

    transaction_factory = TransactionFactory(world)
    transaction_factory.broadcast(10, 1, 1500, nodes_list)

    world.start_simulation()
    report_node_chain(world, nodes_list)
    write_report(world)


if __name__ == '__main__':
    run_model()
