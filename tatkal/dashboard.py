"""Loopback-only local dashboard for preparing Tatkal bookings.

This dashboard never logs in, drives the booking UI, submits a booking, or pays.
Passenger and journey data stay in the existing local JSON store.
"""
from __future__ import annotations

import json
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .assistant import speed_checklist
from .models import IST, Passenger
from .schedule import tatkal_window
from .store import Store

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#101827"><title>Tatkal Companion</title>
<style>
:root{color-scheme:dark;--bg:#0b1220;--panel:#131e30;--line:#26364d;--muted:#9aabc1;--ink:#edf4ff;--accent:#67d5b5}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:1050px;margin:auto;padding:24px 16px 56px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}h1{font-size:clamp(25px,5vw,36px);margin:0}.sub,.muted{color:var(--muted)}.sub{margin:5px 0 22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:14px}h2{font-size:18px;margin:0 0 13px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}.stat{background:var(--panel);border:1px solid var(--line);padding:14px;border-radius:14px}.stat b{display:block;font-size:25px}.stat span{font-size:12px;color:var(--muted)}label{display:block;font-size:13px;color:var(--muted);margin:10px 0 5px}input,select{width:100%;padding:11px 12px;border-radius:9px;border:1px solid var(--line);background:#0c1728;color:var(--ink);font:inherit}button,.link{display:inline-block;border:0;border-radius:9px;padding:11px 14px;background:var(--accent);color:#08251e;font-weight:700;font:inherit;cursor:pointer;text-decoration:none;margin-top:12px}.row{display:flex;gap:9px;flex-wrap:wrap;align-items:center}.card{padding:13px 0;border-top:1px solid var(--line)}.pill{display:inline-block;background:#1d3543;color:var(--accent);border-radius:30px;padding:3px 9px;font-size:12px}.notice{border:1px solid #65512b;background:#302817;color:#f7d995;border-radius:12px;padding:12px 14px;margin:16px 0}small{color:var(--muted)}#message{min-height:24px;color:var(--accent);margin-top:8px}@media(max-width:520px){main{padding:18px 12px 40px}.stat{padding:10px 8px}.stat b{font-size:20px}}
</style></head><body><main>
<div class="top"><div><h1>🚆 Tatkal Companion</h1><div class="sub">Your local travel-preparation dashboard</div></div><a class="link" href="https://www.irctc.co.in/nget/train-search" target="_blank" rel="noopener">Open official IRCTC</a></div>
<div class="notice"><b>Important:</b> This app prepares and organizes your details. It does not sign in, control IRCTC/RailOne, select seats, submit bookings or make payments. Complete those actions yourself on the official service. A confirmed ticket is verified only by the real PNR.</div>
<div class="stats"><div class="stat"><b id="paxCount">0</b><span>Saved passengers</span></div><div class="stat"><b id="journeyCount">0</b><span>Saved journeys</span></div><div class="stat"><b id="nextWindow">—</b><span>Next Tatkal opening</span></div></div>
<div class="grid"><section class="panel"><h2>Passenger master list</h2><form id="paxForm"><label>Full name</label><input name="name" required maxlength="100" placeholder="Passenger name"><div class="row"><div style="flex:1"><label>Age</label><input name="age" type="number" min="1" max="120" required></div><div style="flex:1"><label>Gender</label><select name="gender"><option value="M">Male</option><option value="F">Female</option><option value="O">Other</option></select></div></div><label>Berth preference</label><select name="berth"><option>NO PREFERENCE</option><option>LOWER</option><option>MIDDLE</option><option>UPPER</option><option>SIDE LOWER</option><option>SIDE UPPER</option></select><button type="submit">Save passenger</button></form><div id="passengers" class="muted"></div></section>
<section class="panel"><h2>Journey planner</h2><form id="journeyForm"><div class="row"><div style="flex:1"><label>From station</label><input name="origin" required maxlength="8" placeholder="e.g. BRC"></div><div style="flex:1"><label>To station</label><input name="destination" required maxlength="8" placeholder="e.g. JAT"></div></div><label>Travel date</label><input name="journey_date" type="date" required><div class="row"><div style="flex:1"><label>Class</label><select name="travel_class"><option>3A</option><option>2A</option><option>1A</option><option>3E</option><option>SL</option><option>2S</option><option>CC</option><option>EC</option><option>EA</option></select></div><div style="flex:1"><label>Train (optional)</label><input name="train" placeholder="Train number/name"></div></div><label>Passengers</label><select name="passengers" id="passengerSelect" multiple size="4"></select><small>Use Ctrl (Windows) or multi-select on mobile.</small><br><button type="submit">Save journey</button></form></section></div>
<section class="panel"><div class="row" style="justify-content:space-between"><h2>Saved journeys & readiness</h2><button type="button" id="refresh">Refresh</button></div><div id="journeys" class="muted">Loading…</div></section>
<section class="panel"><h2>Booking-time workflow</h2><ol><li>Open IRCTC or RailOne yourself and sign in.</li><li>Use your saved journey and passenger list as your preparation reference.</li><li>Check journey, class, passenger details and availability on the official interface.</li><li>Review fare and authorize payment yourself.</li><li>Only treat the booking as successful after official confirmation and a real PNR appear.</li></ol><small>Opening times are calculated locally from journey date and class. Verify current railway rules on the official service.</small></section><div id="message" role="status"></div><small>Local-only server · Data stays in your tatkal.json file · No IRCTC credentials requested or stored</small>
</main><script>
const $=s=>document.querySelector(s);function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');return d;}function msg(t){$('#message').textContent=t;}
async function refresh(){try{const d=await api('/api/state');$('#paxCount').textContent=d.passengers.length;$('#journeyCount').textContent=d.journeys.length;$('#passengers').innerHTML=d.passengers.length?d.passengers.map(p=>'<div class="card">'+esc(p.name)+' · '+esc(p.age)+esc(p.gender)+' · '+esc(p.berth_preference)+'</div>').join(''):'No passengers saved yet.';$('#passengerSelect').innerHTML=d.passengers.map(p=>'<option value="'+esc(p.name)+'">'+esc(p.name)+'</option>').join('');$('#nextWindow').textContent=d.next_window||'—';$('#journeys').innerHTML=d.journeys.length?d.journeys.map(j=>'<div class="card"><div class="row"><b>'+esc(j.from)+' → '+esc(j.to)+'</b><span class="pill">'+esc(j.travel_class)+'</span></div><div>'+esc(j.journey_date)+' · '+esc(j.train||'Train not specified')+'</div><small>Tatkal opens: '+esc(j.opens_at)+' · '+esc(j.id)+'</small><p>'+esc((j.passengers||[]).join(', ')||'No passengers selected')+'</p><small>'+esc(j.checklist_summary)+'</small></div>').join(''):'No journeys saved yet.';}catch(e){msg(e.message);}}
$('#paxForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);try{await api('/api/passengers',Object.fromEntries(f));e.target.reset();msg('Passenger saved locally.');refresh();}catch(x){msg(x.message);}});$('#journeyForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target),data=Object.fromEntries(f);data.passengers=Array.from($('#passengerSelect').selectedOptions).map(o=>o.value);try{await api('/api/journeys',data);e.target.reset();msg('Journey saved locally.');refresh();}catch(x){msg(x.message);}});$('#refresh').addEventListener('click',refresh);refresh();
</script></body></html>'''


def _json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 32768:
                raise ValueError("request body is empty or too large")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/state":
                journeys, upcoming = [], None
                for journey in store.journeys():
                    window = tatkal_window(date.fromisoformat(journey["journey_date"]), journey["travel_class"])
                    _, checks = speed_checklist(store, journey)
                    clear = sum(item.done is True for item in checks)
                    journeys.append({**journey, "opens_at": window.opens_at.strftime("%d %b %Y, %H:%M IST"), "checklist_summary": f"{clear}/{len(checks)} checks confirmed"})
                    if window.opens_at >= datetime.now(IST) and (upcoming is None or window.opens_at < upcoming):
                        upcoming = window.opens_at
                return _json(self, 200, {"passengers": store.passengers(), "journeys": journeys, "next_window": upcoming.strftime("%d %b %H:%M") if upcoming else None})
            _json(self, 404, {"error": "not found"})

        def do_POST(self) -> None:
            try:
                data, path = self._body(), urlparse(self.path).path
                if path == "/api/passengers":
                    passenger = Passenger(name=str(data.get("name", "")), age=int(data.get("age", 0)), gender=str(data.get("gender", "M")), berth_preference=str(data.get("berth", "NO PREFERENCE")))
                    return _json(self, 201, {"passenger": store.add_passenger(passenger)})
                if path == "/api/journeys":
                    journey = store.add_journey(from_station=str(data.get("origin", "")), to_station=str(data.get("destination", "")), journey_date=date.fromisoformat(str(data.get("journey_date", ""))), travel_class=str(data.get("travel_class", "")), train=str(data.get("train", "")).strip() or None, passengers=[str(n) for n in data.get("passengers", [])])
                    return _json(self, 201, {"journey": journey})
                _json(self, 404, {"error": "not found"})
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                _json(self, 400, {"error": str(exc)})
    return Handler


def serve(port: int = 8765, store_path: str = "data/tatkal.json", open_browser: bool = True) -> None:
    """Serve the dashboard on loopback only; never expose it to the network."""
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Store(store_path)))
    url = f"http://127.0.0.1:{port}"
    print(f"Tatkal Companion dashboard: {url}\nPress Ctrl+C to stop. Local device only.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run the local Tatkal Companion dashboard")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--store", default="data/tatkal.json")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    serve(args.port, args.store)


if __name__ == "__main__":
    main()
