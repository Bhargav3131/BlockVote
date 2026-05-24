import hashlib
import json
import time

def calculate_hash(index, previous_hash, timestamp, voter_prn_hash, candidate_id):
    block_string = json.dumps({
        "block_index": index,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "voter_prn_hash": voter_prn_hash,
        "candidate_id": candidate_id
    }, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def hash_prn(prn):
    return hashlib.sha256(prn.strip().upper().encode()).hexdigest()

def create_genesis_block():
    timestamp = 0
    return {
        "index": 0,
        "previous_hash": "0" * 64,
        "timestamp": timestamp,
        "voter_prn_hash": "GENESIS",
        "candidate_id": 0,
        "hash": calculate_hash(0, "0" * 64, timestamp, "GENESIS", 0)
    }

def create_block(index, previous_hash, voter_prn_hash, candidate_id):
    timestamp = time.time()
    return {
        "index": index,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "voter_prn_hash": voter_prn_hash,
        "candidate_id": candidate_id,
        "hash": calculate_hash(index, previous_hash, timestamp, voter_prn_hash, candidate_id)
    }

def validate_chain(blocks):
    if not blocks:
        return True, "Chain is empty"
    for i in range(1, len(blocks)):
        curr = blocks[i]
        prev = blocks[i - 1]
        expected = calculate_hash(curr["block_index"], curr["previous_hash"], curr["timestamp"], curr["voter_prn_hash"], curr["candidate_id"])
        if curr["hash"] != expected:
            return False, f"Block {curr['block_index']} has been tampered (hash mismatch)"
        if curr["previous_hash"] != prev["hash"]:
            return False, f"Block {curr['block_index']} broken from chain (previous_hash mismatch)"
    return True, "Blockchain is valid and untampered"
