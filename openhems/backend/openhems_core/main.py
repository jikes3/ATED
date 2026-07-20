from __future__ import annotations

import html
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from . import __version__
from .config import load_settings
from .database import DB_PATH, init_database
from .discovery import DEVICE_RULES, discover_devices
from .ha_client import all_states, ha_get, supervisor_get, token_available
from .registry import Device, EntityMapping, RegistryStore
from .tank import horizontal_tank_volume, refill_decision

app = FastAPI(title="OpenHEMS Core", version=__version__, docs_url=None, redoc_url=None, openapi_url="/openapi.json")


@app.middleware("http")
async def home_assistant_ingress(request: Request, call_next):
    ingress_path = request.headers.get("x-ingress-path", "").rstrip("/")
    if ingress_path:
        request.scope["root_path"] = ingress_path
    return await call_next(request)


registry_store = RegistryStore(DB_PATH)


@app.on_event("startup")
def startup() -> None:
    init_database()
    seed_registry()


def ingress_base(request: Request) -> str:
    return request.headers.get("x-ingress-path", "").rstrip("/")


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


STYLE = """
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color-scheme:light dark}*{box-sizing:border-box}
body{margin:0;background:#f3f5f8;color:#17202a}.wrap{max-width:1200px;margin:auto;padding:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 12px #0002}nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}nav a{background:#fff;padding:9px 13px;border-radius:9px;text-decoration:none;color:#1565c0;font-weight:700}.ok,.found{color:#16803a}.bad,.missing{color:#b3261e}.partial{color:#ad6800}.metric{font-size:2rem;font-weight:800}.muted{color:#667085}table{width:100%;border-collapse:collapse}th,td{padding:9px;text-align:left;border-bottom:1px solid #ddd;vertical-align:top}code{word-break:break-all}.btn{border:0;border-radius:8px;padding:9px 13px;font-weight:700;cursor:pointer;background:#1565c0;color:white}.btn.secondary{background:#667085}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.grow{flex:1;min-width:240px}input,select{width:100%;padding:9px;border-radius:8px;border:1px solid #98a2b3;background:inherit;color:inherit}.status{font-weight:700}.progress{height:10px;background:#d0d5dd;border-radius:999px;overflow:hidden}.progress>span{display:block;height:100%;background:#16803a}
@media(prefers-color-scheme:dark){body{background:#11161d;color:#eef2f6}.card,nav a{background:#1d2630}.muted{color:#aab4c0}nav a{color:#75b7ff}th,td{border-color:#394552}input,select{border-color:#596675}}
"""


def page(request: Request, title: str, content: str, script: str = "") -> HTMLResponse:
    base = ingress_base(request)
    links = [("/", "Přehled"), ("/setup", "Průvodce"), ("/devices", "Discovery"), ("/registry", "Registry"), ("/diagnostics", "Diagnostika"), ("/api/docs", "API")]
    nav = "".join(f'<a href="{base}{path}">{label}</a>' for path, label in links)
    return HTMLResponse(f"<!doctype html><html lang='cs'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>{esc(title)}</title><style>{STYLE}</style></head><body><div class='wrap'><h1>OpenHEMS <small>{__version__}</small></h1><nav>{nav}</nav>{content}</div><script>const BASE={base!r};{script}</script></body></html>")


def seed_registry() -> None:
    settings = load_settings()
    registry_store.upsert_device(Device(None, "rain_tank", "Dešťová nádrž", "tank"))
    if registry_store.get_mapping("rain_tank", "level") is None:
        registry_store.upsert_mapping(EntityMapping(None, "rain_tank", "level", settings.tank_level_entity, "addon_options", 100))
    if registry_store.get_mapping("rain_tank", "refill_pump") is None:
        registry_store.upsert_mapping(EntityMapping(None, "rain_tank", "refill_pump", settings.refill_pump_entity, "addon_options", 100))


