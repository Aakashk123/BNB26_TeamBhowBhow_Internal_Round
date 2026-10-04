"""Provider SDK. Private values and salts never leave the owner except by explicit disclosure."""
import secrets
import time
import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from .canonical import canonical, digest
from .commitments import commit
from .eip712 import ZERO, domain, event_hash, sign_event, sign_witness



class Provider:
    def __init__(self, api_url, key, actor_id, chain_id, contract_address):
        self.api_url=api_url.rstrip('/')
        self.key=key
        self.actor_id=actor_id
        self.domain=domain(chain_id,contract_address)
        self.http=httpx.Client(timeout=60, trust_env=bool(api_url))

    def signed_event(self, version, ops, action=1, parents=None, private_root=ZERO, model_ref=ZERO, simulated=False):
        parents=parents or []
        params={'width':version['width'],'height':version['height'],'mime':version['mime'],'ops':[{k:v for k,v in op.items() if v is not None} for op in ops],'simulated':simulated}
        payload={'actorId':self.actor_id,'action':action,'modelRef':model_ref,'parentEventIds':[p['event_hash'] for p in parents],
                 'inputSha256':[p['sha256'] for p in parents],'outputSha256':version['sha256'],'outputPixelSha256':version['pixel_sha256'],
                 'outputPHash':int(version['phash']['p'],16),'paramsHash':digest(params),'privateRoot':private_root,
                 'claimedAt':int(time.time()),'nonce':'0x'+secrets.token_hex(32)}
        return {'payload':payload,'params':params,'signature':sign_event(payload,self.domain,self.key)}

    def register_profile(self,name,provider,kind):
        profile={'actor_id':self.actor_id,'name':name,'provider':provider,'kind':kind}
        message=encode_defunct(primitive=canonical({**profile,'domain':self.domain}))
        profile['signature']='0x'+Account.sign_message(message,self.key).signature.hex()
        response=self.http.post(self.api_url+'/api/v1/actors',json=profile)
        response.raise_for_status();return response.json()

    def register(self,image,save_thumbnail=False):
        response=self.http.post(self.api_url+'/api/v1/register',files={'file':('output.png',image)},data={'save_thumbnail':str(save_thumbnail).lower()})
        response.raise_for_status();return response.json()['version']

    def submit(self,event):
        response=self.http.post(self.api_url+'/api/v1/events',json=event)
        response.raise_for_status();return response.json()

    def witness_package(self,event_id,evidence,kind=1):
        evidence_hash=digest(evidence)
        return {'kind':kind,'evidence':evidence,'signature':sign_witness(event_id,kind,evidence_hash,self.domain,self.key)}

    def close(self):
        self.http.close()


__all__=['Provider','commit','event_hash']
