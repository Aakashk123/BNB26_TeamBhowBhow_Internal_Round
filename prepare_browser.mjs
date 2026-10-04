// Portable test-browser extraction without filesystem ownership changes.
import {createReadStream,createWriteStream,mkdirSync,chmodSync,existsSync,statSync} from 'node:fs';
import {createBrotliDecompress} from 'node:zlib';
import {pipeline} from 'node:stream/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=path.join(root,'frontend/node_modules/@sparticuz/chromium/bin');
const destination=path.join(root,'.runtime/browser-v153');mkdirSync(destination,{recursive:true});
for(const name of ['chromium','fonts.tar','swiftshader.tar']){
 const output=path.join(destination,name);
 if(!existsSync(output)||statSync(output).size===0)await pipeline(createReadStream(path.join(source,name+'.br')),createBrotliDecompress(),createWriteStream(output));
 if(name.endsWith('.tar'))execFileSync('tar',['--no-same-owner','-xf',output,'-C',destination]);
}
chmodSync(path.join(destination,'chromium'),0o700);
process.stdout.write(path.join(destination,'chromium')+'\n');