async def get_tank_state() -> dict[str, Any]:
    settings = load_settings()
    mapping = registry_store.get_mapping("rain_tank", "level")
    entity_id = mapping.entity_id if mapping else settings.tank_level_entity
    state = await ha_get(f"/states/{entity_id}")
    level_m = float(str(state.get("state", "")).replace(",", "."))
    volume_l = horizontal_tank_volume(level_m, settings.tank_capacity_l, settings.tank_length_m, settings.tank_diameter_m)
    percent = 100 * volume_l / settings.tank_capacity_l
    return {"entity_id": entity_id, "level_m": round(level_m, 3), "volume_l": round(volume_l), "free_l": round(settings.tank_capacity_l-volume_l), "percent": round(percent, 1), "decision": refill_decision(percent, settings.refill_start_percent, settings.refill_stop_percent, settings.emergency_percent), "dry_run": settings.dry_run}


@app.get("/api/docs", include_in_schema=False)
async def api_docs(request: Request) -> HTMLResponse:
    base = ingress_base(request)
    return get_swagger_ui_html(openapi_url=f"{base}/openapi.json", title=f"OpenHEMS Core {__version__} – API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/tank")
async def api_tank() -> JSONResponse:
    try: return JSONResponse(await get_tank_state())
    except Exception as exc: return JSONResponse({"error": str(exc)}, status_code=503)


@app.get("/api/entities")
async def api_entities() -> JSONResponse:
    try: return JSONResponse(await all_states())
    except Exception as exc: return JSONResponse({"error": str(exc)}, status_code=503)


@app.get("/api/discovery")
async def api_discovery() -> JSONResponse:
    try: return JSONResponse({"devices": discover_devices(await all_states())})
    except Exception as exc: return JSONResponse({"error": str(exc)}, status_code=503)


@app.post("/api/discovery/apply")
async def api_discovery_apply(payload: dict[str, Any]) -> dict[str, Any]:
    devices = payload.get("devices")
    if not isinstance(devices, list):
        raise HTTPException(status_code=400, detail="devices musí být seznam")
    saved = 0
    for item in devices:
        if not isinstance(item, dict): continue
        key = str(item.get("key") or "").strip()
        if not key: continue
        registry_store.upsert_device(Device(None, key, str(item.get("name") or key), str(item.get("device_type") or "generic")))
        mappings = item.get("mappings") or {}
        if isinstance(mappings, dict):
            for function, entity_id in mappings.items():
                entity_id = str(entity_id or "").strip()
                if "." not in entity_id: continue
                registry_store.upsert_mapping(EntityMapping(None, key, str(function), entity_id, "discovery", 90))
                saved += 1
    return {"saved_mappings": saved}


@app.get("/api/registry")
async def api_registry() -> dict[str, Any]:
    return {"devices": registry_store.list_devices()}


