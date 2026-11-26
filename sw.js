/* V4.74: dynamic research reports are network-only; static shell may work offline. */
const CACHE="ortak-analiz-v510-static-1";
const ASSETS=["./","./index.html","./manifest.webmanifest","./icon-192.png","./icon-512.png","./mobile-v487.js","./money-v497.js","./mobile-v487.css","./legacy.html"];
function networkOnly(request, origin) {
  const url=new URL(request.url);
  return url.origin===origin && (/\.json$/i.test(url.pathname) || request.cache==="no-store" || url.searchParams.has("ts"));
}
if(typeof module!=="undefined" && module.exports) module.exports={networkOnly};
if(typeof self!=="undefined" && self.addEventListener){
  self.addEventListener("install",e=>{
    self.skipWaiting();
    e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));
  });
  self.addEventListener("activate",e=>{
    e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith("ortak-analiz-")&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
  });
  self.addEventListener("fetch",e=>{
    const req=e.request;
    if(req.method!=="GET"||new URL(req.url).origin!==self.location.origin)return;
    if(networkOnly(req,self.location.origin)){
      e.respondWith(fetch(req,{cache:"no-store"}));
      return;
    }
    e.respondWith(fetch(req).then(async r=>{
      if(r.ok){
        try{const c=await caches.open(CACHE);await c.put(req,r.clone());}catch(_){}
      }
      return r;
    }).catch(async ()=>{
      const c=await caches.open(CACHE);
      const saved=await c.match(req);
      return saved||new Response("Offline",{status:503});
    }));
  });
}
