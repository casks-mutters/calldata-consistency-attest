# calldata-consistency-attest

Attest that a transaction's **calldata and core fields** are identical across
two Ethereum-style RPC providers, and produce a Keccak commitment to the
canonicalized transaction.

Useful for:

- detecting RPCs that serve different calldata or access lists
- verifying L1 vs L2 gateway integrity
- checking client / infra upgrades for regressions
- building reproducible tx witnesses off-chain

---

## Installation

1. Python 3.9+
2. Install dependencies:

   ```bash
   pip install web3
