import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'contracts/artifacts/contracts/ModelLedgerRegistry.sol/ModelLedgerRegistry.json'
artifact=json.loads(source.read_text())
(root/'backend/app/chain/abi/ModelLedgerRegistry.json').write_text(json.dumps(artifact,indent=2)+'\n')
print('Contract artifact exported')
