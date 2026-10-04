"""Isolated test server: SQLite is permitted here only; EVM executes real bytecode."""
import os
import sys
import json
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'backend'),str(root/'sdk/python')]
workspace=tempfile.TemporaryDirectory(prefix='modelledger-e2e-')
os.environ.update(ENV='test',DATABASE_URL='sqlite:///'+workspace.name+'/e2e.db',ALLOW_SIMULATED='true',ENABLE_DEMO='true',RATE_LIMIT_PER_MINUTE='10000')
from eth_tester import EthereumTester,PyEVMBackend
from web3 import Web3,EthereumTesterProvider
from eth_account import Account
from app.config import settings
from app.chain.client import Chain,get_chain
from app.db.models import Base,Actor
from app.db.session import engine,SessionLocal
from app.main import app
from app.seed.demo import seed,h
from app.core.eip712 import ZERO
from alembic.config import Config
from alembic import command
import uvicorn

backend=PyEVMBackend();w3=Web3(EthereumTesterProvider(EthereumTester(backend=backend)))
artifact=json.loads((root/'backend/app/chain/abi/ModelLedgerRegistry.json').read_text())
tx=w3.eth.contract(abi=artifact['abi'],bytecode=artifact['bytecode']).constructor(w3.eth.accounts[0]).transact({'from':w3.eth.accounts[0]})
address=w3.eth.wait_for_transaction_receipt(tx).contractAddress
settings.chain_id=w3.eth.chain_id
chain=Chain(provider=w3.provider,address=address)
keys=['0x'+key.to_bytes().hex() for key in backend.account_keys]
settings.issuer_key=keys[8];settings.gateway_key=keys[9]
config=Config(str(root/'backend/alembic.ini'));config.set_main_option('script_location',str(root/'backend/alembic'))
command.upgrade(config,'head')
chain.send(chain.contract.functions.setIssuer(w3.eth.accounts[8]),keys[0])
with SessionLocal() as db:
    seed(db,chain,keys[0],keys=keys[1:8])
    actor_id=h('ModelLedger Transform Gateway')
    chain.send(chain.contract.functions.registerActor(actor_id,h('gateway-org'),ZERO),keys[9])
    chain.send(chain.contract.functions.approveActor(actor_id),keys[0])
    db.add(Actor(actor_id=actor_id,name='ModelLedger Transform Gateway',provider='ModelLedger',kind='TOOL',**chain.actor(actor_id)))
    db.commit()
app.dependency_overrides[get_chain]=lambda:chain
if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=8000,access_log=False)
