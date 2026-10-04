"""Wrap a real local model command without storing its private prompt.

MODEL_COMMAND is a JSON argv array. The command receives a JSON request on stdin
and must return PNG/JPEG/WebP bytes on stdout. stderr must not contain prompts.
Use a provider-owned key; an independent witness must observe the model run.
This script never fabricates a witness or claims that a local call is attested.
"""
import getpass
import json
import os
import subprocess
from modelledger_sdk import Provider, commit


def main():
    provider=Provider(os.environ['MODELLEDGER_API'],os.environ['PROVIDER_KEY'],os.environ['ACTOR_ID'],int(os.environ['CHAIN_ID']),os.environ['CONTRACT_ADDRESS'])
    private_prompt=getpass.getpass('Private prompt (not echoed or stored): ')
    root,owner_disclosures=commit({'prompt':private_prompt})
    argv=json.loads(os.environ['MODEL_COMMAND'])
    result=subprocess.run(argv,input=json.dumps({'prompt':private_prompt}).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=300)
    version=provider.register(result.stdout)
    event=provider.signed_event(version,[{'action':'AI_GENERATION'}],private_root=root)
    registered=provider.submit(event)
    print(json.dumps({'event_hash':registered['event_hash'],'status':'SELF_ASSERTED until anchored and independently corroborated'}))
    if input('Save owner-only disclosure package to an encrypted recipient? [y/N] ').lower()=='y':
        recipient=os.environ['AGE_RECIPIENT']
        subprocess.run(['age','-r',recipient,'-o','owner-disclosures.age'],input=json.dumps(owner_disclosures).encode(),check=True)
    provider.close()


if __name__=='__main__':main()
