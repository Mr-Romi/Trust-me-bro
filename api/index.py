from flask import Flask, request, jsonify
import joblib
import pandas as pd
import os
from textblob import TextBlob
from google_play_scraper import app as gplay_app, reviews as gplay_reviews, search

# FIX: HTML_PAGE defined BEFORE routes so home() never gets NameError
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AppTrust - Scam App Detector</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0f172a; --surface: #1e293b; --surface2: #334155;
  --text: #f1f5f9; --text2: #94a3b8; --text3: #64748b;
  --accent: #6366f1; --accent-hover: #818cf8;
  --safe: #10b981; --warn: #f59e0b; --danger: #ef4444;
  --radius: 16px; --radius-sm: 10px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:\'Inter\',system-ui,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
.header { background:var(--surface); border-bottom:1px solid var(--surface2); padding:16px 32px; display:flex; align-items:center; gap:14px; }
.header .logo { font-size:22px; font-weight:800; background:linear-gradient(135deg,var(--accent),#a78bfa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.header .tagline { font-size:13px; color:var(--text3); }
.hero { background:linear-gradient(160deg,#1e1b4b 0%,var(--bg) 100%); padding:56px 20px 48px; text-align:center; }
.hero h2 { font-size:28px; font-weight:700; margin-bottom:8px; }
.hero p { color:var(--text2); font-size:15px; margin-bottom:28px; }
.search-wrapper { position:relative; max-width:520px; margin:0 auto; }
.search-row { display:flex; gap:10px; }
.search-row input { flex:1; padding:14px 20px; border-radius:var(--radius-sm); border:2px solid var(--surface2); background:var(--surface); color:var(--text); font-size:15px; outline:none; transition:border .2s; font-family:inherit; }
.search-row input:focus { border-color:var(--accent); }
.search-row button { padding:14px 28px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-size:15px; font-weight:600; cursor:pointer; transition:background .2s; white-space:nowrap; font-family:inherit; }
.search-row button:hover { background:var(--accent-hover); }
.suggestions { position:absolute; top:calc(100% + 6px); left:0; right:0; background:var(--surface); border:1px solid var(--surface2); border-radius:var(--radius-sm); box-shadow:0 12px 40px rgba(0,0,0,.4); z-index:100; overflow:hidden; display:none; }
.suggestion-item { display:flex; align-items:center; gap:12px; padding:12px 16px; cursor:pointer; border-bottom:1px solid var(--surface2); transition:background .15s; }
.suggestion-item:last-child { border-bottom:none; }
.suggestion-item:hover { background:var(--surface2); }
.suggestion-item img { width:38px; height:38px; border-radius:10px; }
.s-name { font-size:14px; font-weight:600; }
.s-id { font-size:11px; color:var(--text3); }
.s-rating { font-size:12px; color:var(--warn); margin-left:auto; font-weight:600; }
.chips { margin-top:16px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }
.chip { padding:6px 16px; border-radius:999px; border:1px solid var(--surface2); background:transparent; color:var(--text2); font-size:13px; cursor:pointer; transition:all .2s; font-family:inherit; }
.chip:hover { border-color:var(--accent); color:var(--accent); background:rgba(99,102,241,.1); }
.result-area { max-width:680px; margin:32px auto; padding:0 16px; }
.spinner-wrap { display:none; text-align:center; padding:48px 0; }
.spinner { width:40px; height:40px; border:4px solid var(--surface2); border-top-color:var(--accent); border-radius:50%; animation:spin .7s linear infinite; margin:0 auto 16px; }
@keyframes spin { to { transform:rotate(360deg); } }
.spinner-wrap p { color:var(--text3); font-size:14px; }
.card { background:var(--surface); border-radius:var(--radius); padding:28px; border:1px solid var(--surface2); display:none; animation:fadeUp .4s ease; }
@keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
.app-header { display:flex; align-items:center; gap:16px; margin-bottom:24px; }
.app-header img { width:64px; height:64px; border-radius:14px; }
.app-header h3 { font-size:20px; font-weight:700; }
.app-header p { font-size:13px; color:var(--text3); margin-top:2px; }
.score-section { text-align:center; margin:24px 0; }
.score-ring { width:110px; height:110px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:32px; font-weight:800; color:#fff; margin-bottom:10px; }
.score-ring.safe { background:linear-gradient(135deg,#10b981,#059669); box-shadow:0 0 30px rgba(16,185,129,.3); }
.score-ring.suspicious { background:linear-gradient(135deg,#f59e0b,#d97706); box-shadow:0 0 30px rgba(245,158,11,.3); }
.score-ring.scam { background:linear-gradient(135deg,#ef4444,#dc2626); box-shadow:0 0 30px rgba(239,68,68,.3); }
/* FIX: score-lbl class renamed from score-label to avoid collision with score-ring class */
.score-lbl { font-size:18px; font-weight:700; }
.score-lbl.safe { color:var(--safe); } .score-lbl.suspicious { color:var(--warn); } .score-lbl.scam { color:var(--danger); }
.score-sub { font-size:13px; color:var(--text3); margin-top:4px; }
.stats { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:20px 0; }
.stat { background:var(--bg); border-radius:var(--radius-sm); padding:16px; text-align:center; }
.stat .val { font-size:22px; font-weight:700; color:var(--text); }
.stat .key { font-size:12px; color:var(--text3); margin-top:4px; }
.reasons { margin-top:24px; }
.reasons h4, .reviews-section h4 { font-size:15px; font-weight:600; margin-bottom:12px; color:var(--text2); }
.reason { display:flex; align-items:center; gap:12px; padding:12px 16px; background:var(--bg); border-radius:var(--radius-sm); margin-bottom:8px; font-size:14px; }
.reason .dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
.reviews-section { margin-top:28px; }
.review { background:var(--bg); border-radius:var(--radius-sm); padding:16px; margin-bottom:10px; border-left:4px solid var(--surface2); }
.review-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.review-stars { color:var(--warn); font-size:13px; }
.sentiment-tag { font-size:11px; font-weight:700; padding:4px 12px; border-radius:999px; color:#fff; text-transform:uppercase; letter-spacing:.5px; }
.review-text { font-size:13px; color:var(--text2); line-height:1.6; }
.divider { border:none; border-top:1px solid var(--surface2); margin:24px 0; }
.error-msg { background:rgba(239,68,68,.1); color:var(--danger); padding:16px; border-radius:var(--radius-sm); text-align:center; display:none; border:1px solid rgba(239,68,68,.2); }
.footer { text-align:center; padding:32px; color:var(--text3); font-size:12px; }
@media (max-width:600px) {
  .stats { grid-template-columns:1fr; }
  .hero h2 { font-size:22px; }
  .search-row { flex-direction:column; }
}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">AppTrust</div>
    <div class="tagline">AI-Powered Scam App Detection</div>
  </div>
</div>
<div class="hero">
  <h2>Is that app safe to install?</h2>
  <p>Search any Google Play app and get an instant trust score powered by ML</p>
  <div class="search-wrapper">
    <div class="search-row">
      <input type="text" id="q" placeholder="Search app name e.g. WhatsApp" autocomplete="off"/>
      <button onclick="doSearch()">Analyze</button>
    </div>
    <div class="suggestions" id="sug"></div>
  </div>
  <div class="chips">
    <span class="chip" onclick="quick(\'WhatsApp\')">WhatsApp</span>
    <span class="chip" onclick="quick(\'Spotify\')">Spotify</span>
    <span class="chip" onclick="quick(\'Instagram\')">Instagram</span>
    <span class="chip" onclick="quick(\'TikTok\')">TikTok</span>
    <span class="chip" onclick="quick(\'Snapchat\')">Snapchat</span>
  </div>
</div>
<div class="result-area">
  <div class="spinner-wrap" id="spin"><div class="spinner"></div><p>Analyzing app - fetching live data from Google Play...</p></div>
  <div class="error-msg" id="err"></div>
  <div class="card" id="card"></div>
</div>
<div class="footer">AppTrust 2025 - Built with ML and Google Play data</div>
<script>
const $=id=>document.getElementById(id);
let timer;
function quick(n){$(\'q\').value=n;doSearch();}
function doSearch(){const q=$(\'q\').value.trim();if(q)fetchSug(q);}
$(\'q\').addEventListener(\'input\',function(){clearTimeout(timer);if(this.value.trim().length<2){$(\'sug\').style.display=\'none\';return;}timer=setTimeout(()=>fetchSug(this.value.trim()),350);});
$(\'q\').addEventListener(\'keypress\',e=>{if(e.key===\'Enter\')doSearch();});
async function fetchSug(query){
  try{
    const r=await fetch(\'/search\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({query})});
    const d=await r.json();
    if(!d.success||!d.results.length)return;
    $(\'sug\').innerHTML=d.results.map(r=>`<div class="suggestion-item" onclick="analyze(\'${r.appId}\')">
      <img src="${r.icon}" alt="" onerror="this.style.display=\'none\'"/>
      <div><div class="s-name">${r.title}</div><div class="s-id">${r.appId}</div></div>
      <div class="s-rating">${r.score?r.score.toFixed(1)+\' stars\':\'\'}</div></div>`).join(\'\');
    $(\'sug\').style.display=\'block\';
  }catch(e){console.error(e);}
}
function stars(n){let s=\'\';for(let i=1;i<=5;i++)s+=i<=n?\'&#9733;\':\'&#9734;\';return s;}
async function analyze(id){
  $(\'sug\').style.display=\'none\';
  $(\'spin\').style.display=\'block\';
  $(\'card\').style.display=\'none\';
  $(\'err\').style.display=\'none\';
  try{
    const r=await fetch(\'/analyze\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({package_id:id})});
    const d=await r.json();
    $(\'spin\').style.display=\'none\';
    if(!d.success){$(\'err\').textContent=d.error||\'App not found.\';$(\'err\').style.display=\'block\';return;}
    $(\'q\').value=d.title;
    const cls=d.label===\'Safe\'?\'safe\':(d.label===\'Suspicious\'?\'suspicious\':\'scam\');
    const dot=cls===\'safe\'?\'var(--safe)\':(cls===\'suspicious\'?\'var(--warn)\':\'var(--danger)\');
    const revHTML=(d.reviews||[]).map(r=>`<div class="review" style="border-left-color:${r.color}">
      <div class="review-top"><span class="review-stars">${stars(r.score)}</span>
      <span class="sentiment-tag" style="background:${r.color}">${r.sentiment}</span></div>
      <div class="review-text">${r.text}</div></div>`).join(\'\');
    $(\'card\').innerHTML=`
      <div class="app-header"><img src="${d.icon}" alt=""/>
        <div><h3>${d.title}</h3><p>${d.rating} stars - ${d.installs} installs</p></div>
      </div>
      <div class="score-section">
        <div class="score-ring ${cls}">${d.trust_score}</div>
        <div class="score-lbl ${cls}">${d.label}</div>
        <div class="score-sub">Trust Score out of 10</div>
      </div>
      <div class="stats">
        <div class="stat"><div class="val">${d.rating}</div><div class="key">Play Store Rating</div></div>
        <div class="stat"><div class="val">${d.avg_polarity}</div><div class="key">Sentiment Score</div></div>
        <div class="stat"><div class="val">${d.trust_score}/10</div><div class="key">Trust Score</div></div>
      </div>
      <div class="reasons"><h4>Analysis Details</h4>
        ${d.reasons.map(r=>`<div class="reason"><div class="dot" style="background:${dot}"></div>${r}</div>`).join(\'\')}
      </div>
      <hr class="divider"/>
      <div class="reviews-section"><h4>Top Reviews</h4>${revHTML}</div>`;
    $(\'card\').style.display=\'block\';
  }catch(e){
    $(\'spin\').style.display=\'none\';
    $(\'err\').textContent=\'Something went wrong. Try again.\';
    $(\'err\').style.display=\'block\';
  }
}
document.addEventListener(\'click\',e=>{if(!e.target.closest(\'.search-wrapper\'))$(\'sug\').style.display=\'none\';});
</script>
</body>
</html>
"""

# Setup
app = Flask(__name__)
MODEL_PATH = os.path.join(os.path.dirname(__file__), \'model.pkl\')
model = joblib.load(MODEL_PATH)

def _polarity(text):
    try:
        return TextBlob(str(text)).sentiment.polarity
    except Exception:
        return 0.0

def _compute_trust(app_data, avg_polarity):
    installs_str = str(app_data[\'installs\']).replace(\',\',\'\').replace(\'+\',\'\')
    installs     = int(installs_str) if installs_str.isdigit() else 1_000_000
    ratio        = app_data[\'reviews\'] / (installs + 1)
    mismatch     = int(app_data[\'score\'] >= 4.0 and avg_polarity < 0.0)
    fake_burst   = int(ratio > 0.05)
    live = pd.DataFrame([{
        \'Rating\': app_data[\'score\'], \'Avg_Polarity\': avg_polarity,
        \'Mismatch\': mismatch, \'Fake_Burst\': fake_burst,
        \'Review_Install_Ratio\': ratio
    }])
    prediction = model.predict(live)[0]
    score = 10.0
    if app_data[\'score\'] < 3.0: score -= 3
    if avg_polarity < 0.0:        score -= 2.5
    if mismatch:                   score -= 2
    if fake_burst:                 score -= 1.5
    score = round(max(score, 0), 1)
    reasons = []
    if mismatch:             reasons.append(\'High rating but negative reviews detected\')
    if fake_burst:           reasons.append(\'Suspicious review-to-install ratio\')
    if avg_polarity < 0.0:  reasons.append(\'Overall negative sentiment in reviews\')
    if app_data[\'score\']<3: reasons.append(\'Low rating on Play Store\')
    if not reasons:          reasons.append(\'No suspicious patterns detected\')
    return score, prediction, reasons

@app.route(\'/\')
def home():
    return HTML_PAGE, 200, {\'Content-Type\': \'text/html\'}

@app.route(\'/search\', methods=[\'POST\'])
def search_apps():
    query = request.json.get(\'query\', \'\')
    try:
        results = search(query, n_hits=6, lang=\'en\', country=\'us\')
        return jsonify({
            \'success\': True,
            \'results\': [
                {\'title\': r.get(\'title\',\'\'), \'appId\': r.get(\'appId\',\'\'),
                 \'icon\': r.get(\'icon\',\'\'), \'score\': r.get(\'score\',0)}
                for r in results if r.get(\'appId\')
            ]
        })
    except Exception as e:
        return jsonify({\'success\': False, \'error\': str(e)})

@app.route(\'/analyze\', methods=[\'POST\'])
def analyze():
    package_id = request.json.get(\'package_id\')
    try:
        app_data = gplay_app(package_id)
        rev, _   = gplay_reviews(package_id, count=100, lang=\'en\', country=\'us\')
        rev_df   = pd.DataFrame(rev)
        rev_df[\'Polarity\'] = rev_df[\'content\'].apply(_polarity)
        avg_pol  = round(rev_df[\'Polarity\'].mean(), 2)
        score, prediction, reasons = _compute_trust(app_data, avg_pol)
        top_reviews = []
        for _, row in rev_df.head(5).iterrows():
            p = row[\'Polarity\']
            if p > 0.1:    tag, color = \'Positive\', \'#10b981\'
            elif p < -0.1: tag, color = \'Negative\', \'#ef4444\'
            else:          tag, color = \'Neutral\',  \'#6b7280\'
            top_reviews.append({
                \'text\': str(row[\'content\'])[:200],
                \'score\': int(row[\'score\']),
                \'sentiment\': tag, \'color\': color
            })
        return jsonify({
            \'success\': True, \'title\': app_data[\'title\'],
            \'rating\': round(app_data[\'score\'],1), \'installs\': app_data[\'installs\'],
            \'icon\': app_data[\'icon\'], \'trust_score\': score,
            \'label\': prediction, \'avg_polarity\': avg_pol,
            \'reasons\': reasons, \'reviews\': top_reviews
        })
    except Exception as e:
        return jsonify({\'success\': False, \'error\': str(e)})

if __name__ == \'__main__\':
    app.run(debug=True)