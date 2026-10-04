import type { components } from './api-types';
export type Status='VERIFIED'|'PARTIALLY_VERIFIED'|'PROVENANCE_INVALID'|'UNVERIFIABLE';
export type Version={id:string;lineage_id:string;sha256:string;pixel_sha256:string;phash:Record<string,string>;mime:string;width:number;height:number;bytes:number;thumbnail:string|null;declared_origin:string|null;c2pa:{state:string}};
export type GraphNode={id:string;label:string;status:string;version?:Version;event_hash?:string;actor?:string;assurance?:string};
export type GraphEdge={id:string;source:string;target:string;label:string;unknown:boolean;status?:string;event_hash?:string;action?:unknown};
export type Report=Omit<components['schemas']['Report'],'input'|'binding'|'origin'|'graph'|'candidates'|'privacy'|'chain'> & {
 input:Partial<Version>&{sha256:string;c2pa:{state:string;valid?:boolean;signer_trusted?:boolean;actions?:string[]}};
 binding:{tier:string;version_id?:string};origin:{actor?:string;assurance:string;corroborations:string[]};
 graph:{nodes:GraphNode[];edges:GraphEdge[];gaps:number;conflicts:number};candidates:{version_id:string;hamming:number;relationship:string}[];
 privacy:{private_roots_present:number;plaintext_stored:boolean};chain:{available:boolean;chain_id:number;contract_address?:string}
};
export type Actor={actor_id:string;name:string;provider:string;kind:string;status:number;org_id:string;signer_address:string;approved_at:number;revoked_from:number;chain_checked:boolean};
export type Scenario={id:string;title:string;expected:{status:string;origin_trust?:string;codes?:string[]}};
export type Outcome={id:string;passed:boolean;actual:{status:string};scope:string};
