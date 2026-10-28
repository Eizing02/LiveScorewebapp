import {defineConfig} from '@playwright/test';
// These specs share one local Worker and its persistent research D1 snapshot.
// A dedicated, strict port and API readiness check avoid reusing another app.
export default defineConfig({testDir:'tests/ui',workers:1,use:{baseURL:'http://127.0.0.1:5193',browserName:'chromium',headless:true},webServer:[{command:'npm run dev:api',url:'http://127.0.0.1:8787/api/health',reuseExistingServer:true,timeout:120000},{command:'npm run dev -- --port 5193 --strictPort',url:'http://127.0.0.1:5193/api/health',reuseExistingServer:true,timeout:60000}]});
