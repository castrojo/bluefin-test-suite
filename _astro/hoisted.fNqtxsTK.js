const w="https://raw.githubusercontent.com/projectbluefin/testing-lab/main/docs/data/factory-stats.json";async function T(){try{const t=await fetch(w);if(!t.ok)throw new Error("CORS or network error");const e=await t.json(),s=document.getElementById("factory-time");s&&e._meta?.generated&&(s.textContent=`Data: ${new Date(e._meta.generated).toLocaleString()}`);const a=document.getElementById("factory-nodes");a&&e.factory?.cluster?.nodes&&(a.innerHTML=e.factory.cluster.nodes.map(o=>`
          <div class="flex items-center justify-between bg-slate-950/40 px-3 py-1.5 rounded border border-slate-800/40">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full ${o.status==="ready"?"bg-emerald-500":"bg-rose-500"}"></span>
              <span class="font-bold text-slate-200">${o.name}</span>
            </div>
            <span class="text-xs text-slate-500 font-mono">${o.role.split("+")[0]} · ${o.ram_gb}GB</span>
          </div>
        `).join(""));const n=e.factory?.semaphores?.containerdisk||{capacity:8,active:0},r=e.factory?.semaphores?.hostdisk||{capacity:6,active:0},c=document.getElementById("sem-cd-pips");c&&(c.innerHTML=Array.from({length:n.capacity},(o,x)=>`
          <div class="flex-1 ${x<n.active?"bg-blue-500/80 border border-blue-500/20":"bg-slate-800 border border-slate-700"} rounded-sm"></div>
        `).join(""));const l=document.getElementById("sem-hd-pips");l&&(l.innerHTML=Array.from({length:r.capacity},(o,x)=>`
          <div class="flex-1 ${x<r.active?"bg-indigo-500/80 border border-indigo-500/20":"bg-slate-800 border border-slate-700"} rounded-sm"></div>
        `).join(""));const u=document.getElementById("val-pipeline-success");u&&e.pipelines?.containerdisk?.success_rate_pct&&(u.textContent=`${e.pipelines.containerdisk.success_rate_pct}%`);const y=document.getElementById("val-runs-week");y&&e.pipelines?.containerdisk?.runs_7d&&(y.textContent=e.pipelines.containerdisk.runs_7d);const f=document.getElementById("triage-bugs"),v=document.getElementById("bug-badge");e.open_bugs&&(v&&(v.textContent=`${e.open_bugs.length} open`),f&&(e.open_bugs.length===0?f.innerHTML=`
              <div class="bg-slate-900/40 p-4 rounded-xl text-center text-xs text-slate-500 border border-slate-800/40">
                No active pipeline bugs!
              </div>`:f.innerHTML=e.open_bugs.slice(0,10).map(o=>`
              <div class="flex items-start justify-between bg-slate-900/40 px-3 py-2 rounded-lg border border-slate-800/40 text-xs">
                <div class="flex-1 min-w-0 pr-2">
                  <a href="${o.url}" target="_blank" class="font-bold text-slate-200 hover:text-blue-400 transition-colors block truncate">${o.title}</a>
                  <span class="text-[10px] text-slate-500 font-mono mt-0.5 block">Opened: ${new Date(o.created_at).toLocaleDateString()}</span>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${o.area==="test"?"bg-amber-500/10 border border-amber-500/20 text-amber-400":"bg-rose-500/10 border border-rose-500/20 text-rose-400"}">
                  ${o.area||"unknown"}
                </span>
              </div>
            `).join("")))}catch(t){console.warn("Telemetry fallback used: ",t);const e=document.getElementById("bug-badge");e&&(e.textContent="Offline")}}const i=["A","B","C"];function L(){const e=(new URLSearchParams(location.search).get("variant")||"B").toUpperCase();return i.includes(e)?e:"B"}function b(t){const e=new URL(location.href);e.searchParams.set("variant",t),history.replaceState({},"",e),i.forEach(s=>{const a=document.getElementById("tab-"+s),n=document.getElementById("view-"+s);s===t?(a?.classList.add("border-blue-500","text-blue-400"),a?.classList.remove("border-transparent","text-slate-400"),n?.classList.add("block"),n?.classList.remove("hidden")):(a?.classList.remove("border-blue-500","text-blue-400"),a?.classList.add("border-transparent","text-slate-400"),n?.classList.add("hidden"),n?.classList.remove("block"))})}i.forEach(t=>{document.getElementById("tab-"+t)?.addEventListener("click",()=>b(t))});document.addEventListener("keydown",t=>{const e=document.activeElement?.tagName;if(e==="INPUT"||e==="TEXTAREA")return;const s=L(),a=i.indexOf(s);if(t.key==="ArrowLeft"){const n=(a-1+i.length)%i.length;b(i[n])}else if(t.key==="ArrowRight"){const n=(a+1)%i.length;b(i[n])}});b(L());T();let m=null;const h=document.getElementById("global-search-input"),g=document.getElementById("search-results-container"),p=document.getElementById("search-results-list"),d=document.getElementById("search-status");h?.addEventListener("focus",async()=>{if(m)g?.classList.remove("hidden");else{d.innerText="Loading index...",g?.classList.remove("hidden");try{m=await import((document.getElementById("search-root")?.getAttribute("data-base-url")||"/")+"pagefind/pagefind.js"),await m.init(),d.innerText="Ready to search. Start typing..."}catch(t){d.innerText="Failed to load search index.",console.error("Pagefind error:",t)}}});let E;h?.addEventListener("input",t=>{clearTimeout(E);const e=t.target.value.trim();if(e.length<2){p&&(p.innerHTML=""),d.innerText="Type at least 2 characters...",d.classList.remove("hidden");return}E=setTimeout(async()=>{if(!m)return;d.innerText="Searching...",d.classList.remove("hidden"),p.innerHTML="";const s=await m.search(e);if(s.results.length===0){d.innerText="No results found matching your query.";return}d.classList.add("hidden");const a=s.results.slice(0,8);for(const n of a){const r=await n.data(),c=document.createElement("div");c.className="hover:bg-slate-900 transition-colors p-4 block cursor-pointer";const l=r.meta.status||"unknown",u=l==="success"||l==="passed"?"bg-emerald-500/10 text-emerald-400 border-emerald-500/20":"bg-rose-500/10 text-rose-400 border-rose-500/20";c.innerHTML=`
          <div class="flex items-center justify-between mb-1">
            <span class="text-sm font-semibold font-mono text-blue-400">${r.meta.title}</span>
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${u}">
              ${l.toUpperCase()}
            </span>
          </div>
          <div class="text-xs text-slate-400 font-mono mb-2 flex justify-between">
            <span>Env: ${r.meta.environment||"N/A"}</span>
            <span>Commit: ${r.meta.commit||"N/A"}</span>
          </div>
          <!-- Highlight excerpt injected dynamically by Pagefind -->
          <div class="text-sm text-slate-300 font-mono bg-slate-950 p-2 rounded border border-slate-800/80 leading-relaxed overflow-x-hidden truncate-3-lines">
            ${r.excerpt}
          </div>
        `,c.addEventListener("click",()=>{window.location.href=r.url}),p?.appendChild(c)}},150)});document.addEventListener("click",t=>{!h?.contains(t.target)&&!g?.contains(t.target)&&g?.classList.add("hidden")});
