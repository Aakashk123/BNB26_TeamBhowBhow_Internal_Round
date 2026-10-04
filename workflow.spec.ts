import {test,expect} from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

test('verify a real anchored demo, inspect graph, certificate and all attacks',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.setViewportSize({width:1440,height:1100});await page.goto('/');
 await expect(page.getByRole('heading',{name:'Every image has a history.'})).toBeVisible();
 fs.mkdirSync('../docs/screenshots',{recursive:true});await page.screenshot({path:'../docs/screenshots/verify.png',fullPage:true});
 await page.getByLabel('Choose image').setInputFiles(path.resolve('../demo/samples/04-final.jpg'));
 await page.getByLabel('Save this report to my history').check();await page.getByRole('button',{name:'Verify provenance'}).click();
 await expect(page.getByRole('heading',{name:'This image is bound to a trusted history.'})).toBeVisible();
 await expect(page.getByText('SIMULATED PROVIDERS —',{exact:false})).toBeVisible();
 await page.screenshot({path:'../docs/screenshots/result.png',fullPage:true});
 await page.getByRole('link',{name:'Provenance graph',exact:true}).click();
 const nodes=page.locator('.react-flow__node');await expect(nodes).toHaveCount(4);await nodes.first().click();
 await expect(page.getByText('SELECTED EVIDENCE')).toBeVisible();
 await page.getByRole('link',{name:'Certificate',exact:true}).click();
 const download=page.waitForEvent('download');await page.getByRole('link',{name:'Download PDF'}).click();expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
 await page.getByRole('link',{name:'Verification history'}).click();await expect(page.locator('.history-row')).toHaveCount(1);
 await page.getByRole('link',{name:'Adversarial lab'}).click();await page.getByRole('button',{name:'Run all scenarios'}).click();
 await expect(page.locator('.test-pass')).toHaveCount(21,{timeout:90000});
 await page.screenshot({path:'../docs/screenshots/adversarial.png',fullPage:true});expect(errors).toEqual([]);
});

test('unknown image, privacy mode, mobile and keyboard entry',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await page.getByLabel('Choose image').setInputFiles(path.resolve('../demo/samples/unknown.png'));
 await page.getByLabel('Hash in my browser').check();await page.getByRole('button',{name:'Verify provenance'}).click();
 await expect(page.getByRole('heading',{name:'There is not enough evidence to verify this image.'})).toBeVisible();
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);expect(overflow).toBe(false);
 await page.screenshot({path:'../docs/screenshots/mobile.png',fullPage:true});
 await page.getByRole('link',{name:'Verification history'}).click();await expect(page.getByRole('heading',{name:'Your saved reports will appear here.'})).toBeVisible();
});

test('200-node synthetic graph remains interactive',async({page})=>{
 // This fixture benchmarks rendering only; it makes no provenance claim.
 const nodes=Array.from({length:200},(_,i)=>({id:`IMG-${i}`,label:`IMG-${i}`,status:'UNKNOWN'}));
 const edges=nodes.slice(1).map((n,i)=>({id:`EDGE-${i}`,source:`IMG-${Math.floor(i/3)}`,target:n.id,label:'UNKNOWN / UNVERIFIED TRANSFORMATION',unknown:true}));
 await page.route('**/api/v1/reports/PERF-200',route=>route.fulfill({json:{report_id:'PERF-200',engine_version:'1',timestamp:new Date().toISOString(),input:{sha256:'0x'+'0'.repeat(64),c2pa:{state:'NONE'}},status:'UNVERIFIABLE',origin_trust:'UNVERIFIABLE',origin:{assurance:'A0',corroborations:[]},binding:{tier:'NONE'},graph:{nodes,edges,gaps:199,conflicts:0},counts:{verified:0,unverified:200,gaps:199,conflicts:0,tamper_warnings:0},reasons:[],candidates:[],privacy:{},chain:{},policy_hash:'test-only',saved:false,simulated:true}}));
 const start=Date.now();await page.goto('/graph/PERF-200');await expect(page.locator('.react-flow__node')).toHaveCount(200);
 const rendered=Date.now()-start;await page.locator('.react-flow__node').first().dispatchEvent('click');await expect(page.getByText('SELECTED EVIDENCE')).toBeVisible();
 const interaction=Date.now()-start-rendered;fs.writeFileSync('../bench/results/graph.json',JSON.stringify({fixture:'200-node synthetic rendering benchmark',nodes:200,edges:199,initial_render_ms:rendered,selection_ms:interaction},null,2));
 expect(rendered).toBeLessThan(10000);expect(interaction).toBeLessThan(2000);
});
