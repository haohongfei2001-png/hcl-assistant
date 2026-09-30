import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
export default defineConfig({root:'apps/web',server:{fs:{strict:true,allow:[fileURLToPath(new URL('.',import.meta.url))]},port:5173,strictPort:true,proxy:{'/v1':'http://127.0.0.1:8765'}},build:{outDir:'../../dist',emptyOutDir:true}});
