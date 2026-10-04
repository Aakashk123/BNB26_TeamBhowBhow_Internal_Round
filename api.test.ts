import {describe,it,expect,vi,afterEach} from 'vitest';
import {api,browserHash,human,shorten} from './api';
import {webcrypto} from 'node:crypto';
vi.stubGlobal('crypto',webcrypto);
afterEach(()=>vi.restoreAllMocks());
describe('API boundary',()=>{
 it('propagates safe API errors',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:422,json:async()=>({error:{message:'Invalid image'}})}));await expect(api('/api/v1/verify')).rejects.toThrow('Invalid image');});
 it('handles non-JSON proxy failures',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:502,json:async()=>{throw new Error('HTML');}}));await expect(api('/api/v1/verify')).rejects.toThrow('502');});
 it('hashes bytes with WebCrypto SHA-256',async()=>{const file=new File(['abc'],'test');expect(await browserHash(file)).toBe('0xba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');});
 it('humanizes the actual verdict without altering its meaning',()=>{expect(human('PROVENANCE_INVALID')).toBe('Provenance invalid');expect(shorten(undefined)).toBe('Not available');});
});
