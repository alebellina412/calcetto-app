import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar
} from "recharts";

// ═══════════════════════════════════════════════════════════
// DESIGN TOKENS
// ═══════════════════════════════════════════════════════════
const C = {
  bg: "#070b11",
  surface: "#0c1220",
  surface2: "#111b2e",
  surface3: "#162236",
  border: "#1a2840",
  borderHi: "#243656",
  em: "#00e87a",   // emerald — player / accent
  emDim: "#00e87a18",
  emMid: "#00e87a40",
  blue: "#3b82f6",   // electric blue — player 2 / versus
  blueDim: "#3b82f618",
  blueMid: "#3b82f640",
  gold: "#f5a623",
  goldDim: "#f5a62318",
  red: "#ff3b5c",
  redDim: "#ff3b5c15",
  t1: "#dce9ff",   // primary text
  t2: "#4d6a94",   // secondary text
  t3: "#253754",   // muted text
};

// ═══════════════════════════════════════════════════════════
// GLOBAL STYLES
// ═══════════════════════════════════════════════════════════
const Styles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { font-size: 16px; }
    body { background: ${C.bg}; font-family: 'DM Sans', sans-serif; color: ${C.t1}; -webkit-font-smoothing: antialiased; }
    ::-webkit-scrollbar { width: 3px; height: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 2px; }
    ::selection { background: ${C.emMid}; color: ${C.em}; }

    @keyframes fadeUp   { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
    @keyframes fadeIn   { from{opacity:0} to{opacity:1} }
    @keyframes scaleIn  { from{opacity:0;transform:scale(.95)} to{opacity:1;transform:scale(1)} }
    @keyframes slidLeft { from{opacity:0;transform:translateX(-20px)} to{opacity:1;transform:translateX(0)} }
    @keyframes slidRight{ from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }
    @keyframes spin     { to{transform:rotate(360deg)} }
    @keyframes pulse    { 0%,100%{opacity:1}50%{opacity:.5} }
    @keyframes glowPulse{ 0%,100%{box-shadow:0 0 16px ${C.emMid}}50%{box-shadow:0 0 32px ${C.em}60} }
    @keyframes barFill  { from{width:0%} to{width:var(--target-w)} }
    @keyframes countUp  { from{opacity:0;transform:scale(.8)} to{opacity:1;transform:scale(1)} }

    .page     { animation: fadeUp .4s cubic-bezier(.16,1,.3,1) both; }
    .fade-in  { animation: fadeIn .3s ease both; }
    .scale-in { animation: scaleIn .25s cubic-bezier(.16,1,.3,1) both; }
    .slid-l   { animation: slidLeft  .4s cubic-bezier(.16,1,.3,1) both; }
    .slid-r   { animation: slidRight .4s cubic-bezier(.16,1,.3,1) both; }
    .count-up { animation: countUp .5s cubic-bezier(.16,1,.3,1) both; }

    .glass {
      background: ${C.surface};
      border: 1px solid ${C.border};
      border-radius: 14px;
      backdrop-filter: blur(12px);
    }
    .glass2 {
      background: ${C.surface2};
      border: 1px solid ${C.border};
      border-radius: 10px;
    }

    .nav-item {
      display: flex; align-items: center; gap: 10px;
      padding: 9px 11px; border-radius: 9px;
      cursor: pointer; transition: all .18s ease;
      color: ${C.t2}; font-size: 13.5px; font-weight: 500;
      border: 1px solid transparent;
      user-select: none;
    }
    .nav-item:hover { background: ${C.surface2}; color: ${C.t1}; border-color: ${C.border}; }
    .nav-item.act   { background: ${C.emDim}; color: ${C.em}; border-color: ${C.emMid}; }
    .nav-item.act svg { color: ${C.em}; }

    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 7px;
      cursor: pointer; border: none; border-radius: 9px;
      font-family: 'DM Sans', sans-serif; font-weight: 600;
      transition: all .18s; white-space: nowrap;
    }
    .btn-em   { background: ${C.em}; color: #04120a; font-size: 13px; padding: 9px 18px; }
    .btn-em:hover { background: #00ff87; transform: translateY(-1px); box-shadow: 0 6px 22px ${C.emMid}; }
    .btn-em:disabled { opacity:.3; cursor:not-allowed; transform:none; box-shadow:none; }
    .btn-ghost { background: transparent; color: ${C.t2}; border: 1px solid ${C.border}; font-size: 13px; padding: 8px 16px; }
    .btn-ghost:hover { background: ${C.surface2}; color: ${C.t1}; border-color: ${C.borderHi}; }
    .btn-icon { background: ${C.surface2}; border: 1px solid ${C.border}; color: ${C.t2}; padding: 7px; border-radius: 8px; cursor:pointer; transition:all .18s; display:inline-flex;align-items:center;justify-content:center; }
    .btn-icon:hover { border-color: ${C.em}; color: ${C.em}; background: ${C.emDim}; }
    .btn-blue { background: ${C.blue}; color: #fff; font-size: 13px; padding: 9px 18px; }
    .btn-blue:hover { background: #60a5fa; transform:translateY(-1px); box-shadow:0 6px 22px ${C.blueMid}; }

    .tag { display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border-radius:99px; font-size:11px; font-weight:600; letter-spacing:.3px; }
    .tag-em   { background:${C.emDim};   color:${C.em};   border:1px solid ${C.emMid}; }
    .tag-blue { background:${C.blueDim}; color:${C.blue}; border:1px solid ${C.blueMid}; }
    .tag-gold { background:${C.goldDim}; color:${C.gold}; border:1px solid ${C.gold}40; }
    .tag-red  { background:${C.redDim};  color:${C.red};  border:1px solid ${C.red}30; }

    .form-group label { display:block; font-size:11px; font-weight:600; letter-spacing:.9px; color:${C.t2}; margin-bottom:6px; text-transform:uppercase; }
    .form-group input, .form-group select, .form-group textarea {
      width:100%; background:${C.surface2}; border:1px solid ${C.border};
      border-radius:8px; color:${C.t1}; font-family:'DM Sans',sans-serif;
      font-size:13.5px; padding:9px 12px; transition:border-color .15s, box-shadow .15s;
    }
    .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
      outline:none; border-color:${C.em}; box-shadow:0 0 0 3px ${C.emDim};
    }
    select option { background:${C.surface2}; }

    .tr { transition: all .18s; }
    .tr-row { border-bottom: 1px solid ${C.border}; transition: background .15s; }
    .tr-row:last-child { border-bottom: none; }
    .tr-row:hover { background: ${C.surface2}; }
    .sort-col { cursor:pointer; user-select:none; transition:color .15s; }
    .sort-col:hover { color:${C.em} !important; }

    .card-player {
      cursor:pointer; transition:transform .28s cubic-bezier(.16,1,.3,1), box-shadow .28s;
    }
    .card-player:hover { transform:translateY(-8px); }
    .card-player:hover .card-inner { box-shadow: 0 20px 60px rgba(0,0,0,.6); }

    .modal-bg {
      position:fixed; inset:0; background:rgba(7,11,17,.88);
      z-index:500; display:flex; align-items:center; justify-content:center;
      backdrop-filter:blur(6px); animation:fadeIn .2s ease;
    }
    .modal { background:${C.surface}; border:1px solid ${C.border}; border-radius:18px;
      padding:28px; max-width:560px; width:92%; max-height:90vh; overflow-y:auto;
      animation:scaleIn .22s cubic-bezier(.16,1,.3,1); }

    .tooltip-custom { background:${C.surface2} !important; border:1px solid ${C.border} !important;
      border-radius:9px !important; font-family:'DM Sans',sans-serif !important;
      font-size:12px !important; color:${C.t1} !important; box-shadow:0 8px 32px rgba(0,0,0,.5) !important; }

    /* Versus specific */
    .vs-divider { position:relative; display:flex; align-items:center; justify-content:center; }
    .vs-divider::before { content:''; position:absolute; left:0; right:0; height:1px; background:${C.border}; }
    .vs-badge {
      position:relative; background:${C.surface3}; border:2px solid ${C.border};
      border-radius:50%; width:44px; height:44px; display:flex; align-items:center; justify-content:center;
      font-family:'Oswald',sans-serif; font-size:15px; font-weight:700; color:${C.t2};
      z-index:1;
    }

    .compare-bar-wrap { display:flex; align-items:center; gap:0; }
    .compare-bar-p1 { height:4px; border-radius:2px 0 0 2px; transition:width .6s cubic-bezier(.16,1,.3,1); }
    .compare-bar-p2 { height:4px; border-radius:0 2px 2px 0; transition:width .6s cubic-bezier(.16,1,.3,1); }

    .winner-glow-em   { animation: glowPulse 2.5s ease-in-out infinite; }
    .winner-glow-blue { animation: none; box-shadow: 0 0 20px ${C.blueMid}; }

    /* noise overlay */
    .noise::after {
      content:''; position:absolute; inset:0; border-radius:inherit; pointer-events:none;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
      opacity:.3; mix-blend-mode:overlay;
    }

    .scan-line::before {
      content:''; position:absolute; inset:0; border-radius:inherit; pointer-events:none;
      background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,232,122,.015) 2px, rgba(0,232,122,.015) 4px);
    }
  `}</style>
);

// ═══════════════════════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════════════════════
const PLAYERS = [
  { id: "lustrati", cognome: "Lustrati", nome: "Matteo", partite: 35, vittorie: 14, vittorie_pct: 40, mvp: 2, gol: 68, gol_pp: 1.94, assist: 70, assist_pp: 2.00, ga: 138, ga_pp: 3.94, intonso: 2, autogol: 1 },
  { id: "porcu", cognome: "Porcu", nome: "Riccardo", partite: 39, vittorie: 19, vittorie_pct: 49, mvp: 3, gol: 84, gol_pp: 2.15, assist: 35, assist_pp: 0.90, ga: 119, ga_pp: 3.05, intonso: 3, autogol: 3 },
  { id: "martinelli", cognome: "Martinelli", nome: "Alessio", partite: 35, vittorie: 18, vittorie_pct: 51, mvp: 5, gol: 55, gol_pp: 1.57, assist: 50, assist_pp: 1.43, ga: 105, ga_pp: 3.00, intonso: 1, autogol: 0 },
  { id: "waheb", cognome: "Waheb", nome: "Marco", partite: 30, vittorie: 9, vittorie_pct: 30, mvp: 3, gol: 57, gol_pp: 1.90, assist: 42, assist_pp: 1.40, ga: 99, ga_pp: 3.30, intonso: 0, autogol: 3 },
  { id: "tovoli", cognome: "Tovoli", nome: "Filippo", partite: 37, vittorie: 18, vittorie_pct: 49, mvp: 2, gol: 57, gol_pp: 1.54, assist: 37, assist_pp: 1.00, ga: 94, ga_pp: 2.54, intonso: 3, autogol: 0 },
  { id: "ascarelli", cognome: "Ascarelli", nome: "Andrea", partite: 37, vittorie: 21, vittorie_pct: 57, mvp: 1, gol: 41, gol_pp: 1.11, assist: 41, assist_pp: 1.11, ga: 82, ga_pp: 2.22, intonso: 4, autogol: 3 },
  { id: "succo", cognome: "Succo", nome: "Francesco", partite: 14, vittorie: 4, vittorie_pct: 29, mvp: 2, gol: 47, gol_pp: 3.36, assist: 12, assist_pp: 0.86, ga: 59, ga_pp: 4.21, intonso: 0, autogol: 0 },
  { id: "porretti", cognome: "Porretti", nome: "Andrea N.", partite: 40, vittorie: 14, vittorie_pct: 35, mvp: 5, gol: 26, gol_pp: 0.65, assist: 32, assist_pp: 0.80, ga: 58, ga_pp: 1.45, intonso: 5, autogol: 3 },
  { id: "tomassetti", cognome: "Tomassetti", nome: "Federico", partite: 19, vittorie: 9, vittorie_pct: 47, mvp: 1, gol: 36, gol_pp: 1.89, assist: 6, assist_pp: 0.32, ga: 42, ga_pp: 2.21, intonso: 1, autogol: 3 },
  { id: "petroni", cognome: "Petroni", nome: "Leonardo", partite: 10, vittorie: 4, vittorie_pct: 40, mvp: 3, gol: 30, gol_pp: 3.00, assist: 7, assist_pp: 0.70, ga: 37, ga_pp: 3.70, intonso: 1, autogol: 0 },
  { id: "pucci", cognome: "Pucci", nome: "Valerio", partite: 23, vittorie: 6, vittorie_pct: 26, mvp: 1, gol: 20, gol_pp: 0.87, assist: 10, assist_pp: 0.43, ga: 30, ga_pp: 1.30, intonso: 6, autogol: 0 },
  { id: "brescia", cognome: "Brescia", nome: "Leonardo", partite: 13, vittorie: 4, vittorie_pct: 31, mvp: 0, gol: 18, gol_pp: 1.38, assist: 8, assist_pp: 0.62, ga: 26, ga_pp: 2.00, intonso: 0, autogol: 0 },
  { id: "campisano", cognome: "Campisano", nome: "Giorgio", partite: 15, vittorie: 7, vittorie_pct: 47, mvp: 1, gol: 9, gol_pp: 0.60, assist: 14, assist_pp: 0.93, ga: 23, ga_pp: 1.53, intonso: 4, autogol: 3 },
  { id: "falorni", cognome: "Falorni", nome: "Giovanni", partite: 4, vittorie: 1, vittorie_pct: 25, mvp: 3, gol: 16, gol_pp: 4.00, assist: 3, assist_pp: 0.75, ga: 19, ga_pp: 4.75, intonso: 0, autogol: 0 },
  { id: "petrassi", cognome: "Petrassi", nome: "Alessandro", partite: 9, vittorie: 4, vittorie_pct: 44, mvp: 0, gol: 15, gol_pp: 1.67, assist: 3, assist_pp: 0.33, ga: 18, ga_pp: 2.00, intonso: 0, autogol: 0 },
  { id: "dangelo", cognome: "D'Angelo", nome: "Giulio", partite: 7, vittorie: 3, vittorie_pct: 43, mvp: 2, gol: 11, gol_pp: 1.57, assist: 5, assist_pp: 0.71, ga: 16, ga_pp: 2.29, intonso: 2, autogol: 0 },
  { id: "paciolla", cognome: "Paciolla", nome: "Emanuele", partite: 5, vittorie: 1, vittorie_pct: 20, mvp: 0, gol: 4, gol_pp: 0.80, assist: 4, assist_pp: 0.80, ga: 8, ga_pp: 1.60, intonso: 2, autogol: 0 },
];

// Season split: S1=first 24 matches, S2=last 20
const MATCHES = [
  { d: "13/03/24", label: "Mar'24", mvp: "Lustrati", gol: 16, assist: 0, autogol: 1, season: 1 },
  { d: "28/03/24", label: "Mar'24", mvp: "Lustrati", gol: 21, assist: 0, autogol: 1, season: 1 },
  { d: "10/04/24", label: "Apr'24", mvp: "Porretti", gol: 12, assist: 9, autogol: 0, season: 1 },
  { d: "17/04/24", label: "Apr'24", mvp: "Martinelli", gol: 22, assist: 15, autogol: 0, season: 1 },
  { d: "16/05/24", label: "Mag'24", mvp: "Filipponi", gol: 14, assist: 11, autogol: 0, season: 1 },
  { d: "30/05/24", label: "Mag'24", mvp: "Waheb", gol: 19, assist: 12, autogol: 2, season: 1 },
  { d: "06/06/24", label: "Giu'24", mvp: "Filipponi", gol: 20, assist: 13, autogol: 1, season: 1 },
  { d: "13/06/24", label: "Giu'24", mvp: "D'Angelo", gol: 9, assist: 7, autogol: 0, season: 1 },
  { d: "09/10/24", label: "Ott'24", mvp: "Martinelli", gol: 9, assist: 7, autogol: 1, season: 1 },
  { d: "16/10/24", label: "Ott'24", mvp: "Porcu", gol: 19, assist: 10, autogol: 1, season: 1 },
  { d: "30/10/24", label: "Ott'24", mvp: "Martinelli", gol: 18, assist: 11, autogol: 0, season: 1 },
  { d: "06/11/24", label: "Nov'24", mvp: "Waheb", gol: 21, assist: 14, autogol: 0, season: 1 },
  { d: "20/11/24", label: "Nov'24", mvp: "Federico", gol: 17, assist: 9, autogol: 0, season: 1 },
  { d: "24/11/24", label: "Nov'24", mvp: "Melegoni", gol: 17, assist: 12, autogol: 0, season: 1 },
  { d: "04/12/24", label: "Dic'24", mvp: "Porretti", gol: 19, assist: 12, autogol: 1, season: 1 },
  { d: "22/12/24", label: "Dic'24", mvp: "Spina G.", gol: 10, assist: 7, autogol: 1, season: 1 },
  { d: "08/01/25", label: "Gen'25", mvp: "Palermo", gol: 14, assist: 8, autogol: 0, season: 1 },
  { d: "29/01/25", label: "Gen'25", mvp: "D'Angelo", gol: 21, assist: 17, autogol: 0, season: 1 },
  { d: "05/03/25", label: "Mar'25", mvp: "Ascarelli", gol: 22, assist: 14, autogol: 0, season: 1 },
  { d: "19/03/25", label: "Mar'25", mvp: "Porretti", gol: 20, assist: 16, autogol: 0, season: 1 },
  { d: "26/03/25", label: "Mar'25", mvp: "Succo", gol: 21, assist: 10, autogol: 0, season: 1 },
  { d: "02/04/25", label: "Apr'25", mvp: "Martinelli", gol: 22, assist: 15, autogol: 1, season: 1 },
  { d: "09/04/25", label: "Apr'25", mvp: "Petroni", gol: 17, assist: 13, autogol: 1, season: 1 },
  { d: "23/04/25", label: "Apr'25", mvp: "Petrassi", gol: 11, assist: 7, autogol: 0, season: 1 },
  { d: "07/05/25", label: "Mag'25", mvp: "Succo", gol: 14, assist: 6, autogol: 0, season: 2 },
  { d: "21/05/25", label: "Mag'25", mvp: "Minotti", gol: 22, assist: 15, autogol: 0, season: 2 },
  { d: "04/06/25", label: "Giu'25", mvp: "Tovoli", gol: 17, assist: 11, autogol: 0, season: 2 },
  { d: "02/07/25", label: "Lug'25", mvp: "Falorni", gol: 32, assist: 19, autogol: 2, season: 2 },
  { d: "16/07/25", label: "Lug'25", mvp: "Porcu", gol: 24, assist: 15, autogol: 0, season: 2 },
  { d: "30/07/25", label: "Lug'25", mvp: "Falorni", gol: 14, assist: 11, autogol: 0, season: 2 },
  { d: "03/09/25", label: "Set'25", mvp: "Waheb", gol: 16, assist: 8, autogol: 0, season: 2 },
  { d: "06/09/25", label: "Set'25", mvp: "Porcu", gol: 12, assist: 9, autogol: 0, season: 2 },
  { d: "10/09/25", label: "Set'25", mvp: "Petroni", gol: 19, assist: 13, autogol: 0, season: 2 },
  { d: "18/09/25", label: "Set'25", mvp: "Falorni", gol: 18, assist: 10, autogol: 1, season: 2 },
  { d: "01/10/25", label: "Ott'25", mvp: "Paolo", gol: 21, assist: 13, autogol: 1, season: 2 },
  { d: "08/10/25", label: "Ott'25", mvp: "Porretti", gol: 15, assist: 7, autogol: 1, season: 2 },
  { d: "22/10/25", label: "Ott'25", mvp: "Tomassetti", gol: 17, assist: 10, autogol: 0, season: 2 },
  { d: "05/11/25", label: "Nov'25", mvp: "Porretti", gol: 17, assist: 11, autogol: 1, season: 2 },
  { d: "12/11/25", label: "Nov'25", mvp: "Martinelli", gol: 16, assist: 8, autogol: 2, season: 2 },
  { d: "26/11/25", label: "Nov'25", mvp: "Tovoli", gol: 18, assist: 9, autogol: 0, season: 2 },
  { d: "03/12/25", label: "Dic'25", mvp: "Petroni", gol: 12, assist: 7, autogol: 0, season: 2 },
  { d: "07/01/26", label: "Gen'26", mvp: "Campisano", gol: 17, assist: 12, autogol: 0, season: 2 },
  { d: "12/01/26", label: "Gen'26", mvp: "Pucci", gol: 10, assist: 5, autogol: 0, season: 2 },
  { d: "21/01/26", label: "Gen'26", mvp: "Minotti", gol: 17, assist: 11, autogol: 0, season: 2 },
];

// ═══════════════════════════════════════════════════════════
// ALGORITHM — "MOMENTO DI FORMA"
// ═══════════════════════════════════════════════════════════
const norm = (v, lo, hi) => Math.max(0, Math.min(1, (v - lo) / (hi - lo)));

function calcSeasonTrend(player, matches) {
  const name = player.cognome;
  const s1 = matches.filter(m => m.season === 1);
  const s2 = matches.filter(m => m.season === 2);
  const s1mvp = s1.filter(m => m.mvp === name).length / Math.max(s1.length, 1);
  const s2mvp = s2.filter(m => m.mvp === name).length / Math.max(s2.length, 1);
  const delta = s2mvp - s1mvp;           // positive = improving
  return norm(delta, -0.12, 0.18);       // centered, S2 improvement → higher score
}

function calcForm(player, matches) {
  // Based on MVP appearances in last 12 matches
  const recent = matches.slice(-12);
  const hits = recent.filter(m => m.mvp === player.cognome).length;
  return Math.min(1, hits / 2.5);
}

function calcOverall(player, matches) {
  const reliability = Math.min(1, player.partite / 14);  // dampens low-sample players
  // Subscores
  const gaScore = norm(player.ga_pp, 0, 5.0);  // G+A per partita
  const mvpRate = player.mvp / Math.max(player.partite, 1);
  const mvpScore = norm(mvpRate, 0, 0.30);
  const trend = calcSeasonTrend(player, matches);
  const winScore = norm(player.vittorie_pct, 15, 68);
  // Weights: G+A 45%, MVP 25%, Season trend 20%, Win 10%
  const composite = gaScore * 0.45 + mvpScore * 0.25 + trend * 0.20 + winScore * 0.10;
  const dampened = composite * reliability + 0.40 * (1 - reliability);
  return Math.round(54 + dampened * 43);  // range ≈ 56–97
}

function calcSubs(player, matches) {
  return {
    GOL: Math.round(norm(player.gol_pp, 0, 4.5) * 99),
    ASS: Math.round(norm(player.assist_pp, 0, 2.5) * 99),
    MVP: Math.round(norm(player.mvp / Math.max(player.partite, 1), 0, 0.30) * 99),
    WIN: Math.round(norm(player.vittorie_pct, 15, 68) * 99),
    FORMA: Math.round(calcForm(player, matches) * 99),
  };
}

function tier(ovr) {
  if (ovr >= 1200) return { label: "LEGGENDA", color: C.gold, cls: "legenda", glow: `0 0 28px ${C.gold}60` };
  if (ovr >= 1100) return { label: "ELITE", color: C.em, cls: "elite", glow: `0 0 20px ${C.emMid}` };
  if (ovr >= 1050) return { label: "SILVER", color: "#7ba8d0", cls: "silver", glow: `0 0 12px #7ba8d040` };
  return { label: "BRONZO", color: "#b47a45", cls: "bronze", glow: `0 0 10px #b47a4520` };
}

