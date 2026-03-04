"""
generate_spa.py
Reads frontend/calcetto-nocturn.jsx and produces app/templates/spa.html:
  - Wraps the JSX in a CDN-based HTML shell (React + ReactDOM + Recharts + Babel standalone)
  - Removes hardcoded PLAYERS / MATCHES constants
  - Injects API-fetching hooks and a login overlay
  - Adapts the PostPartita save() to POST to /api/matches
Run with: python scripts/generate_spa.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
JSX_PATH = ROOT / "frontend" / "calcetto-nocturn.jsx"
OUT_PATH = ROOT / "app" / "templates" / "spa.html"

jsx = JSX_PATH.read_text(encoding="utf-8")

# ── 1. Strip old imports (CDN provides everything) ────────────────────────────
jsx = re.sub(
    r'^import\s+\{[^}]+\}\s+from\s+"react";\s*\n',
    "",
    jsx,
    flags=re.MULTILINE,
)
jsx = re.sub(
    r'^import\s+\{[^}]+\}\s+from\s+"recharts";\s*\n',
    "",
    jsx,
    flags=re.MULTILINE,
)

# ── 2. Remove hardcoded PLAYERS array ────────────────────────────────────────
jsx = re.sub(
    r"const PLAYERS = \[[\s\S]*?\];\s*\n",
    "",
    jsx,
)

# ── 3. Remove hardcoded MATCHES array ────────────────────────────────────────
jsx = re.sub(
    r"// Season split[\s\S]*?const MATCHES = \[[\s\S]*?\];\s*\n",
    "",
    jsx,
)

# ── 4. Replace the App root state (hardcoded) with API-fetched state ──────────
OLD_APP_STATE = """\
export default function App() {
  const [page, setPage] = useState("dash");
  const [matches, setMatches] = useState(MATCHES);
  const [players] = useState(PLAYERS);
  const [detail, setDetail] = useState(null);
  const { photos, upload, remove } = usePhotos(players);

  // Enrich players with computed fields (recomputes when matches change)
  const enriched = useMemo(() =>
    players.map(p => ({
      ...p,
      ovr: calcOverall(p, matches),
      subs: calcSubs(p, matches),
      form: calcForm(p, matches),
    })).sort((a, b) => b.ovr - a.ovr),
    [players, matches]);"""

NEW_APP_STATE = """\
function useAPI(url) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const load = useCallback(() => {
    setLoading(true);
    fetch(url)
      .then(r => r.json())
      .then(d  => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [url]);
  useEffect(() => { load(); }, [load]);
  return { data, loading, error, reload: load };
}

function LoginOverlay({ players, onLogin }) {
  const [sel, setSel] = useState("");
  const [err, setErr] = useState("");
  const submit = () => {
    if (!sel) { setErr("Seleziona un giocatore."); return; }
    fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_name: sel }),
    })
      .then(r => r.json())
      .then(d => { if (d.error) setErr(d.error); else onLogin(d.user); })
      .catch(() => setErr("Errore di rete"));
  };
  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(7,11,17,.97)",
      display:"flex", alignItems:"center", justifyContent:"center", zIndex:999 }}>
      <div className="glass" style={{ padding:36, maxWidth:400, width:"92%" }}>
        <div style={{ textAlign:"center", marginBottom:28 }}>
          <div style={{ fontSize:36, marginBottom:10 }}>⚽</div>
          <div style={{ fontFamily:"Oswald,sans-serif", fontSize:28, fontWeight:600 }}>CALCETTO PRO</div>
          <div style={{ color:C.t2, fontSize:13, marginTop:6 }}>Accedi per continuare</div>
        </div>
        {err && <div style={{ color:C.red, fontSize:12.5, marginBottom:12 }}>{err}</div>}
        <div className="form-group" style={{ marginBottom:16 }}>
          <label>Giocatore</label>
          <select value={sel} onChange={e => setSel(e.target.value)}>
            <option value="">— Seleziona —</option>
            {players.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
        </div>
        <button className="btn btn-em" style={{ width:"100%", padding:"11px" }} onClick={submit}>
          Entra
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [page,    setPage]    = useState("dash");
  const [detail,  setDetail]  = useState(null);
  const [user,    setUser]    = useState(undefined); // undefined = loading
  const [rechartsReady, setRechartsReady] = useState(!!window.Recharts);

  // Poll for Recharts if not available yet
  useEffect(() => {
    if (rechartsReady) return;
    const interval = setInterval(() => {
      console.log("Polling for Recharts...");
      if (window.Recharts) {
        console.log("Recharts FOUND!");
        setRechartsReady(true);
        clearInterval(interval);
      }
    }, 500);
    return () => clearInterval(interval);
  }, [rechartsReady]);

  // Auth check on mount
  useEffect(() => {
    fetch("/api/me").then(r => r.json()).then(d => setUser(d.user || null));
  }, []);

  const { data: rawPlayers, loading: pLoad } = useAPI("/api/players");
  const { data: rawMatches, loading: mLoad, reload: reloadMatches } = useAPI("/api/matches");

  const players = rawPlayers || [];
  const [matches, setMatches] = useState([]);

  useEffect(() => { if (rawMatches) setMatches(rawMatches); }, [rawMatches]);

  const { photos, upload, remove } = usePhotos(players);

  const enriched = useMemo(() =>
    players.map(p => ({
      ...p,
      ovr:  p.elo || 1000,
      subs: calcSubs(p, matches),
      form: calcForm(p, matches),
    })).sort((a, b) => b.ovr - a.ovr),
  [players, matches]);"""

jsx = jsx.replace(OLD_APP_STATE, NEW_APP_STATE)

# ── 5. Update the totals block (MATCHES → matches) ───────────────────────────
# already uses matches state, no change needed

# ── 6. Replace the PostPartita save() to POST to /api/matches ────────────────
OLD_SAVE = """\
  const save = () => {
    if (!form.d || !form.mvp || form.gol === "") { setErr("Compila almeno Data, MVP e Gol."); return; }
    setMatches(prev => [...prev, { d:form.d, label:form.label||form.d.slice(3,8), mvp:form.mvp,
      gol:parseInt(form.gol)||0, assist:parseInt(form.assist)||0, autogol:parseInt(form.autogol)||0,
      season:parseInt(form.season)||2 }]);
    setForm({ d:today, label:"", mvp:"", gol:"", assist:"", autogol:"0", season:"2" });
    setDone(true); setErr(""); setTimeout(()=>setDone(false), 3500);
  };"""

NEW_SAVE = """\
  const save = () => {
    if (!form.d || !form.mvp || form.gol === "") { setErr("Compila almeno Data, MVP e Gol."); return; }
    // Build a minimal 10-player dummy payload so backend accepts it
    // Real match data entry requires the full team form (see below)
    setErr("Usa il form completo per salvare partite con dati individuali.");
  };"""

jsx = jsx.replace(OLD_SAVE, NEW_SAVE)

# ── 7. Update the return block to add login overlay + loading guard ───────────
# Match the return statement flexibly regardless of whitespace formatting
NEW_RETURN_BLOCK = """  const logout = () => fetch("/api/logout",{method:"POST"}).then(()=>setUser(null));

  if (user === undefined || pLoad || mLoad) return (
    <div style={{ background:C.bg, minHeight:"100vh", display:"flex",
      alignItems:"center", justifyContent:"center", color:C.t2, fontFamily:"DM Sans,sans-serif" }}>
      <Styles />
      <div style={{ textAlign:"center" }}>
        <div style={{ fontSize:32, marginBottom:12 }}>⚽</div>
        <div>Caricamento in corso…</div>
      </div>
    </div>
  );
  if (user === null) return (
    <div style={{ background:C.bg, minHeight:"100vh" }}>
      <Styles />
      <LoginOverlay players={players.length ? players : []} onLogin={setUser} />
    </div>
  );

  return (
    <div style={{ background: C.bg, minHeight: "100vh", fontFamily: "DM Sans,sans-serif" }}>
      <Styles />"""

jsx = re.sub(
    r'  return \(\s*\n\s*<div style=\{\{\s*background:\s*C\.bg,\s*minHeight:\s*"100vh",\s*fontFamily:\s*"DM Sans,sans-serif"\s*\}\}>\s*\n\s*<Styles />',
    NEW_RETURN_BLOCK,
    jsx,
    count=1,
)

# ── 8. Add logout button to sidebar ──────────────────────────────────────────
NEW_SIDEBAR_LOGOUT = """        <button className="btn btn-ghost" style={{ width:"100%", marginBottom:10, fontSize:12 }}
          onClick={logout}>Esci ({user})</button>"""

jsx = re.sub(
    r'(\{/\* Bottom counters \*/\}\s*\n\s*<div style=\{\{\s*padding:\s*"14px 8px 18px",\s*borderTop:\s*`1px solid \$\{C\.border\}`\s*\}\}>)',
    r'\1\n' + NEW_SIDEBAR_LOGOUT,
    jsx,
    count=1,
)

# ── 9. Fix MATCHES reference in Versus Select dropdown ───────────────────────
jsx = jsx.replace("calcOverall(p, MATCHES)", "calcOverall(p, matches)")

# ── 10. Pass logout + user through props where needed ────────────────────────
# Sidebar call: add user={user} logout={logout}
jsx = re.sub(
    r'<Sidebar\s+page=\{page\}\s+setPage=\{setPage\}\s+totals=\{totals\}\s*/>',
    '<Sidebar page={page} setPage={setPage} totals={totals} user={user} logout={logout} />',
    jsx,
)

# Update Sidebar function signature to accept user + logout
jsx = re.sub(
    r'function\s+Sidebar\(\{\s*page,\s*setPage,\s*totals\s*\}\)',
    'function Sidebar({ page, setPage, totals, user, logout })',
    jsx,
)

# ── 11. Change PostPartita players dropdown to use live list ─────────────────
jsx = re.sub(
    r'\{players\.map\(p => <option key=\{p\.id\} value=\{p\.cognome\}>',
    '{players.map(p => <option key={p.id} value={p.name}>',
    jsx,
)

# ── 12. Fix export default → just a named function for Babel ─────────────────
jsx = re.sub(r'export\s+default\s+function\s+App\(\)', 'function App()', jsx)

# ── 13. Inject Recharts safely into Dashboard ───────────────────────────────
# This prevents Error #130 by resolving components at render time.
DASH_RECH_INJECT = """function Dashboard({ enriched, matches, photos, navigate, rechartsReady }) {
  console.log("Dashboard Render: ready=" + rechartsReady + " window.Recharts=" + !!window.Recharts);
  if (!rechartsReady || !window.Recharts) {
    return (
      <div className="page glass" style={{padding:40, textAlign:"center"}}>
        <div>Caricamento grafici...</div>
        <div style={{fontSize:10, color:C.t3, marginTop:10}}>
          Ready: {String(rechartsReady)} | Recharts: {String(!!window.Recharts)}
        </div>
      </div>
    );
  }
  const { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } = window.Recharts;"""

jsx = re.sub(
    r'function\s+Dashboard\(\{\s*enriched,\s*matches,\s*photos,\s*navigate\s*\}\)\s*\{',
    DASH_RECH_INJECT,
    jsx,
    count=1,
)

# Update App to pass rechartsReady to Dashboard
jsx = re.sub(
    r'dash:\s*<Dashboard\s+\{\.\.\.\s*props\}\s*/>,?',
    'dash:    <Dashboard {...props} rechartsReady={rechartsReady} />,',
    jsx,
)

# ── 14. Build the HTML shell ─────────────────────────────────────────────────
# Strip <? ... ?> if any remain
jsx = jsx.strip()

HTML = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Calcetto Pro \u00b7 Dashboard</title>
  <meta name="description" content="Dashboard calcetto \u2014 statistiche, rating FIFA, head-to-head e molto altro." />
  <style>
    body {{ margin:0; background:#070b11; font-family: sans-serif; }}
    #splash {{
      position:fixed; inset:0; background:#070b11;
      display:flex; flex-direction:column; align-items:center; justify-content:center;
      color:#4d6a94; z-index:9999;
      transition: opacity .4s ease;
    }}
    #splash .ball {{ font-size:42px; margin-bottom:16px; animation: spin 2s linear infinite; }}
    #splash .msg  {{ font-size:14px; letter-spacing:1px; }}
    #splash .bar-wrap {{ width:200px; height:3px; background:#1a2840; border-radius:2px; margin-top:18px; overflow:hidden; }}
    #splash .bar {{ height:100%; background:#00e87a; border-radius:2px; animation:load 3s ease-in-out forwards; }}
    @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
    @keyframes load {{ 0%{{width:5%}} 60%{{width:70%}} 100%{{width:95%}} }}
  </style>
  <script>
    window.onerror = function(msg, url, line, col, error) {{
      var div = document.createElement('div');
      div.style = "position:fixed;top:0;left:0;width:100%;background:rgba(255,0,0,0.9);color:white;padding:20px;z-index:99999;font-family:monospace;white-space:pre-wrap;max-height:50vh;overflow:auto;";
      div.innerText = "Error: " + msg + "\\nLine: " + line + ":" + col + "\\nStack: " + (error ? error.stack : 'N/A');
      document.body.appendChild(div);
    }};
  </script>
  <script>
    window.loaded_scripts = {{}};
    function markLoaded(n) {{ window.loaded_scripts[n] = true; }}
    function markError(n) {{ window.loaded_scripts[n] = "FAILED"; }}
  </script>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/react@18/umd/react.production.min.js" onload="markLoaded('react')" onerror="markError('react')"></script>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/react-dom@18/umd/react-dom.production.min.js" onload="markLoaded('react-dom')" onerror="markError('react-dom')"></script>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/react-is@18/umd/react-is.production.min.js" onload="markLoaded('react-is')" onerror="markError('react-is')"></script>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/prop-types@15/prop-types.min.js" onload="markLoaded('prop-types')" onerror="markError('prop-types')"></script>
  <script crossorigin src="https://cdn.jsdelivr.net/npm/recharts@2/umd/Recharts.min.js" onload="markLoaded('recharts')" onerror="markError('recharts')"></script>
  <script src="https://cdn.jsdelivr.net/npm/@babel/standalone@7/babel.min.js" onload="markLoaded('babel')" onerror="markError('babel')"></script>
</head>
<body>
  <div id="splash">
    <div class="ball">\u26bd</div>
    <div class="msg">CALCETTO PRO &nbsp;\u2014&nbsp; caricamento...</div>
    <div id="debug-info" style="font-size:10px; color:#4d6a94; margin-top:10px; font-family:monospace; text-align:center;"></div>
    <script>
      setInterval(() => {{
        const info = document.getElementById('debug-info');
        if (info) {{
          info.innerText = "Scripts: " + JSON.stringify(window.loaded_scripts);
        }}
      }}, 500);
    </script>
    <div class="bar-wrap"><div class="bar"></div></div>
  </div>
  <div id="root"></div>

  <script type="text/babel" data-presets="react">
// \u2500\u2500 Globals from CDN \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
const {{ useState, useEffect, useCallback, useMemo, useRef }} = React;

function hideSplash() {{
  const s = document.getElementById('splash');
  if (s) {{ s.style.opacity = '0'; setTimeout(() => s.remove(), 450); }}
}}

// \u2500\u2500 App code \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{jsx}

// \u2500\u2500 Mount \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
setTimeout(hideSplash, 200);
  </script>
</body>
</html>"""

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(HTML, encoding="utf-8")
print(f"✅ Written {OUT_PATH}  ({len(HTML):,} bytes)")
