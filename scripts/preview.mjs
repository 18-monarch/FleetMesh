// Static production bundle plus a same-origin API proxy, for local browser verification.
import http from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'../public');
const target=new URL(process.env.API_ORIGIN||'http://127.0.0.1:9293');
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.webp':'image/webp','.png':'image/png','.svg':'image/svg+xml','.mp4':'video/mp4'};
http.createServer(async(req,res)=>{
 if(req.url.startsWith('/api/')){
  const upstream=http.request(new URL(req.url,target),{method:req.method,headers:{...req.headers,host:target.host}},r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res)});
  upstream.on('error',()=>{res.writeHead(503,{'content-type':'application/json'});res.end('{"error":"Backend unavailable"}')});
  req.pipe(upstream);return;
 }
 let pathname;try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname)}catch{res.writeHead(400);res.end();return}
 if(pathname==='/')pathname='/index.html';else if(!path.extname(pathname))pathname+='.html';
 const file=path.resolve(root,'.'+pathname);
 if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return}
 try{const data=await readFile(file);res.writeHead(200,{'content-type':types[path.extname(file)]||'application/octet-stream'});res.end(req.method==='HEAD'?'':data)}catch{res.writeHead(404);res.end('Not found')}
}).listen(Number(process.env.PREVIEW_PORT||4173),'127.0.0.1',()=>console.log('Static frontend preview ready.'));