// ═══════════════════════════════════════════════════════════
// STORAGE SERVICE (interface for localStorage; swap for Supabase)
// ═══════════════════════════════════════════════════════════
const Storage = {
  get: (k) => { try { return localStorage.getItem(`calc_${k}`); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(`calc_${k}`, v); } catch { } },
  delete: (k) => { try { localStorage.removeItem(`calc_${k}`); } catch { } },
  // Swap body for: await supabase.storage.from('photos').upload(k, blob)
};

function usePhotos(players) {
  const [photos, setPhotos] = useState({});

  useEffect(() => {
    const loaded = {};
    players.forEach(p => {
      const v = Storage.get(`photo_${p.id}`);
      if (v) loaded[p.id] = v;
    });
    setPhotos(loaded);
  }, []);

  const upload = useCallback((id, file) => {
    const reader = new FileReader();
    reader.onload = e => {
      const url = e.target.result;
      setPhotos(prev => ({ ...prev, [id]: url }));
      Storage.set(`photo_${id}`, url);
    };
    reader.readAsDataURL(file);
  }, []);

  const remove = useCallback(id => {
    setPhotos(prev => { const n = { ...prev }; delete n[id]; return n; });
    Storage.delete(`photo_${id}`);
  }, []);

  return { photos, upload, remove };
}