@app.put("/api/registry/devices/{device_key}")
async def api_upsert_device(device_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    device = Device(None, device_key, str(payload.get("name") or device_key), str(payload.get("device_type") or "generic"), bool(payload.get("enabled", True)))
    return registry_store.upsert_device(device).to_dict()


@app.put("/api/registry/devices/{device_key}/mappings/{function}")
async def api_upsert_mapping(device_key: str, function: str, payload: dict[str, Any]) -> dict[str, Any]:
    entity_id = str(payload.get("entity_id") or "").strip()
    if "." not in entity_id: raise HTTPException(status_code=400, detail="entity_id musí mít tvar domain.object_id")
    mapping = EntityMapping(None, device_key, function, entity_id, str(payload.get("source") or "manual"), max(0, min(100, int(payload.get("confidence", 100)))))
    return registry_store.upsert_mapping(mapping).to_dict()


@app.delete("/api/registry/devices/{device_key}/mappings/{function}")
async def api_delete_mapping(device_key: str, function: str) -> dict[str, bool]:
    return {"deleted": registry_store.delete_mapping(device_key, function)}


@app.get("/api/dashboard")
async def api_dashboard() -> JSONResponse:
    result: dict[str, Any] = {"version": __version__, "dry_run": load_settings().dry_run, "registry_devices": len(registry_store.list_devices())}
    try: result["tank"] = await get_tank_state()
    except Exception as exc: result["tank"] = {"error": str(exc)}
    return JSONResponse(result)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    content = """
<div class='grid'>
  <div class='card'><h2>Jádro systému</h2><div id='core' class='metric'>…</div><p class='muted'>Automatická aktualizace každých 10 sekund</p></div>
  <div class='card'><h2>💧 Dešťová nádrž</h2><div id='tank' class='metric'>…</div><p id='tankdetail'></p><div class='progress'><span id='tankbar' style='width:0%'></span></div></div>
  <div class='card'><h2>Registry</h2><div id='registry' class='metric'>…</div><p class='muted'>Počet logických zařízení</p></div>
</div>"""
    script = """
async function refresh(){try{const r=await fetch(BASE+'/api/dashboard');const d=await r.json();document.getElementById('core').textContent='OK · '+d.version;document.getElementById('registry').textContent=d.registry_devices;if(d.tank&&!d.tank.error){document.getElementById('tank').textContent=d.tank.percent+' %';document.getElementById('tankdetail').textContent=d.tank.volume_l+' l · '+d.tank.decision;document.getElementById('tankbar').style.width=Math.max(0,Math.min(100,d.tank.percent))+'%'}else{document.getElementById('tank').textContent='Chyba';document.getElementById('tankdetail').textContent=(d.tank||{}).error||''}}catch(e){document.getElementById('core').textContent='Offline'}}refresh();setInterval(refresh,10000);
"""
    return page(request, "Přehled", content, script)


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request) -> HTMLResponse:
    content = """
<div class='card'><h2>Průvodce prvním spuštěním</h2><p>OpenHEMS vyhledá známá zařízení a navrhne mapování. Nic nebude fyzicky sepnuto.</p><button class='btn' onclick='scan()'>Spustit hledání</button> <button class='btn secondary' onclick='applyAll()'>Uložit doporučení</button><p id='setupstatus' class='status'></p></div><div id='results' class='grid'></div>"""
    script = """
let discovered=[];
function h(s){return String(s??'').replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]))}
async function scan(){document.getElementById('setupstatus').textContent='Načítám entity…';const r=await fetch(BASE+'/api/discovery');const d=await r.json();discovered=d.devices||[];document.getElementById('results').innerHTML=discovered.map((dev,i)=>`<div class='card'><h2>${dev.icon} ${h(dev.name)}</h2><p class='${dev.status}'><strong>${dev.score}% · ${dev.status}</strong></p>${dev.functions.map(f=>`<label>${h(f.name)}<select data-i='${i}' data-f='${h(f.key)}'><option value=''>— nenalezeno —</option>${f.matches.map(m=>`<option value='${h(m.entity_id)}' ${f.recommended&&m.entity_id===f.recommended.entity_id?'selected':''}>${h(m.entity_id)} · ${h(m.state)} ${h(m.unit)}</option>`).join('')}</select></label><br>`).join('')}</div>`).join('');document.getElementById('setupstatus').textContent='Hledání dokončeno.'}
async function applyAll(){const devices=discovered.map((dev,i)=>{const mappings={};document.querySelectorAll(`select[data-i='${i}']`).forEach(s=>{if(s.value)mappings[s.dataset.f]=s.value});return {key:dev.key,name:dev.name,device_type:dev.device_type,mappings}});const r=await fetch(BASE+'/api/discovery/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({devices})});const d=await r.json();document.getElementById('setupstatus').textContent='Uloženo mapování: '+(d.saved_mappings??0)}
scan();
"""
    return page(request, "Průvodce", content, script)


