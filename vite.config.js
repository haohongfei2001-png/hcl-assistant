import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
const privacyHeaders={'Referrer-Policy':'no-referrer'};
export default defineConfig({root:'apps/web',server:{headers:privacyHeaders,fs:{strict:true,allow:[fileURLToPath(new URL('.',import.meta.url))]},port:5173,strictPort:true,proxy:{'/v1':process.env.HCLA_TEST_CLOUD_PROXY?'http://127.0.0.1:8771':'http://127.0.0.1:8765'}},preview:{headers:privacyHeaders},build:{outDir:'../../dist',emptyOutDir:true}});
