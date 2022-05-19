# Talaria

Talaria is a novel permissioned blockchain simulator based on open source blockchain simulator [BlockSim](https://github.com/carlosfaria94/blocksim). We significantly extend the capability of BlockSim, to support permissioned blockchains. To the best of our knowledge, Talaria is the first blockchain simulator designed for simulating private blockchain models. 

Presently, a simplified version of Proof-of-Authority and the complete pBFT consensus protocols are implemented. Other permissioned protocols such as PoET can easily be included into our flexible modeling framework. Moreover, our new blockchain simulator handles  different types of faulty authorities and a variable number of transactions generated per day at every node. These features make our Talaria ideal for testing and simulating protocols for a range of use cases including the challenging setting of supply chain management. We also demonstrate its application on a supply chain management example that utilizes the practical Byzantine Fault Tolerance (pBFT) protocol. 

Protocols Out-of-box:
 - Simplified PoA
 - pBFT
 - PoET

Other features are also included for convenience:
 - Simulating for certain time duration v.s. until finish certain amount of transactions.
 - Counting inter-regional transactions.
 - Multiple (days') simulation using the same chain.
 - Switching output on and off
 
---

# Full Paper

Please cite our paper if you use it in your research: `Talaria: A Framework for Simulation of Permissioned Blockchains for Logistics and Beyond`.

The full paper is now available at [arXiv](https://arxiv.org/abs/2103.02260). 

---
# Overview
There are several important classes that are needed by the simulator. There is needed a main file, a transaction factory, and a node factory, as well as a variety of configuration and parameter files. Each is described below in detail.

## main.py
This function takes in a json file with the number of transactions for each node on each day, and uses imported per protocol transaction and node factories, as well as per protocol network files to create the simulation world. This function also relies on the following files: config.json, latency.json, throughput_received.json, throughput_sent.json, delays.json. This function will also call the network's start_heartbeat, and run the simulation using the world's start_simulation function.

## config.json
This file includes parameters such as the number of transactions per block, block size limit, and the max size of each block.

## latency.json
This file includes the latency distributions from each location to each other location. There are some researches in literature which can help find these distributions for a specific use case.

## throughput_received.json
For each location, this file includes outgoing throughput distributions and parameters to every other location.

## throughput_sent.json
For each location, this file includes incoming throughput distributions and parameters to every other location.

## delays.json
This file includes distribution specifications for a variety of other delays that may occur. For example, the distributions for the transaction validation time, the block validation time, and the time between blocks. 

## Transaction Factory
The current transaction factory takes in a JSON file indicating the number of transactions created by each node every day.

## Node Factory
The node factory will populate the simulated world with new instances of some kind of node. There are currently implemented a permissioned node factory and a public node factory.

## Network
The network is a low level class which interacts with the underlying event framework and uses the network delays config to handle processing message delivery.

---
# Run the Simulation
Here is how you can run this simulation
## Setup
Setup pip depedencies.
```
cd ./talaria
pip install . 
pip install -r requirements.txt
```

## Installation 
First, clone this repo to your local directory. 
Then, install the dependences, I suggest that you use conda:

Omits build info in talaria.yml
```
conda env export -n talaria -f talaria.yml --no-builds
```
Build the Conda enviroment
```
conda env create -f talaria.yml
```

## Running 
```
conda activate talaria
set PYTHONPATH='.'

python ./blocksim/pbft_main.py
```

Use export instead of set for unix/linux systems
```
export PYTHONPATH='.'
```
This runs the pBFT protocol as default.

---
# Acknowledgment

This material is based on work supported by the Defense Advanced Research Projects Agency (DARPA) and Space and Naval Warfare Systems Center, Pacific (SSC Pacific) under contract number N6600118C4031.



# Notes from Blocksim
https://static.carlosfaria.pt/file/personal-assets/talks/blocksim-ieee-blockchain-2019.pdf

## Architecture

![image](https://user-images.githubusercontent.com/19495613/169375338-8c9398b3-b895-465d-9e9d-2382b414d8f0.png)

### Discrete Event Simulation Engine
- Manages simulation clock
- Scheduling, queing and processing events
- Control the access of resources by the entities
- Creation of blockchain system entities (nodes, blocks, transactions)

### Simulation World
Management of simulation input parameters:
- Configuration File
- Delays
- Latency
- Throughput Received and Sent

The world starts here. It sets the simulation world.

The simulation world can be configured with the following characteristics:
- param int sim_duration: duration of the simulation
- param str blockchain: the type of blockchain being simulated (e.g. bitcoin or ethereum)
- param dict time_between_block_distribution: Probability distribution to represent the time between blocks
- param dict validate_tx_distribution: Probability distribution to represent the transaction validation delay
- param dict validate_block_distribution: Probability distribution to represent the block validation delay

Each distribution is represented as dictionary, with the following schema: { 'name': str, 'parameters': tuple }

## Models

![image](https://user-images.githubusercontent.com/19495613/169374091-bdcab8ff-d96d-4e19-8922-f488fa8c27fa.png)

### Network Model
- Contains the state of each node; build connection channels; apply network latency
- Nodes are selected to broadcast their candidate block; Interval between each selection is the time between blocks
- Nodes have a hash rate; greater hash rate, greater the probability of the node being chosen
- It also simulates the occurrence of orphan blocks

### Node Model
- P2P network functionality
- Origin node starts listening for inbound communications from a destination node; a node can send a direct message or broadcast a message to all neighbours
- It also apply a delay when receiving and sending messages, corresponding to node throughput
- This model is normally extended to implement a specific blockchain client implementation

### Chain Model
- Mimic the behaviour of a chain:
- when adding a block, checks if the block is being added to the head; if the case, adds a block to the chain. Otherwise, the block is added to a queue
- when is not being added to the head, and the previous hash points to an old block, it creates a fork on the chain by creating a secondary chain. Then, it checks if the block should be the new head by calculating the difficulty of the chain. If this is the case, it accepts the secondary chain as the main chain

### Consensus Model
- We do not perform block or transaction validation, it adds a delay that simulates the validation process

difficulty = Pd+(Bts-Pts)

- It also defines a simple equation to calculate the difficulty of a new block: It simplifies and resembles ideas from Ethereum and Bitcoin by incrementing the difficulty of a block when it is created in less time

## Modeling Bitcoin
- Simulation World receives the block size limit and the probability distribution for the number of transactions per block
- There are miner nodes and non-miner nodes
- Miner nodes: broadcast its candidate block to the network (when selected by the Network)
![image](https://user-images.githubusercontent.com/19495613/169376928-111628d8-b232-411c-911b-0b1584bd1de6.png)
![image](https://user-images.githubusercontent.com/19495613/169376670-382dd90f-4092-4f84-875c-7a34900bb03b.png)

## Modeling Ethereum
- Simulation World receives the block gas limit and start gas for every transaction
Ex. if we set the simulation to have a block gas limit of 10,000, and for a transaction start gas of 1,000, then we can fit 10 transactions
![image](https://user-images.githubusercontent.com/19495613/169376888-34b5f8b4-0401-4a7f-b5fe-4b3fef183e27.png)
![image](https://user-images.githubusercontent.com/19495613/169376733-3c542f6c-fca4-4e49-88d4-099733167306.png)

# Other Notes

# Classes

## Main:
### NodeFactory
from blocksim.models.bitcoin.node import BTCNode
from blocksim.models.ethereum.node import ETHNode

### TransactionFactory
from blocksim.models.transaction import Transaction
from blocksim.models.ethereum.transaction import Transaction as ETHTransaction


## Permissioned Blockchain:
### permissioned_main.py
from blocksim.models.poa.poa_network import PoANetwork as Network

from blocksim.permissioned_node_factory import PermNodeFactory
from blocksim.permissioned_transaction_factory import PermTransactionFactory

from blocksim.world import SimulationWorld

### permissioned_transaction_factory.py
from blocksim.transaction_factory import TransactionFactory

from blocksim.models.ethereum.transaction import Transaction as ETHTransaction
from blocksim.models.transaction import Transaction

### permissioned_node_factory.py
- Models
from blocksim.models.bitcoin.node import BTCNode
from blocksim.models.ethereum.dlasc_node import ETHNode
from blocksim.models.poa.node import POANode
from blocksim.models.pbft.node import PBFTNode
from blocksim.models.pbft_network import MaliciousModel

from blocksim.node_factory import NodeFactory






