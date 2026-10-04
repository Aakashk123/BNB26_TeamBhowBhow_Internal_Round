import json
from pathlib import Path
from threading import RLock

from eth_account import Account
from web3 import Web3

from app.config import ROOT, settings


def hex32(value):
    return "0x" + bytes(value).hex()


transaction_lock = RLock()


class Chain:
    def __init__(self, provider=None, address=None):
        self.web3 = Web3(provider or Web3.HTTPProvider(settings.chain_rpc_url, request_kwargs={"timeout": 5}))
        address = address or settings.contract_address
        deployment = ROOT / ".runtime/deployment.json"
        if not address and deployment.exists():
            address = json.loads(deployment.read_text())["address"]
        abi_path = Path(__file__).parent / "abi/ModelLedgerRegistry.json"
        artifact = json.loads(abi_path.read_text())
        self.contract = (
            self.web3.eth.contract(address=Web3.to_checksum_address(address), abi=artifact["abi"]) if address else None
        )

    def ready(self):
        return bool(
            self.contract
            and self.web3.is_connected()
            and self.web3.eth.chain_id == settings.chain_id
            and self.web3.eth.get_code(self.contract.address)
        )

    def send(self, function, key):
        with transaction_lock:
            acct = Account.from_key(key)
            transaction = function.build_transaction(
                {
                    "from": acct.address,
                    "nonce": self.web3.eth.get_transaction_count(acct.address, "pending"),
                    "chainId": self.web3.eth.chain_id,
                }
            )
            signed = acct.sign_transaction(transaction)
            tx = self.web3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx, timeout=60)
            if receipt.status != 1:
                raise ValueError("Chain transaction reverted")
            return hex32(tx)

    def actor(self, actor_id):
        a = self.contract.functions.getActor(actor_id).call()
        return {
            "signer_address": a[0],
            "org_id": hex32(a[1]),
            "model_measurement": hex32(a[2]),
            "status": a[3],
            "approved_at": a[4],
            "revoked_from": a[5],
        }

    def anchor(self, event_id):
        a = self.contract.functions.getAnchor(event_id).call()
        return {"actor_id": hex32(a[0]), "block_time": a[1], "block_number": a[2]}

    def witness_records(self, event_id):
        result = []
        for c in self.contract.functions.getWitnesses(event_id).call():
            info = self.contract.functions.witnesses(c[0]).call()
            result.append(
                {
                    "signer": c[0],
                    "org_id": hex32(c[1]),
                    "kind": c[2],
                    "evidence_hash": hex32(c[3]),
                    "block_time": c[4],
                    "approved": info[1] and hex32(info[0]) == hex32(c[1]),
                    "on_chain": True,
                }
            )
        return result


def get_chain():
    return Chain()
