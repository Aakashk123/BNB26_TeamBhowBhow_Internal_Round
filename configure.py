"""Create local development secrets; never overwrites an existing configuration."""
import os
import secrets
import subprocess
from pathlib import Path
from eth_account import Account

root=Path(__file__).resolve().parents[1]
target=root/'.env'
if target.exists():
    print('Existing .env retained')
else:
    # Hardhat's documented public development mnemonic. This chain must stay local.
    Account.enable_unaudited_hdwallet_features()
    registrar=Account.from_mnemonic('test test test test test test test test test test test junk')
    postgres=secrets.token_hex(24)
    issuer='0x'+Account.create().key.hex();gateway='0x'+Account.create().key.hex()
    lines=['ENV=dev',f'POSTGRES_PASSWORD={postgres}',f'DATABASE_URL=postgresql+psycopg://modelledger:{postgres}@localhost:5432/modelledger',
           'CHAIN_RPC_URL=http://127.0.0.1:8545','CHAIN_ID=31337','CONTRACT_ADDRESS=',f'ISSUER_KEY={issuer}',f'GATEWAY_KEY={gateway}',
           f'REGISTRAR_KEY=0x{registrar.key.hex()}',f'DEV_API_KEY={secrets.token_hex(32)}','PUBLIC_URL=http://localhost:8080',
           'CORS_ORIGINS=http://localhost:8080,http://localhost:5173','ALLOW_SIMULATED=true','ENABLE_DEMO=true','RATE_LIMIT_PER_MINUTE=120']
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as file:file.write('\n'.join(lines)+'\n')
    print('Development configuration generated. Keep .env private.')
