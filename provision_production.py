"""One-time external-chain setup. Requires a funded registrar and gateway.
Run from backend with environment variables loaded from .env.production.
No mnemonic, unlocked account, or simulated provider is used.
"""
from eth_account import Account
from eth_utils import keccak
from app.chain.client import Chain
from app.config import settings
from app.core.eip712 import ZERO
from app.db.models import Actor
from app.db.session import SessionLocal


def main():
    if settings.env!='production':raise ValueError('This command requires ENV=production')
    chain=Chain()
    if not chain.ready():raise RuntimeError('Deploy the registry and configure its chain and address first')
    name='ModelLedger Transform Gateway';actor_id='0x'+keccak(text=name).hex()
    if chain.actor(actor_id)['status']==0:
        chain.send(chain.contract.functions.registerActor(actor_id,'0x'+keccak(text='ModelLedger').hex(),ZERO),settings.gateway_key)
    if chain.actor(actor_id)['status']==1:
        chain.send(chain.contract.functions.approveActor(actor_id),settings.registrar_key)
    chain.send(chain.contract.functions.setIssuer(Account.from_key(settings.issuer_key).address),settings.registrar_key)
    with SessionLocal() as db:
        if not db.get(Actor,actor_id):
            db.add(Actor(actor_id=actor_id,name=name,provider='ModelLedger',kind='TOOL',**chain.actor(actor_id)))
            db.commit()
    print('Production gateway and issuer provisioned. Remove REGISTRAR_KEY from the service environment.')


if __name__=='__main__':main()