// ═══════════════════════════════════════════════════════════
// SVG RADAR — custom (no recharts, handles dual overlay)
// ═══════════════════════════════════════════════════════════
function Radar({ stats, stats2, size = 90, color = C.em, color2 = C.blue, showLabels = false }) {
  const labels = ["GOL", "ASS", "MVP", "WIN", "FORMA"];
  const vals1 = labels.map(l => (stats[l] || 0) / 100);
  const vals2 = stats2 ? labels.map(l => (stats2[l] || 0) / 100) : null;
  const cx = size / 2, cy = size / 2, r = size * 0.36;
  const labelR = size * (showLabels ? 0.48 : 0);

  const pts = labels.map((_, i) => {
    const a = (i / labels.length) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a), lx: cx + (labelR || r * 1.4) * Math.cos(a), ly: cy + (labelR || r * 1.4) * Math.sin(a) };
  });

  const poly = vs => pts.map((p, i) => `${(cx + (p.x - cx) * vs[i]).toFixed(2)},${(cy + (p.y - cy) * vs[i]).toFixed(2)}`).join(" ");

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {[0.33, 0.66, 1].map(s => (
        <polygon key={s} points={pts.map(p => `${(cx + (p.x - cx) * s).toFixed(2)},${(cy + (p.y - cy) * s).toFixed(2)}`).join(" ")}
          fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="0.8" />
      ))}
      {pts.map((p, i) => (
        <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.06)" strokeWidth="0.7" />
      ))}
      {vals2 && (
        <>
          <polygon points={poly(vals2)} fill={`${color2}22`} stroke={color2} strokeWidth="1.4" strokeLinejoin="round" opacity="0.85" />
          {pts.map((p, i) => {
            const px = (cx + (p.x - cx) * vals2[i]).toFixed(2), py = (cy + (p.y - cy) * vals2[i]).toFixed(2);
            return <circle key={i} cx={px} cy={py} r="2.2" fill={color2} opacity="0.9" />;
          })}
        </>
      )}
      <polygon points={poly(vals1)} fill={`${color}1e`} stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
      {pts.map((p, i) => {
        const px = (cx + (p.x - cx) * vals1[i]).toFixed(2), py = (cy + (p.y - cy) * vals1[i]).toFixed(2);
        return <circle key={i} cx={px} cy={py} r="2.4" fill={color} />;
      })}
      {showLabels && pts.map((p, i) => (
        <text key={i} x={p.lx} y={p.ly} textAnchor="middle" dominantBaseline="middle"
          fontSize="10" fill={C.t2} fontFamily="DM Sans,sans-serif" fontWeight="600">
          {labels[i]}
        </text>
      ))}
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════
// PLAYER CARD
// ═══════════════════════════════════════════════════════════
function PlayerCard({ player, ovr, subs, t, photo, onUpload, onClick, style, delay = 0, accentColor, small = false }) {
  const fileRef = useRef();
  const initials = player.cognome[0] + (player.nome[0] || "");
  const acc = accentColor || t.color;
  const size = small ? 172 : 190;

  return (
    <div className="card-player" style={{ animationDelay: `${delay}ms`, ...style }}>
      <div className="card-inner noise scan-line" style={{
        width: size, position: "relative", borderRadius: 14, overflow: "hidden",
        background: `linear-gradient(155deg, ${C.surface} 0%, ${C.surface2} 60%, ${C.surface3} 100%)`,
        border: `1px solid ${acc}40`,
        boxShadow: t.glow,
        padding: small ? "14px 12px 12px" : "18px 14px 14px",
      }} onClick={onClick}>

        {/* Tier badge */}
        <div style={{ position: "absolute", top: 10, right: 10 }}>
          <span className="tag" style={{ background: `${acc}15`, color: acc, border: `1px solid ${acc}30`, fontSize: 9, padding: "2px 7px" }}>
            {t.label}
          </span>
        </div>

        {/* OVR */}
        <div style={{ marginBottom: small ? 4 : 6 }}>
          <div style={{
            fontFamily: "Oswald,sans-serif", fontSize: small ? 32 : 38, fontWeight: 700, color: acc,
            lineHeight: 1, textShadow: `0 0 30px ${acc}60`
          }}>
            {ovr}
          </div>
          <div style={{ fontSize: 8.5, color: C.t2, letterSpacing: 2.5, fontWeight: 600, textTransform: "uppercase", marginTop: -3 }}>Overall</div>
        </div>

        {/* Avatar + upload */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: small ? 6 : 10 }}>
          <div style={{ position: "relative" }}>
            <div style={{
              width: small ? 60 : 72, height: small ? 60 : 72, borderRadius: "50%", overflow: "hidden",
              border: `2px solid ${acc}50`, background: C.surface3,
              display: "flex", alignItems: "center", justifyContent: "center"
            }}>
              {photo
                ? <img src={photo} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                : <span style={{ fontFamily: "Oswald,sans-serif", fontSize: small ? 20 : 24, fontWeight: 700, color: acc, opacity: .6 }}>{initials}</span>}
            </div>
            {onUpload && (
              <>
                <button className="btn-icon" onClick={e => { e.stopPropagation(); fileRef.current?.click(); }}
                  style={{
                    position: "absolute", bottom: -2, right: -2, width: 20, height: 20, borderRadius: "50%",
                    padding: 0, border: `2px solid ${C.surface}`, fontSize: 8
                  }}>
                  📷
                </button>
                <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
                  onChange={e => { const f = e.target.files[0]; if (f) onUpload(player.id, f); }}
                  onClick={e => e.stopPropagation()} />
              </>
            )}
          </div>
        </div>

        {/* Name */}
        <div style={{ textAlign: "center", marginBottom: small ? 6 : 8 }}>
          <div style={{
            fontFamily: "Oswald,sans-serif", fontSize: small ? 15 : 17, fontWeight: 600, color: C.t1,
            letterSpacing: .4, lineHeight: 1, textTransform: "uppercase"
          }}>{player.cognome}</div>
          <div style={{ fontSize: 10.5, color: C.t2, marginTop: 2 }}>{player.nome}</div>
        </div>

        {/* Radar */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: small ? 4 : 6 }}>
          <Radar stats={subs} size={small ? 70 : 82} color={acc} />
        </div>

        {/* Stats strip */}
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: small ? 2 : 4,
          borderTop: `1px solid ${acc}20`, paddingTop: small ? 6 : 8
        }}>
          {[["G/P", player.gol_pp.toFixed(1)], ["A/P", player.assist_pp.toFixed(1)], ["MVP", player.mvp], ["WIN%", player.vittorie_pct]].map(([k, v]) => (
            <div key={k} style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "Oswald,sans-serif", fontSize: small ? 13 : 15, fontWeight: 600, color: acc, lineHeight: 1 }}>{v}</div>
              <div style={{ fontSize: 7.5, color: C.t2, marginTop: 1, letterSpacing: .5 }}>{k}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════
const NAV = [
  { id: "dash", emoji: "◎", label: "Dashboard" },
  { id: "cards", emoji: "▣", label: "Giocatori" },
  { id: "versus", emoji: "⚡", label: "Versus", hot: true },
  { id: "albo", emoji: "◈", label: "Albo d'Oro" },
  { id: "partite", emoji: "▷", label: "Partite" },
  { id: "post", emoji: "＋", label: "Post-Partita" },
];

function Sidebar({ page, setPage, totals }) {
  return (
    <div style={{
      width: 216, minHeight: "100vh", background: C.surface, borderRight: `1px solid ${C.border}`,
      position: "fixed", top: 0, left: 0, zIndex: 200, display: "flex", flexDirection: "column", padding: "0 10px"
    }}>

      {/* Logo */}
      <div style={{ padding: "22px 8px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 9, background: C.emDim, border: `1px solid ${C.emMid}`,
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 17
          }}>⚽</div>
          <div>
            <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 17, fontWeight: 600, color: C.t1, letterSpacing: .5, lineHeight: 1 }}>CALCETTO PRO</div>
            <div style={{ fontSize: 9, color: C.em, letterSpacing: 2.5, fontWeight: 600, marginTop: 1 }}>DASHBOARD</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
        <div style={{ fontSize: 9.5, color: C.t3, letterSpacing: 2, fontWeight: 600, padding: "0 8px", marginBottom: 8, textTransform: "uppercase" }}>Menu</div>
        {NAV.map(({ id, emoji, label, hot }) => (
          <div key={id} className={`nav-item ${page === id ? "act" : ""}`} onClick={() => setPage(id)}>
            <span style={{ fontSize: 14, lineHeight: 1 }}>{emoji}</span>
            <span>{label}</span>
            {hot && <span className="tag tag-em" style={{ marginLeft: "auto", fontSize: 9, padding: "1px 6px" }}>NEW</span>}
          </div>
        ))}
      </div>

      {/* Bottom counters */}
      <div style={{ padding: "14px 8px 18px", borderTop: `1px solid ${C.border}` }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {Object.entries(totals).map(([k, v]) => (
            <div key={k} style={{ background: C.surface2, borderRadius: 8, padding: "8px 10px", border: `1px solid ${C.border}` }}>
              <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 19, fontWeight: 600, color: C.t1 }}>{v}</div>
              <div style={{ fontSize: 9.5, color: C.t2, letterSpacing: .5 }}>{k}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// PAGE: DASHBOARD
// ═══════════════════════════════════════════════════════════
function Dashboard({ enriched, matches, photos, navigate }) {
  const top5 = enriched.slice(0, 5);
  const onFire = [...enriched].sort((a, b) => b.form - a.form).slice(0, 4);
  const recentChart = matches.slice(-10).map(m => ({ name: m.label, gol: m.gol, assist: m.assist }));
  const goalChart = enriched.slice(0, 8).map(p => ({ name: p.cognome, gol: p.gol }));

  const statCards = [
    { label: "Capocannoniere", val: enriched.sort((a, b) => b.gol - a.gol)[0]?.cognome, sub: `${enriched[0]?.gol} gol`, icon: "⚽", color: C.em },
    { label: "Miglior Assist", val: enriched.sort((a, b) => b.assist - a.assist)[0]?.cognome, sub: `${enriched[0]?.assist} assist`, icon: "🎯", color: C.blue },
    { label: "Re MVP", val: enriched.sort((a, b) => b.mvp - a.mvp)[0]?.cognome, sub: `${enriched[0]?.mvp} premi`, icon: "⭐", color: C.gold },
    { label: "Top Rating", val: enriched.sort((a, b) => b.ovr - a.ovr)[0]?.cognome, sub: `OVR ${enriched[0]?.ovr}`, icon: "🏆", color: "#f472b6" },
  ];
  // re-sort for rest of function
  enriched.sort((a, b) => b.ovr - a.ovr);

  return (
    <div className="page">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: "Oswald,sans-serif", fontSize: 36, fontWeight: 600, color: C.t1, letterSpacing: .3, lineHeight: 1 }}>Dashboard</h1>
        <p style={{ color: C.t2, fontSize: 13.5, marginTop: 6 }}>All-Time · 13 Mar 2024 → 19 Feb 2026</p>
      </div>

      {/* KPI */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 20 }}>
        {statCards.map((s, i) => (
          <div key={i} className="glass tr" style={{
            padding: "18px 16px",
            animationDelay: `${i * 60}ms`, transition: "transform .2s, box-shadow .2s"
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = `0 8px 28px ${s.color}18`; }}
            onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 10, color: C.t2, fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" }}>{s.label}</span>
              <div style={{ fontSize: 18, lineHeight: 1 }}>{s.icon}</div>
            </div>
            <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 22, fontWeight: 600, color: C.t1, lineHeight: 1 }}>{s.val}</div>
            <div style={{ fontSize: 12, color: C.t2, marginTop: 6 }}>{s.sub}</div>
            <div style={{ height: 2, background: `linear-gradient(90deg,${s.color},transparent)`, borderRadius: 1, marginTop: 10, width: "60%" }} />
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 16, marginBottom: 16 }}>
        {/* Area chart */}
        <div className="glass" style={{ padding: 20 }}>
          <div style={{ fontSize: 10, color: C.t2, fontWeight: 700, letterSpacing: 2, marginBottom: 16, textTransform: "uppercase" }}>Gol & Assist — Ultime 10 Partite</div>
          <ResponsiveContainer width="100%" height={175}>
            <AreaChart data={recentChart} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={C.em} stopOpacity={.35} />
                  <stop offset="95%" stopColor={C.em} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="aG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={C.blue} stopOpacity={.3} />
                  <stop offset="95%" stopColor={C.blue} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={C.border} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: C.t2, fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: C.t2, fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 9, fontFamily: "DM Sans" }} labelStyle={{ color: C.t2 }} itemStyle={{ color: C.t1 }} />
              <Area type="monotone" dataKey="gol" stroke={C.em} strokeWidth={2} fill="url(#gG)" name="Gol" dot={{ r: 3, fill: C.em, strokeWidth: 0 }} />
              <Area type="monotone" dataKey="assist" stroke={C.blue} strokeWidth={2} fill="url(#aG)" name="Assist" dot={{ r: 3, fill: C.blue, strokeWidth: 0 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* On fire */}
        <div className="glass" style={{ padding: 20 }}>
          <div style={{ fontSize: 10, color: C.t2, fontWeight: 700, letterSpacing: 2, marginBottom: 14, textTransform: "uppercase" }}>🔥 On Fire — Forma Attuale</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[...enriched].sort((a, b) => b.form - a.form).slice(0, 4).map((p, i) => {
              const t = tier(p.ovr);
              return (
                <div key={p.id} style={{
                  display: "flex", alignItems: "center", gap: 10, padding: "9px 11px",
                  background: C.surface2, borderRadius: 9, border: `1px solid ${C.border}`,
                  cursor: "pointer", transition: "all .15s"
                }}
                  onClick={() => navigate("versus")}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = C.borderHi; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; }}>
                  <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 12, fontWeight: 600, color: C.t3, width: 16, textAlign: "center" }}>{i + 1}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600, color: C.t1 }}>{p.cognome}</div>
                    <div style={{ fontSize: 10.5, color: C.t2, marginTop: 1 }}>{p.ga_pp.toFixed(2)} G+A/P</div>
                  </div>
                  <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 22, fontWeight: 700, color: t.color }}>{p.ovr}</div>
                  {p.form > 0.55 && <span style={{ fontSize: 13 }}>🔥</span>}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top 20 — ELO Ranking */}
      <div className="glass" style={{ padding: 20 }}>
        <div style={{ fontSize: 10, color: C.t2, fontWeight: 700, letterSpacing: 2, marginBottom: 18, textTransform: "uppercase" }}>🏆 Top 20 — Classifica ELO</div>
        <div style={{ display: "grid", gridTemplateColumns: "32px 1fr 80px 60px 60px 60px 70px", gap: "0", fontSize: 12.5 }}>
          {/* Header */}
          <div style={{ padding: "8px 4px", color: C.t3, fontSize: 10, fontWeight: 700, letterSpacing: 1, borderBottom: `1px solid ${C.border}` }}>#</div>
          <div style={{ padding: "8px 4px", color: C.t3, fontSize: 10, fontWeight: 700, letterSpacing: 1, borderBottom: `1px solid ${C.border}` }}>GIOCATORE</div>
          <div style={{ padding: "8px 4px", color: C.t3, fontSize: 10, fontWeight: 700, letterSpacing: 1, borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>ELO</div>
          <div style={{ padding: "8px 4px", color: C.t3, fontSize: 10, fontWeight: 700, letterSpacing: 1, borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>G/P</div>
          <div style={{ padding: "8px 4px", color: C.t3, fontSize: 10, fontWeight: 700, letterSpacing: 1, borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>A/P</div>
          <div style={{ padding: "8px 4px", color: C.t3, fontSize: 10, fontWeight: 700, letterSpacing: 1, borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>WIN%</div>
          <div style={{ padding: "8px 4px", color: C.t3, fontSize: 10, fontWeight: 700, letterSpacing: 1, borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>PARTITE</div>
          {/* Rows */}
          {enriched.slice(0, 20).map((p, i) => {
            const t = tier(p.ovr);
            return [
              <div key={`r${i}`} style={{ padding: "10px 4px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center" }}>
                <span style={{ fontFamily: "Oswald,sans-serif", fontSize: 14, fontWeight: 700, color: i < 3 ? t.color : C.t3 }}>{i + 1}</span>
              </div>,
              <div key={`n${i}`} style={{ padding: "10px 4px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontWeight: 600, color: C.t1 }}>{p.cognome}</span>
                <span style={{ fontSize: 10, color: C.t2 }}>{p.nome}</span>
                {i === 0 && <span style={{ fontSize: 11 }}>👑</span>}
              </div>,
              <div key={`e${i}`} style={{ padding: "10px 4px", borderBottom: `1px solid ${C.border}`, textAlign: "right" }}>
                <span style={{ fontFamily: "Oswald,sans-serif", fontSize: 16, fontWeight: 700, color: t.color }}>{Math.round(p.ovr)}</span>
              </div>,
              <div key={`g${i}`} style={{ padding: "10px 4px", borderBottom: `1px solid ${C.border}`, textAlign: "right", color: C.t2 }}>{p.gol_pp.toFixed(1)}</div>,
              <div key={`a${i}`} style={{ padding: "10px 4px", borderBottom: `1px solid ${C.border}`, textAlign: "right", color: C.t2 }}>{p.assist_pp.toFixed(1)}</div>,
              <div key={`w${i}`} style={{ padding: "10px 4px", borderBottom: `1px solid ${C.border}`, textAlign: "right", color: C.t2 }}>{p.vittorie_pct}%</div>,
              <div key={`p${i}`} style={{ padding: "10px 4px", borderBottom: `1px solid ${C.border}`, textAlign: "right", color: C.t2 }}>{p.partite}</div>,
            ];
          })}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// PAGE: CARDS GRID
// ═══════════════════════════════════════════════════════════
function Cards({ enriched, photos, upload, setDetail }) {
  return (
    <div className="page">
      <h1 style={{ fontFamily: "Oswald,sans-serif", fontSize: 36, fontWeight: 600, marginBottom: 6 }}>Giocatori</h1>
      <p style={{ color: C.t2, fontSize: 13.5, marginBottom: 28 }}>Card FIFA · Rating Momento di Forma — clicca per dettaglio</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
        {enriched.map((p, i) => (
          <PlayerCard key={p.id} player={p} ovr={p.ovr} subs={p.subs} t={tier(p.ovr)}
            photo={photos[p.id]} onUpload={upload}
            onClick={() => setDetail(p)} delay={i * 45} />
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// PAGE: VERSUS ⚡ — Star Feature
// ═══════════════════════════════════════════════════════════
function CompareBar({ label, v1, v2, fmt = x => x, suffix = "" }) {
  const total = Math.max(v1 + v2, 0.001);
  const w1 = (v1 / total) * 100;
  const w2 = (v2 / total) * 100;
  const p1wins = v1 >= v2;

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
        <div style={{
          fontFamily: "Oswald,sans-serif", fontSize: 17, fontWeight: 600,
          color: p1wins ? C.em : C.t2, minWidth: 50
        }}>{fmt(v1)}{suffix}</div>
        <div style={{ fontSize: 10.5, color: C.t2, fontWeight: 600, letterSpacing: .8, textTransform: "uppercase", textAlign: "center", flex: 1 }}>{label}</div>
        <div style={{
          fontFamily: "Oswald,sans-serif", fontSize: 17, fontWeight: 600,
          color: !p1wins ? C.blue : C.t2, textAlign: "right", minWidth: 50
        }}>{fmt(v2)}{suffix}</div>
      </div>
      <div style={{ display: "flex", gap: 2, height: 5, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${w1}%`, background: p1wins ? `linear-gradient(90deg,${C.em}80,${C.em})` : `${C.em}30`, borderRadius: "3px 0 0 3px", transition: "width .7s cubic-bezier(.16,1,.3,1)" }} />
        <div style={{ width: `${w2}%`, background: !p1wins ? `linear-gradient(90deg,${C.blue},${C.blue}80)` : `${C.blue}30`, borderRadius: "0 3px 3px 0", transition: "width .7s cubic-bezier(.16,1,.3,1)" }} />
      </div>
    </div>
  );
}

function Versus({ enriched, photos, upload }) {
  const [sel1, setSel1] = useState(enriched[0]?.id || "");
  const [sel2, setSel2] = useState(enriched[1]?.id || "");

  const p1 = enriched.find(p => p.id === sel1);
  const p2 = enriched.find(p => p.id === sel2);
  const t1o = p1 ? tier(p1.ovr) : null;
  const t2o = p2 ? tier(p2.ovr) : null;
  const p1wins = p1 && p2 && p1.ovr >= p2.ovr;

  const comparisons = p1 && p2 ? [
    { label: "GOL Totali", v1: p1.gol, v2: p2.gol, fmt: v => v },
    { label: "ASSIST Totali", v1: p1.assist, v2: p2.assist, fmt: v => v },
    { label: "G+A Totali", v1: p1.ga, v2: p2.ga, fmt: v => v },
    { label: "Gol/Partita", v1: p1.gol_pp, v2: p2.gol_pp, fmt: v => v.toFixed(2) },
    { label: "Assist/Partita", v1: p1.assist_pp, v2: p2.assist_pp, fmt: v => v.toFixed(2) },
    { label: "G+A/Partita", v1: p1.ga_pp, v2: p2.ga_pp, fmt: v => v.toFixed(2) },
    { label: "MVP", v1: p1.mvp, v2: p2.mvp, fmt: v => v },
    { label: "Win Rate", v1: p1.vittorie_pct, v2: p2.vittorie_pct, fmt: v => v, suffix: "%" },
    { label: "Presenze", v1: p1.partite, v2: p2.partite, fmt: v => v },
    { label: "Forma (OVR)", v1: p1.ovr, v2: p2.ovr, fmt: v => v },
  ] : [];

  const p1wins_count = comparisons.filter(c => c.v1 >= c.v2).length;
  const p2wins_count = comparisons.length - p1wins_count;

  const Select = ({ val, setVal, exclude }) => (
    <div className="form-group" style={{ minWidth: 180 }}>
      <label>Seleziona giocatore</label>
      <select value={val} onChange={e => setVal(e.target.value)}>
        {enriched.filter(p => p.id !== exclude).map(p => (
          <option key={p.id} value={p.id}>{p.cognome} · {p.nome} ({calcOverall(p, MATCHES)} OVR)</option>
        ))}
      </select>
    </div>
  );

  return (
    <div className="page">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 28, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span className="tag tag-em">FEATURE</span>
          </div>
          <h1 style={{ fontFamily: "Oswald,sans-serif", fontSize: 36, fontWeight: 600, color: C.t1, letterSpacing: .3, lineHeight: 1 }}>Versus</h1>
          <p style={{ color: C.t2, fontSize: 13.5, marginTop: 6 }}>Confronto testa a testa — radar sovrapposti e statistiche comparative</p>
        </div>

        {/* Selectors */}
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <Select val={sel1} setVal={setSel1} exclude={sel2} />
          <div style={{ paddingBottom: 10, fontSize: 18, color: C.t3, fontWeight: 700 }}>⚡</div>
          <Select val={sel2} setVal={setSel2} exclude={sel1} />
        </div>
      </div>

      {p1 && p2 ? (
        <>
          {/* VS Cards row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 20, alignItems: "center", marginBottom: 24 }}>
            {/* Player 1 */}
            <div className="slid-l" style={{ display: "flex", justifyContent: "flex-end" }}>
              <div style={{ position: "relative" }}>
                {p1wins && (
                  <div className="winner-glow-em" style={{
                    position: "absolute", inset: -3, borderRadius: 17, zIndex: 0,
                    border: `2px solid ${C.em}`, pointerEvents: "none"
                  }} />
                )}
                <PlayerCard player={p1} ovr={p1.ovr} subs={p1.subs} t={t1o}
                  photo={photos[p1.id]} onUpload={upload} accentColor={C.em} />
                {p1wins && (
                  <div style={{ textAlign: "center", marginTop: 10 }}>
                    <span className="tag tag-em">👑 VINCITORE</span>
                  </div>
                )}
              </div>
            </div>

            {/* VS Center */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 52, fontWeight: 700, color: C.t3, lineHeight: 1 }}>VS</div>
              <div style={{ fontSize: 11, color: C.t2, textAlign: "center" }}>
                <span style={{ color: C.em, fontWeight: 700 }}>{p1wins_count}</span>
                <span style={{ color: C.t3, margin: "0 4px" }}>-</span>
                <span style={{ color: C.blue, fontWeight: 700 }}>{p2wins_count}</span>
              </div>
              {/* Dual OVR comparison */}
              <div className="glass2" style={{ padding: "12px 16px", textAlign: "center", width: 110 }}>
                <div style={{
                  fontFamily: "Oswald,sans-serif", fontSize: 32, fontWeight: 700,
                  background: `linear-gradient(135deg,${C.em},${C.blue})`,
                  WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
                }}>
                  {Math.abs(p1.ovr - p2.ovr)}
                </div>
                <div style={{ fontSize: 9, color: C.t2, letterSpacing: 1.5 }}>ΔΔ OVR</div>
              </div>
            </div>

            {/* Player 2 */}
            <div className="slid-r" style={{ display: "flex", justifyContent: "flex-start" }}>
              <div style={{ position: "relative" }}>
                {!p1wins && (
                  <div style={{
                    position: "absolute", inset: -3, borderRadius: 17, zIndex: 0,
                    border: `2px solid ${C.blue}`, boxShadow: `0 0 20px ${C.blueMid}`,
                    pointerEvents: "none"
                  }} />
                )}
                <PlayerCard player={p2} ovr={p2.ovr} subs={p2.subs} t={t2o}
                  photo={photos[p2.id]} onUpload={upload} accentColor={C.blue} />
                {!p1wins && (
                  <div style={{ textAlign: "center", marginTop: 10 }}>
                    <span className="tag tag-blue">👑 VINCITORE</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Dual Radar + Compare Table */}
          <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>

            {/* Overlapping radar */}
            <div className="glass" style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{ fontSize: 10, color: C.t2, fontWeight: 700, letterSpacing: 2, marginBottom: 16, textTransform: "uppercase" }}>Radar — Confronto</div>
              <Radar stats={p1.subs} stats2={p2.subs} size={220} color={C.em} color2={C.blue} showLabels={true} />
              <div style={{ display: "flex", gap: 20, marginTop: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: C.em }} />
                  <span style={{ fontSize: 12, color: C.em, fontWeight: 600 }}>{p1.cognome}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: C.blue }} />
                  <span style={{ fontSize: 12, color: C.blue, fontWeight: 600 }}>{p2.cognome}</span>
                </div>
              </div>

              {/* Quick verdict */}
              <div style={{
                marginTop: 16, padding: "12px 16px", background: C.surface2, borderRadius: 10,
                border: `1px solid ${C.border}`, width: "100%"
              }}>
                <div style={{ fontSize: 9.5, color: C.t2, letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase" }}>Analisi Radar</div>
                {[
                  { label: "Bomber", winner: p1.gol_pp >= p2.gol_pp ? p1.cognome : p2.cognome, color: p1.gol_pp >= p2.gol_pp ? C.em : C.blue },
                  { label: "Assist King", winner: p1.assist_pp >= p2.assist_pp ? p1.cognome : p2.cognome, color: p1.assist_pp >= p2.assist_pp ? C.em : C.blue },
                  { label: "MVP Machine", winner: p1.mvp >= p2.mvp ? p1.cognome : p2.cognome, color: p1.mvp >= p2.mvp ? C.em : C.blue },
                  { label: "Costanza", winner: p1.vittorie_pct >= p2.vittorie_pct ? p1.cognome : p2.cognome, color: p1.vittorie_pct >= p2.vittorie_pct ? C.em : C.blue },
                ].map(({ label, winner, color }) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, padding: "3px 0", borderBottom: `1px solid ${C.border}` }}>
                    <span style={{ color: C.t2 }}>{label}</span>
                    <span style={{ color, fontWeight: 700 }}>{winner}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Comparison bars */}
            <div className="glass" style={{ padding: 24 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
                <div style={{ fontSize: 10, color: C.t2, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase" }}>Statistiche Comparative</div>
                <div style={{ display: "flex", gap: 14 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 1, background: C.em }} />
                    <span style={{ fontSize: 11.5, color: C.em, fontWeight: 600 }}>{p1.cognome}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 1, background: C.blue }} />
                    <span style={{ fontSize: 11.5, color: C.blue, fontWeight: 600 }}>{p2.cognome}</span>
                  </div>
                </div>
              </div>
              {comparisons.map(c => (
                <CompareBar key={c.label} {...c} />
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="glass" style={{ padding: 60, textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>⚡</div>
          <div style={{ color: C.t2, fontSize: 15 }}>Seleziona due giocatori per avviare il confronto</div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// PAGE: ALBO D'ORO
// ═══════════════════════════════════════════════════════════
function Albo({ enriched }) {
  const [key, setKey] = useState("ovr");
  const [dir, setDir] = useState("desc");

  const COLS = [
    { k: "ovr", l: "OVR", f: v => <span style={{ fontFamily: "Oswald,sans-serif", fontSize: 17, fontWeight: 700 }}>{v}</span> },
    { k: "partite", l: "P" },
    { k: "vittorie_pct", l: "WIN%", f: v => `${v}%` },
    { k: "gol", l: "GOL" },
    { k: "gol_pp", l: "G/P", f: v => v.toFixed(2) },
    { k: "assist", l: "ASS" },
    { k: "assist_pp", l: "A/P", f: v => v.toFixed(2) },
    { k: "ga_pp", l: "G+A/P", f: v => v.toFixed(2) },
    { k: "mvp", l: "MVP" },
    { k: "intonso", l: "INT" },
    { k: "autogol", l: "OG", f: (v, row) => <span style={{ color: v > 0 ? C.red : C.t2 }}>{v}</span> },
    { k: "form", l: "FORMA", f: v => <span style={{ color: v > 0.6 ? C.em : v > 0.3 ? C.gold : C.t2 }}>{Math.round(v * 100)}</span> },
  ];

  const sorted = [...enriched].sort((a, b) => {
    const va = a[key] ?? 0, vb = b[key] ?? 0;
    return dir === "desc" ? vb - va : va - vb;
  });

  const gc = `28px 140px repeat(${COLS.length},1fr)`;

  return (
    <div className="page">
      <h1 style={{ fontFamily: "Oswald,sans-serif", fontSize: 36, fontWeight: 600, marginBottom: 6 }}>Albo d'Oro</h1>
      <p style={{ color: C.t2, fontSize: 13.5, marginBottom: 24 }}>Clicca sulle colonne per ordinare</p>
      <div className="glass" style={{ overflow: "auto" }}>
        {/* Head */}
        <div style={{
          display: "grid", gridTemplateColumns: gc, padding: "10px 16px",
          borderBottom: `1px solid ${C.border}`, position: "sticky", top: 0, background: C.surface, zIndex: 10, gap: 4
        }}>
          <div /><div style={{ fontSize: 9.5, color: C.t2, fontWeight: 700, letterSpacing: 1.2 }}>GIOCATORE</div>
          {COLS.map(c => (
            <div key={c.k} className="sort-col" onClick={() => { if (key === c.k) setDir(d => d === "desc" ? "asc" : "desc"); else { setKey(c.k); setDir("desc"); } }}
              style={{
                fontSize: 9.5, color: key === c.k ? C.em : C.t2, fontWeight: 700, letterSpacing: .8,
                textAlign: "center", display: "flex", alignItems: "center", justifyContent: "center", gap: 2
              }}>
              {c.l}
              {key === c.k && <span style={{ fontSize: 9 }}>{dir === "desc" ? "↓" : "↑"}</span>}
            </div>
          ))}
        </div>
        {/* Rows */}
        {sorted.map((p, i) => {
          const t = tier(p.ovr);
          return (
            <div key={p.id} className="tr-row" style={{ display: "grid", gridTemplateColumns: gc, padding: "10px 16px", gap: 4, alignItems: "center" }}>
              <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 13, color: i < 3 ? C.gold : C.t3 }}>{i + 1}</div>
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: C.t1 }}>{p.cognome}</div>
                <div style={{ fontSize: 10.5, color: C.t2 }}>{p.nome}</div>
              </div>
              {COLS.map(c => {
                const raw = p[c.k] ?? 0;
                return (
                  <div key={c.k} style={{ textAlign: "center", fontSize: 13, color: key === c.k ? C.t1 : C.t2, fontWeight: key === c.k ? 600 : 400, ...(c.k === "ovr" ? { color: t.color } : {}) }}>
                    {c.f ? c.f(raw, p) : raw}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// PAGE: PARTITE
// ═══════════════════════════════════════════════════════════
function Partite({ matches }) {
  const [q, setQ] = useState("");
  const filtered = [...matches].filter(m =>
    m.mvp.toLowerCase().includes(q.toLowerCase()) || m.d.includes(q) || m.label.includes(q)
  ).reverse();

  return (
    <div className="page">
      <h1 style={{ fontFamily: "Oswald,sans-serif", fontSize: 36, fontWeight: 600, marginBottom: 6 }}>Partite</h1>
      <p style={{ color: C.t2, fontSize: 13.5, marginBottom: 20 }}>{matches.length} partite · All-Time</p>
      <div className="form-group" style={{ marginBottom: 16 }}>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Cerca MVP, data, mese…" />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {filtered.map((m, i) => (
          <div key={i} className="glass" style={{
            padding: "14px 18px", display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap",
            transition: "border-color .15s"
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = C.borderHi; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; }}>
            <div style={{ minWidth: 140 }}>
              <div style={{ fontSize: 12.5, color: C.em, fontWeight: 600 }}>{m.d}</div>
              <div style={{ fontSize: 11, color: C.t2, marginTop: 2 }}>🏟 Season {m.season} · {m.label}</div>
            </div>
            <div style={{ display: "flex", gap: 20, flex: 1 }}>
              {[["⚽", m.gol, "Gol", C.t1], ["🎯", m.assist, "Assist", C.blue], ...(m.autogol > 0 ? [["😬", m.autogol, "OG", C.red]] : [])].map(([ic, v, l, col]) => (
                <div key={l} style={{ textAlign: "center" }}>
                  <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 26, fontWeight: 600, color: col, lineHeight: 1 }}>{v}</div>
                  <div style={{ fontSize: 9.5, color: C.t2, marginTop: 2 }}>{l}</div>
                </div>
              ))}
            </div>
            <div style={{ background: C.goldDim, border: `1px solid ${C.gold}30`, borderRadius: 8, padding: "8px 14px", textAlign: "center" }}>
              <div style={{ fontSize: 8.5, color: C.gold, fontWeight: 700, letterSpacing: 1.5 }}>MVP</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: C.t1, marginTop: 2 }}>{m.mvp}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// PAGE: POST-PARTITA
// ═══════════════════════════════════════════════════════════
function PostPartita({ players, matches, setMatches }) {
  const today = new Date().toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
  const [form, setForm] = useState({ d: today, label: "", mvp: "", gol: "", assist: "", autogol: "0", season: "2" });
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");
  const s = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const save = () => {
    if (!form.d || !form.mvp || form.gol === "") { setErr("Compila almeno Data, MVP e Gol."); return; }
    setMatches(prev => [...prev, {
      d: form.d, label: form.label || form.d.slice(3, 8), mvp: form.mvp,
      gol: parseInt(form.gol) || 0, assist: parseInt(form.assist) || 0, autogol: parseInt(form.autogol) || 0,
      season: parseInt(form.season) || 2
    }]);
    setForm({ d: today, label: "", mvp: "", gol: "", assist: "", autogol: "0", season: "2" });
    setDone(true); setErr(""); setTimeout(() => setDone(false), 3500);
  };

  const F = ({ label, k, type = "text", ph = "" }) => (
    <div className="form-group">
      <label>{label}</label>
      <input type={type} value={form[k]} onChange={s(k)} placeholder={ph} />
    </div>
  );

  return (
    <div className="page" style={{ maxWidth: 600 }}>
      <h1 style={{ fontFamily: "Oswald,sans-serif", fontSize: 36, fontWeight: 600, marginBottom: 6 }}>Post-Partita</h1>
      <p style={{ color: C.t2, fontSize: 13.5, marginBottom: 24 }}>Inserisci i dati · l'Overall si ricalcola in tempo reale</p>

      {done && (
        <div className="scale-in" style={{ background: C.emDim, border: `1px solid ${C.emMid}`, borderRadius: 10, padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 18 }}>✅</span>
          <span style={{ color: C.em, fontWeight: 600, fontSize: 13.5 }}>Partita salvata — tutti i Rating sono stati aggiornati istantaneamente.</span>
        </div>
      )}
      {err && (
        <div style={{ background: C.redDim, border: `1px solid ${C.red}30`, borderRadius: 10, padding: "12px 16px", marginBottom: 16 }}>
          <span style={{ color: C.red, fontSize: 13 }}>{err}</span>
        </div>
      )}

      <div className="glass" style={{ padding: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
          <F label="Data" k="d" ph="GG/MM/AAAA" />
          <F label="Label breve" k="label" ph="es. Feb'26" />
          <div className="form-group">
            <label>MVP della serata</label>
            <select value={form.mvp} onChange={s("mvp")}>
              <option value="">— Seleziona —</option>
              {players.map(p => <option key={p.id} value={p.cognome}>{p.cognome} · {p.nome}</option>)}
              <option value="Ospite">Ospite</option>
            </select>
          </div>
          <div className="form-group">
            <label>Season</label>
            <select value={form.season} onChange={s("season")}>
              <option value="1">Season 1</option>
              <option value="2">Season 2</option>
            </select>
          </div>
          <F label="Gol Totali" k="gol" type="number" ph="0" />
          <F label="Assist Totali" k="assist" type="number" ph="0" />
          <F label="Autogol" k="autogol" type="number" ph="0" />
        </div>
        <div style={{ display: "flex", gap: 10, borderTop: `1px solid ${C.border}`, paddingTop: 18 }}>
          <button className="btn btn-em" onClick={save} style={{ flex: 1, padding: "11px" }}>
            ＋ Salva Partita
          </button>
          <button className="btn btn-ghost" onClick={() => setForm({ d: today, label: "", mvp: "", gol: "", assist: "", autogol: "0", season: "2" })}>
            Reset
          </button>
        </div>
      </div>

      {matches.length > 0 && (() => {
        const last = matches[matches.length - 1];
        return (
          <div className="glass" style={{ padding: 18, marginTop: 16, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: C.em, fontWeight: 600 }}>Ultima partita salvata</div>
              <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 20, fontWeight: 600, color: C.t1 }}>{last.d}</div>
              <div style={{ fontSize: 11.5, color: C.t2 }}>Totale: {matches.length} partite</div>
            </div>
            {[["⚽", last.gol, "Gol"], ["🎯", last.assist, "Assist"]].map(([ic, v, l]) => (
              <div key={l} style={{ textAlign: "center" }}>
                <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 28, fontWeight: 600, lineHeight: 1 }}>{v}</div>
                <div style={{ fontSize: 10, color: C.t2 }}>{l}</div>
              </div>
            ))}
            <div style={{ background: C.goldDim, border: `1px solid ${C.gold}30`, borderRadius: 8, padding: "8px 14px", textAlign: "center" }}>
              <div style={{ fontSize: 9, color: C.gold, fontWeight: 700, letterSpacing: 1 }}>MVP</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>{last.mvp}</div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// PLAYER DETAIL MODAL
// ═══════════════════════════════════════════════════════════
function DetailModal({ player, onClose, photos, upload, matches }) {
  const ovr = calcOverall(player, matches);
  const subs = calcSubs(player, matches);
  const t = tier(ovr);
  const radarData = Object.entries(subs).map(([k, v]) => ({ stat: k, value: v }));

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 580 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span className="tag" style={{ background: `${t.color}18`, color: t.color, border: `1px solid ${t.color}30` }}>{t.label}</span>
            </div>
            <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 28, fontWeight: 600, color: t.color }}>{player.cognome.toUpperCase()}</div>
            <div style={{ color: C.t2, fontSize: 13 }}>{player.nome}</div>
          </div>
          <div style={{ fontFamily: "Oswald,sans-serif", fontSize: 60, fontWeight: 700, color: t.color, lineHeight: 1, textShadow: `0 0 30px ${t.color}60` }}>{ovr}</div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <div style={{ fontSize: 9.5, color: C.t2, letterSpacing: 2, fontWeight: 600, marginBottom: 10, textTransform: "uppercase" }}>Radar Completo</div>
            <Radar stats={subs} size={200} color={t.color} showLabels={true} />
          </div>
          <div>
            <div style={{ fontSize: 9.5, color: C.t2, letterSpacing: 2, fontWeight: 600, marginBottom: 10, textTransform: "uppercase" }}>Statistiche</div>
            {[
              ["Partite Giocate", player.partite],
              ["Vittorie", `${player.vittorie} (${player.vittorie_pct}%)`],
              ["Gol", `${player.gol} · ${player.gol_pp.toFixed(2)}/P`],
              ["Assist", `${player.assist} · ${player.assist_pp.toFixed(2)}/P`],
              ["G+A", `${player.ga} · ${player.ga_pp.toFixed(2)}/P`],
              ["MVP", player.mvp],
              ["Intonso", player.intonso],
              ["Autogol", player.autogol],
            ].map(([k, v]) => (
              <div key={k} style={{
                display: "flex", justifyContent: "space-between", padding: "6px 10px",
                background: C.surface2, borderRadius: 6, marginBottom: 4, borderLeft: `2px solid ${C.border}`
              }}>
                <span style={{ fontSize: 12.5, color: C.t2 }}>{k}</span>
                <span style={{ fontSize: 12.5, color: C.t1, fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
        <button className="btn btn-ghost" style={{ width: "100%", justifyContent: "center", marginTop: 18 }} onClick={onClose}>
          Chiudi
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// APP ROOT
// ═══════════════════════════════════════════════════════════
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
    [players, matches]);

  const totals = {
    Partite: matches.length,
    Giocatori: players.length,
    Gol: matches.reduce((s, m) => s + m.gol, 0),
    MVP: [...new Set(matches.map(m => m.mvp))].length,
  };

  const props = { enriched, matches, setMatches, photos, upload, remove, players, navigate: setPage };

  const PAGES = {
    dash: <Dashboard {...props} />,
    cards: <Cards {...props} setDetail={setDetail} />,
    versus: <Versus {...props} />,
    albo: <Albo enriched={enriched} />,
    partite: <Partite matches={matches} />,
    post: <PostPartita {...props} />,
  };

  return (
    <div style={{ background: C.bg, minHeight: "100vh", fontFamily: "DM Sans,sans-serif" }}>
      <Styles />

      {/* Ambient glow */}
      <div style={{
        position: "fixed", top: "-20%", left: "30%", width: "500px", height: "500px",
        background: `radial-gradient(ellipse at center, ${C.em}08 0%, transparent 70%)`,
        pointerEvents: "none", zIndex: 0
      }} />
      <div style={{
        position: "fixed", bottom: "-10%", right: "10%", width: "400px", height: "400px",
        background: `radial-gradient(ellipse at center, ${C.blue}06 0%, transparent 70%)`,
        pointerEvents: "none", zIndex: 0
      }} />

      <Sidebar page={page} setPage={setPage} totals={totals} />

      <main style={{ marginLeft: 216, padding: "32px 32px 56px", minHeight: "100vh", position: "relative", zIndex: 1 }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          {PAGES[page] || PAGES.dash}
        </div>
      </main>

      {detail && (
        <DetailModal player={detail} onClose={() => setDetail(null)}
          photos={photos} upload={upload} matches={matches} />
      )}
    </div>
  );
}
