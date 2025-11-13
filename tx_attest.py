#!/usr/bin/env python3
import os
import sys
import time
import json
from typing import Any, Dict
from web3 import Web3

DEFAULT_RPC_A = os.getenv("RPC_A", "https://mainnet.infura.io/v3/your_api_key")
DEFAULT_RPC_B = os.getenv("RPC_B", "https://eth.llamarpc.com")

def connect(url: str) -> Web3:
    if " " in url:
        print(f"⚠️ RPC URL contains whitespace: {url}")
    w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        print(f"❌ Failed to connect: {url}")
        sys.exit(1)
    return w3

def keccak_json(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return "0x" + Web3.keccak(data).hex()

def canonical_tx(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize transaction into a canonical dictionary:
    strip node-specific fields and normalize numeric types.
    """
    return {
        "hash": tx.get("hash").hex() if isinstance(tx.get("hash"), bytes) else tx.get("hash"),
        "nonce": int(tx.get("nonce", 0)),
        "from": tx.get("from"),
        "to": tx.get("to"),
        "value": int(tx.get("value", 0)),
        "gas": int(tx.get("gas", 0)),
        "gasPrice": int(tx.get("gasPrice", 0)) if tx.get("gasPrice") is not None else None,
        "maxFeePerGas": int(tx.get("maxFeePerGas", 0)) if tx.get("maxFeePerGas") is not None else None,
        "maxPriorityFeePerGas": int(tx.get("maxPriorityFeePerGas", 0)) if tx.get("maxPriorityFeePerGas") is not None else None,
        "type": int(tx.get("type", 0)) if tx.get("type") is not None else None,
        "input": tx.get("input"),
        "accessList": tx.get("accessList", None),
        "chainId": int(tx.get("chainId", 0)) if tx.get("chainId") is not None else None,
        "v": int(tx.get("v", 0)),
        "r": int(tx.get("r", 0)),
        "s": int(tx.get("s", 0)),
        "blockNumber": int(tx.get("blockNumber", 0)) if tx.get("blockNumber") is not None else None,
        "transactionIndex": int(tx.get("transactionIndex", 0)) if tx.get("transactionIndex") is not None else None,
    }

def fetch_tx(w3: Web3, tx_hash: str) -> Dict[str, Any]:
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if tx is None:
            return {"error": "transaction not found"}
        return canonical_tx(dict(tx))
    except Exception as e:
        return {"error": str(e)}

def compare_txs(tx_a: Dict[str, Any], tx_b: Dict[str, Any]):
    if "error" in tx_a or "error" in tx_b:
        return False, {
            "errorA": tx_a.get("error"),
            "errorB": tx_b.get("error"),
        }

    if tx_a == tx_b:
        return True, {"root": keccak_json(tx_a)}

    # diff on field-level
    diff_fields = {}
    for k in sorted(set(tx_a.keys()) | set(tx_b.keys())):
        if tx_a.get(k) != tx_b.get(k):
            diff_fields[k] = {"a": tx_a.get(k), "b": tx_b.get(k)}

    return False, {
        "rootA": keccak_json(tx_a),
        "rootB": keccak_json(tx_b),
        "fieldDiffs": diff_fields,
    }

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tx_attest.py <txhash> [rpcA] [rpcB]")
        print("Example:")
        print("  python tx_attest.py 0x1234...dead RPC_A_URL RPC_B_URL")
        sys.exit(1)

    txh = sys.argv[1]
    rpcA = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_RPC_A
    rpcB = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_RPC_B

    if not (txh.startswith("0x") and len(txh) == 66):
        print("❌ Invalid transaction hash; expected 0x + 64 hex chars.")
        sys.exit(2)

    if rpcA == rpcB:
        print("⚠️ rpcA and rpcB are identical — comparison will be trivial.")

    if "your_api_key" in rpcA or "your_api_key" in rpcB:
        print("⚠️ One of the RPC URLs still uses an Infura placeholder — replace with a real key.")

    wA = connect(rpcA)
    wB = connect(rpcB)

    chainA = wA.eth.chain_id
    chainB = wB.eth.chain_id
    print(f"🌐 RPC A: {rpcA} (chainId={chainA})")
    print(f"🌐 RPC B: {rpcB} (chainId={chainB})")

    if chainA != chainB:
        print("❌ chainId mismatch between RPC A and B — transaction views are not comparable.")
        sys.exit(3)

    print(f"🔍 Fetching transaction {txh}…")
    t0 = time.monotonic()
    txA = fetch_tx(wA, txh)
    txB = fetch_tx(wB, txh)
    elapsed = time.monotonic() - t0

    ok, info = compare_txs(txA, txB)

    if ok:
        print("✅ Transaction views match across both providers.")
        print(f"🔏 Canonical tx root: {info['root']}")
    else:
        print("❌ Transaction views differ.")
        print(json.dumps(info, indent=2))

    print(f"⏱️ Elapsed: {elapsed:.2f}s")

if __name__ == "__main__":
    main()
