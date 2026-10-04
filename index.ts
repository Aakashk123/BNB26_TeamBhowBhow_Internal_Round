import {Wallet,keccak256,toUtf8Bytes,TypedDataEncoder,randomBytes,hexlify,concat} from 'ethers';
import {canonicalize} from 'json-canonicalize';
export const eventTypes={Event:[['actorId','bytes32'],['action','uint8'],['modelRef','bytes32'],['parentEventIds','bytes32[]'],['inputSha256','bytes32[]'],['outputSha256','bytes32'],['outputPixelSha256','bytes32'],['outputPHash','uint64'],['paramsHash','bytes32'],['privateRoot','bytes32'],['claimedAt','uint64'],['nonce','bytes32']].map(([name,type])=>({name,type}))};
export const zeroHash='0x'+'00'.repeat(32);
export const paramsHash=(value:unknown)=>keccak256(toUtf8Bytes(canonicalize(value)));
export function commitment(values:Record<string,string>){
 const allowed=new Set(['prompt','negative_prompt','seed','sampler_params','source_file_sha256','operator_id']);
 const entries=Object.entries(values).sort(([a],[b])=>a.localeCompare(b));
 if(!entries.length||entries.some(([field])=>!allowed.has(field)))throw new Error('Unsupported private fields');
 const records=entries.map(([field,value])=>({field,value,salt:hexlify(randomBytes(16))}));
 const leaf=(r:typeof records[number])=>keccak256(concat([keccak256(toUtf8Bytes(r.field)),r.salt,keccak256(toUtf8Bytes(r.value))]));
 const leaves=records.map(leaf);while(leaves.length<8)leaves.push(hexlify(randomBytes(32)));
 const levels=[leaves];while(levels.at(-1)!.length>1){const row=levels.at(-1)!;const next=[];for(let i=0;i<row.length;i+=2)next.push(keccak256(concat([row[i],row[i+1]].sort())));levels.push(next);}
 return {root:levels.at(-1)![0],disclosures:records.map((record,index)=>{const proof=[];for(const row of levels.slice(0,-1)){proof.push(row[index^1]);index=Math.floor(index/2);}return {...record,proof};})};
}
export async function signEvent(key:string,chainId:number,contract:string,payload:Record<string,unknown>){
 const domain={name:'ModelLedger',version:'1',chainId,verifyingContract:contract};
 return {event_hash:TypedDataEncoder.hash(domain,eventTypes,payload),signature:await new Wallet(key).signTypedData(domain,eventTypes,payload)};
}
export async function submitEvent(apiUrl:string,event:unknown){const response=await fetch(apiUrl+'/api/v1/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(event,(_,value)=>typeof value==='bigint'?value.toString():value)});if(!response.ok)throw new Error(`Event submission failed: ${response.status}`);return response.json();}
