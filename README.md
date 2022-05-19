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
## Models

### Network Model
- Contains the state of each node; build connection channels; apply network latency
- Nodes are selected to broadcast their candidate block; Interval between each selection is the time between blocks
- Nodes have a hash rate; greater hash rate, greater the probability of the node being chosen
- It also simulates the occurrence of orphan blocks

### Node Model

### Chain Model

### Consensus Model


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






