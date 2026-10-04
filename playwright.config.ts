import {defineConfig} from '@playwright/test';
import {execFileSync} from 'node:child_process';
const localBrowser=process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||execFileSync('node',['../scripts/prepare_browser.mjs'],{encoding:'utf8'}).trim();
export default defineConfig({testDir:'./e2e',fullyParallel:false,workers:1,timeout:90000,expect:{timeout:12000},reporter:[['list'],['html',{open:'never'}]],
 use:{baseURL:'http://127.0.0.1:5173',trace:'retain-on-failure',screenshot:'only-on-failure',launchOptions:{executablePath:localBrowser,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote']}},
 webServer:[{command:'../.venv/bin/python ../scripts/e2e_server.py',url:'http://127.0.0.1:8000/api/v1/health',timeout:120000,reuseExistingServer:false},{command:'npm run dev -- --host 127.0.0.1 --port 5173',url:'http://127.0.0.1:5173',timeout:60000,reuseExistingServer:false}]
});