@app.get("/devices", response_class=HTMLResponse)
async def devices(request: Request) -> HTMLResponse:
    try:
        data = discover_devices(await all_states())
        cards = []
        for dev in data:
            funcs = "".join(f"<li>{esc(f['name'])}: <strong>{f['count']}</strong></li>" for f in dev["functions"])
            cards.append(f"<div class='card'><h2>{dev['icon']} {esc(dev['name'])}</h2><p class='{dev['status']}'><strong>{dev['score']} % · {dev['status']}</strong></p><ul>{funcs}</ul></div>")
        content = "<div class='grid'>"+"".join(cards)+"</div>"
    except Exception as exc:
        content = f"<div class='card'><p class='bad'>Discovery selhalo: {esc(exc)}</p></div>"
    return page(request, "Discovery", content)


@app.get("/registry", response_class=HTMLResponse)
async def registry_page(request: Request) -> HTMLResponse:
    devices_data = registry_store.list_devices()
    cards=[]
    for dev in devices_data:
        rows="".join(f"<tr><td><code>{esc(m['function'])}</code></td><td><div class='row'><input class='grow map-input' data-device='{esc(dev['key'])}' data-function='{esc(m['function'])}' value='{esc(m['entity_id'])}' list='entities'><button class='btn save-map'>Uložit</button></div></td><td>{esc(m['source'])}</td></tr>" for m in dev['mappings']) or "<tr><td colspan='3' class='muted'>Žádné mapování</td></tr>"
        cards.append(f"<div class='card'><h2>{esc(dev['name'])}</h2><p><code>{esc(dev['key'])}</code> · {esc(dev['device_type'])}</p><table><tr><th>Funkce</th><th>Entita</th><th>Zdroj</th></tr>{rows}</table></div>")
    content="<div class='card'><h2>Device Registry</h2><p>Entity lze upravit přímo zde. Pole nabízí entity načtené z Home Assistantu.</p><p id='regstatus' class='status'></p><datalist id='entities'></datalist></div><div class='grid'>"+"".join(cards)+"</div>"
    script="""
async function loadEntities(){const r=await fetch(BASE+'/api/entities');const d=await r.json();document.getElementById('entities').innerHTML=(Array.isArray(d)?d:[]).map(e=>`<option value='${e.entity_id}'>`).join('')}
document.querySelectorAll('.save-map').forEach(b=>b.onclick=async()=>{const i=b.parentElement.querySelector('input');const r=await fetch(`${BASE}/api/registry/devices/${encodeURIComponent(i.dataset.device)}/mappings/${encodeURIComponent(i.dataset.function)}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({entity_id:i.value,source:'manual',confidence:100})});document.getElementById('regstatus').textContent=r.ok?'Mapování uloženo.':'Uložení selhalo.'});loadEntities();
"""
    return page(request, "Registry", content, script)


@app.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics(request: Request) -> HTMLResponse:
    rows=[("Python aplikace","OK",f"OpenHEMS {__version__}"),("SQLite","OK",str(DB_PATH)),("Supervisor token","OK" if token_available() else "CHYBA","dostupný" if token_available() else "chybí")]
    try: rows.append(("Home Assistant API","OK",str((await ha_get("/config")).get("version","neznámá verze"))))
    except Exception as exc: rows.append(("Home Assistant API","CHYBA",str(exc)))
    try: rows.append(("Supervisor API","OK",str((await supervisor_get("/info")).get("result","ok"))))
    except Exception as exc: rows.append(("Supervisor API","CHYBA",str(exc)))
    try:
        tank=await get_tank_state();rows.append(("Entita hladiny","OK",f"{tank['entity_id']} = {tank['level_m']} m"))
    except Exception as exc: rows.append(("Entita hladiny","CHYBA",str(exc)))
    table="".join(f"<tr><td>{esc(n)}</td><td class='{'ok' if s=='OK' else 'bad'}'><strong>{s}</strong></td><td>{esc(d)}</td></tr>" for n,s,d in rows)
    return page(request,"Diagnostika",f"<div class='card'><h2>Diagnostika</h2><table><tr><th>Část</th><th>Stav</th><th>Detail</th></tr>{table}</table></div>")
