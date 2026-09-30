import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
export default defineConfig({root:'pages-preview',base:'./',server:{fs:{strict:true,allow:[fileURLToPath(new URL('.',import.meta.url))]},port:4174,strictPort:true},build:{outDir:'../pages-dist',emptyOutDir:true}});
