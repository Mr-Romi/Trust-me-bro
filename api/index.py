from flask import Flask, request, jsonify
import os

# app defined FIRST — Vercel scans top-level names at import time
app = Flask(__name__)

try:
    import joblib
    import pandas as pd
    from textblob import TextBlob
    from google_play_scraper import app as gplay_app, reviews as gplay_reviews, search
    MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model.pkl')
    model = joblib.load(MODEL_PATH)
    MODEL_LOADED = True
except Exception as _e:
    MODEL_LOADED = False
    MODEL_ERROR = str(_e)

HTML_PAGE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page.html')).read() if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page.html')) else "<h1>AppTrust</h1>"

@app.route('/')
def home():
    return HTML_PAGE, 200, {'Content-Type': 'text/html'}

@app.route('/health')
def health():
    return {'status': 'ok', 'model_loaded': MODEL_LOADED}

@app.route('/search', methods=['POST'])
def search_apps():
    if not MODEL_LOADED:
        return {'success': False, 'error': MODEL_ERROR}
    query = request.json.get('query', '')
    try:
        results = search(query, n_hits=6, lang='en', country='us')
        return {'success': True, 'results': [
            {'title': r.get('title',''), 'appId': r.get('appId',''),
             'icon': r.get('icon',''), 'score': r.get('score',0)}
            for r in results if r.get('appId')
        ]}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/analyze', methods=['POST'])
def analyze():
    if not MODEL_LOADED:
        return {'success': False, 'error': MODEL_ERROR}
    package_id = request.json.get('package_id')
    try:
        app_data = gplay_app(package_id)
        rev, _ = gplay_reviews(package_id, count=100, lang='en', country='us')
        rev_df = pd.DataFrame(rev)
        rev_df['Polarity'] = rev_df['content'].apply(lambda x: TextBlob(str(x)).sentiment.polarity if x else 0.0)
        avg_pol = round(rev_df['Polarity'].mean(), 2)

        installs_str = str(app_data['installs']).replace(',','').replace('+','')
        installs = int(installs_str) if installs_str.isdigit() else 1_000_000
        ratio = app_data['reviews'] / (installs + 1)
        mismatch = int(app_data['score'] >= 4.0 and avg_pol < 0.0)
        fake_burst = int(ratio > 0.05)

        live = pd.DataFrame([{
            'Rating': app_data['score'], 'Avg_Polarity': avg_pol,
            'Mismatch': mismatch, 'Fake_Burst': fake_burst,
            'Review_Install_Ratio': ratio
        }])
        prediction = model.predict(live)[0]

        score = 10.0
        if app_data['score'] < 3.0: score -= 3
        if avg_pol < 0.0: score -= 2.5
        if mismatch: score -= 2
        if fake_burst: score -= 1.5
        score = round(max(score, 0), 1)

        reasons = []
        if mismatch: reasons.append('High rating but negative reviews detected')
        if fake_burst: reasons.append('Suspicious review-to-install ratio')
        if avg_pol < 0.0: reasons.append('Overall negative sentiment in reviews')
        if app_data['score'] < 3: reasons.append('Low rating on Play Store')
        if not reasons: reasons.append('No suspicious patterns detected')

        top_reviews = []
        for _, row in rev_df.head(5).iterrows():
            p = row['Polarity']
            tag, color = ('Positive','#10b981') if p>0.1 else (('Negative','#ef4444') if p<-0.1 else ('Neutral','#6b7280'))
            top_reviews.append({'text': str(row['content'])[:200], 'score': int(row['score']), 'sentiment': tag, 'color': color})

        return {'success': True, 'title': app_data['title'],
                'rating': round(app_data['score'],1), 'installs': app_data['installs'],
                'icon': app_data['icon'], 'trust_score': score, 'label': prediction,
                'avg_polarity': avg_pol, 'reasons': reasons, 'reviews': top_reviews}
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    app.run(debug=True)
