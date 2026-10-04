import json
from pathlib import Path
from app.adversarial.scenarios import fixtures,run


def main():
    rows=[]
    for s in fixtures():
        # Deliberately naive baseline: assumes approved signatures imply truthful origins.
        valid_approved=any(e['actor'].get('approved_at') for e in s['snapshot']['events'].values())
        baseline='VERIFIED' if valid_approved else 'UNVERIFIABLE'
        actual=run(s['id'])
        rows.append({'scenario':s['id'],'signature_only':baseline,'expected':s['expected']['status'],'baseline_correct':baseline==s['expected']['status'],'full_policy_correct':actual['passed']})
    result={'rows':rows,'signature_only_correct':sum(r['baseline_correct'] for r in rows),'full_policy_correct':sum(r['full_policy_correct'] for r in rows),
            'scope':'Controlled baseline versus production engine; TEE and watermark adapters not accredited or counted.'}
    root=Path(__file__).resolve().parents[1];(root/'bench/results/origin.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
