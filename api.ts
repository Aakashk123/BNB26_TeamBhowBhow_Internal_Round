export async function api<T>(path:string, init?:RequestInit):Promise<T>{
 const response=await fetch(path,{...init,credentials:'same-origin'});
 if(!response.ok){let message=`Request failed (${response.status})`;try{const data=await response.json();message=data.error?.message||message;}catch{/* Non-JSON proxy failure retains the HTTP status. */}throw new Error(message);}
 return response.json() as Promise<T>;
}
export function post<T>(path:string,data:unknown){return api<T>(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
export async function browserHash(file:File):Promise<string>{const hash=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());return '0x'+Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');}
export const human=(value:string)=>value.replaceAll('_',' ').toLowerCase().replace(/^./,c=>c.toUpperCase());
export const shorten=(value?:string)=>value?value.slice(0,12)+'…'+value.slice(-8):'Not available';
