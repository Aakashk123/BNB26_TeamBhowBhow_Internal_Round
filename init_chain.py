"""Initialize local demo registry once; reuse a configured contract on later starts."""
import json
import time
from pathlib import Path
from eth_account import Account
from eth_utils import keccak
from sqlalchemy import select
from app.config import ROOT,settings
from app.chain.client import Chain
from app.core.eip712 import ZERO
from app.db.session import SessionLocal
from app.db.models import Actor


def main():
    if settings.env!='dev':
        print('Production registry must be provisioned by its registrar; no development transactions sent')
        return
    chain=Chain()
    if chain.web3.eth.chain_id!=settings.chain_id:raise RuntimeError('CHAIN_ID mismatch')
    if not chain.contract or not chain.web3.eth.get_code(chain.contract.address):
        artifact=json.loads((ROOT/'backend/app/chain/abi/ModelLedgerRegistry.json').read_text())
        admin=Account.from_key(settings.registrar_key)
        factory=chain.web3.eth.contract(abi=artifact['abi'],bytecode=artifact['bytecode'])
        receipt_hash=chain.send(factory.constructor(admin.address),settings.registrar_key)
        address=chain.web3.eth.get_transaction_receipt(receipt_hash).contractAddress
        (ROOT/'.runtime').mkdir(exist_ok=True)
        (ROOT/'.runtime/deployment.json').write_text(json.dumps({'address':address,'chainId':settings.chain_id}))
        chain=Chain(address=address)
    gateway=Account.from_key(settings.gateway_key)
    if chain.web3.eth.get_balance(gateway.address)<10**17:
        tx=chain.web3.eth.send_transaction({'from':Account.from_key(settings.registrar_key).address,'to':gateway.address,'value':10**18})
        chain.web3.eth.wait_for_transaction_receipt(tx)
    actor_id='0x'+keccak(text='ModelLedger Transform Gateway').hex()
    if chain.actor(actor_id)['status']==0:
        chain.send(chain.contract.functions.registerActor(actor_id,'0x'+keccak(text='ModelLedger').hex(),ZERO),settings.gateway_key)
    if chain.actor(actor_id)['status']==1:chain.send(chain.contract.functions.approveActor(actor_id),settings.registrar_key)
    chain.send(chain.contract.functions.setIssuer(Account.from_key(settings.issuer_key).address),settings.registrar_key)
    with SessionLocal() as db:
        if not db.get(Actor,actor_id):
            db.add(Actor(actor_id=actor_id,name='ModelLedger Transform Gateway',provider='ModelLedger',kind='TOOL',**chain.actor(actor_id)))
            db.commit()
    print('Registry, gateway and issuer ready')


if __name__=='__main__':main()
