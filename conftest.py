import os

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"
os.environ["ALLOW_SIMULATED"] = "true"
import json
from pathlib import Path

import pytest
from eth_tester import EthereumTester, PyEVMBackend
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from web3 import EthereumTesterProvider, Web3

from app.chain.client import Chain, get_chain
from app.config import settings
from app.db.models import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def chain():
    backend = PyEVMBackend()
    w3 = Web3(EthereumTesterProvider(EthereumTester(backend=backend)))
    artifact = json.loads((Path(__file__).resolve().parents[1] / "app/chain/abi/ModelLedgerRegistry.json").read_text())
    tx = (
        w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        .constructor(w3.eth.accounts[0])
        .transact({"from": w3.eth.accounts[0]})
    )
    address = w3.eth.wait_for_transaction_receipt(tx).contractAddress
    original = settings.chain_id
    settings.chain_id = w3.eth.chain_id
    c = Chain(provider=w3.provider, address=address)
    c.keys = ["0x" + k.to_bytes().hex() for k in backend.account_keys]
    yield c
    settings.chain_id = original


@pytest.fixture
def db():
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool} if url.startswith("sqlite") else {}
    engine = create_engine(url, **kwargs)
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db, chain):
    def db_override():
        yield db

    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_chain] = lambda: chain
    original = settings.issuer_key
    settings.issuer_key = chain.keys[8]
    chain.send(chain.contract.functions.setIssuer(chain.web3.eth.accounts[8]), chain.keys[0])
    with TestClient(app) as c:
        yield c
    settings.issuer_key = original
    app.dependency_overrides.clear()
