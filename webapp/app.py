#!/usr/bin/env python3
"""
Flask web app for reviewing backchannel candidates
"""

from flask import Flask, render_template, jsonify, request, Response
import csv
import os
import io
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Initialize database
def init_db():
    db_path = os.path.join(os.path.dirname(__file__), 'annotations.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS annotations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_name TEXT NOT NULL,
                  candidate_id TEXT NOT NULL,
                  doc TEXT NOT NULL,
                  a_sent_id TEXT NOT NULL,
                  b_sent_id TEXT NOT NULL,
                  vote TEXT NOT NULL,
                  timestamp TEXT NOT NULL,
                  UNIQUE(user_name, candidate_id))''')
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)

# Load backchannel lexicon from file
def load_lexicon():
    lexicon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lexicon', 'sl_backchannels.txt')
    lexicon = []
    try:
        with open(lexicon_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    lexicon.append(line.lower())
    except FileNotFoundError:
        print(f"Warning: Lexicon file not found at {lexicon_path}")
    return sorted(lexicon)

LEXICON = load_lexicon()
print(f"Loaded {len(LEXICON)} lexicon words for webapp")

# Path to CSV file
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                        'output/sst/backchannel_candidates.csv')

def load_candidates():
    """Load candidates from CSV file"""
    candidates = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse attachment info for visualization
            if row.get('proposed_attach_root'):
                try:
                    # Format: sent_id::token_id
                    parts = row['proposed_attach_root'].split('::')
                    if len(parts) == 2:
                        row['attach_token_id'] = parts[1]
                except:
                    row['attach_token_id'] = None
            else:
                row['attach_token_id'] = None
            
            # Parse A tokens for highlighting
            if row.get('attach_token_id') and row.get('A_tokens'):
                try:
                    # A_tokens is space-separated
                    tokens = row['A_tokens'].split()
                    # Token IDs are 1-indexed
                    token_idx = int(row['attach_token_id']) - 1
                    if 0 <= token_idx < len(tokens):
                        row['attach_word'] = tokens[token_idx]
                    else:
                        row['attach_word'] = None
                except:
                    row['attach_word'] = None
            else:
                row['attach_word'] = None
            
            candidates.append(row)
    return candidates

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/candidates')
def get_candidates():
    """API endpoint to get all candidates with optional filters"""
    candidates = load_candidates()
    
    # Apply filters
    confidence_filter = request.args.get('confidence', '')
    sort_by = request.args.get('sort', '')
    min_tokens = request.args.get('min_tokens', type=int)
    max_tokens = request.args.get('max_tokens', type=int)
    min_score = request.args.get('min_score', type=int)
    max_score = request.args.get('max_score', type=int)
    search = request.args.get('search', '').lower()
    doc_filter = request.args.get('doc', '').lower()
    continuation = request.args.get('continuation', '')
    lexicon_filter = request.args.get('lexicon', '')  # Get lexicon filter
    
    # Parse lexicon words
    lexicon_words = []
    if lexicon_filter:
        lexicon_words = [w.strip().lower() for w in lexicon_filter.split(',') if w.strip()]
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Warning flags filters
    has_content = request.args.get('has_content', '')
    is_question = request.args.get('is_question', '')
    after_question = request.args.get('after_question', '')
    a_backchannel = request.args.get('a_backchannel', '')
    
    filtered = []
    for c in candidates:
        # Confidence filter
        if confidence_filter and c['confidence'] != confidence_filter:
            continue
        
        # Token count filter
        token_count = int(c['B_token_count'])
        if min_tokens and token_count < min_tokens:
            continue
        if max_tokens and token_count > max_tokens:
            continue
        
        # Score filter
        score = int(c['confidence_score'])
        if min_score is not None and score < min_score:
            continue
        if max_score is not None and score > max_score:
            continue
        
        # Search filter
        if search:
            searchable = f"{c['B_text']} {c['A_text']}".lower()
            if search not in searchable:
                continue
        
        # Document filter
        if doc_filter and doc_filter not in c['doc'].lower():
            continue
        
        # Lexicon filter - check if B_tokens contains any of the selected lexicon words
        if lexicon_words:
            b_tokens = c.get('B_tokens', '').lower().split()
            if not any(word in b_tokens for word in lexicon_words):
                continue
        
        # Continuation type filter
        if continuation:
            why = c['why_candidate'].lower()
            if continuation == 'immediate' and 'immediately' not in why:
                continue
            elif continuation == 'windowed' and ('within' not in why or 'immediately' in why):
                continue
            elif continuation == 'none' and 'no continuation' not in why:
                continue
        
        # Warning flags filters
        if has_content and c['B_has_content'] != has_content:
            continue
        if is_question and c['B_is_question'] != is_question:
            continue
        if after_question and c['B_after_question'] != after_question:
            continue
        if a_backchannel and c['A_looks_like_backchannel'] != a_backchannel:
            continue
        
        filtered.append(c)
    
    # Apply sorting
    if sort_by == 'score_desc':
        filtered.sort(key=lambda x: int(x['confidence_score']), reverse=True)
    elif sort_by == 'score_asc':
        filtered.sort(key=lambda x: int(x['confidence_score']))
    elif sort_by == 'tokens_asc':
        filtered.sort(key=lambda x: int(x['B_token_count']))
    elif sort_by == 'tokens_desc':
        filtered.sort(key=lambda x: int(x['B_token_count']), reverse=True)
    
    # Pagination
    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    return jsonify({
        'candidates': paginated,
        'total': total,
        'page': page,
        'per_page': per_page
    })

@app.route('/api/stats')
def get_stats():
    """Get statistics about candidates"""
    candidates = load_candidates()
    
    stats = {
        'total': len(candidates),
        'HIGH': sum(1 for c in candidates if c['confidence'] == 'HIGH'),
        'MEDIUM': sum(1 for c in candidates if c['confidence'] == 'MEDIUM'),
        'LOW': sum(1 for c in candidates if c['confidence'] == 'LOW'),
    }
    
    return jsonify(stats)

@app.route('/api/documents')
def get_documents():
    """Get all unique document IDs"""
    candidates = load_candidates()
    docs = sorted(set(c['doc'] for c in candidates))
    return jsonify(docs)

@app.route('/api/lexicon')
def get_lexicon():
    """Get backchannel lexicon words"""
    return jsonify(sorted(LEXICON))
    return jsonify(stats)

@app.route('/api/annotate', methods=['POST'])
def save_annotation():
    """Save user annotation"""
    data = request.json
    user_name = data.get('user_name')
    candidate_id = data.get('candidate_id')
    doc = data.get('doc')
    a_sent_id = data.get('a_sent_id')
    b_sent_id = data.get('b_sent_id')
    vote = data.get('vote')
    
    if not all([user_name, candidate_id, doc, a_sent_id, b_sent_id, vote]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    db_path = os.path.join(os.path.dirname(__file__), 'annotations.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('''INSERT OR REPLACE INTO annotations 
                     (user_name, candidate_id, doc, a_sent_id, b_sent_id, vote, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (user_name, candidate_id, doc, a_sent_id, b_sent_id, vote, datetime.now().isoformat()))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/annotations/<user_name>')
def get_user_annotations(user_name):
    """Get all annotations for a user"""
    db_path = os.path.join(os.path.dirname(__file__), 'annotations.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('SELECT candidate_id, vote FROM annotations WHERE user_name = ?', (user_name,))
    rows = c.fetchall()
    conn.close()
    
    annotations = {row[0]: row[1] for row in rows}
    return jsonify(annotations)

@app.route('/api/annotation-stats')
def get_annotation_stats():
    """Get annotation statistics"""
    db_path = os.path.join(os.path.dirname(__file__), 'annotations.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(DISTINCT user_name) FROM annotations')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM annotations')
    total_annotations = c.fetchone()[0]
    
    c.execute('''SELECT candidate_id, vote, COUNT(*) as count 
                 FROM annotations 
                 GROUP BY candidate_id, vote''')
    rows = c.fetchall()
    conn.close()
    
    candidate_votes = {}
    for row in rows:
        candidate_id, vote, count = row
        if candidate_id not in candidate_votes:
            candidate_votes[candidate_id] = {'yes': 0, 'no': 0}
        candidate_votes[candidate_id][vote] = count
    
    return jsonify({
        'total_users': total_users,
        'total_annotations': total_annotations,
        'candidate_votes': candidate_votes
    })

@app.route('/api/export')
def export_csv():
    """Export filtered candidates to CSV"""
    # Use same filtering logic as get_candidates
    candidates = load_candidates()
    
    # Apply same filters
    confidence_filter = request.args.get('confidence', '')
    sort_by = request.args.get('sort', '')
    min_tokens = request.args.get('min_tokens', type=int)
    max_tokens = request.args.get('max_tokens', type=int)
    min_score = request.args.get('min_score', type=int)
    max_score = request.args.get('max_score', type=int)
    search = request.args.get('search', '').lower()
    doc_filter = request.args.get('doc', '').lower()
    continuation = request.args.get('continuation', '')
    has_content = request.args.get('has_content', '')
    is_question = request.args.get('is_question', '')
    after_question = request.args.get('after_question', '')
    a_backchannel = request.args.get('a_backchannel', '')
    lexicon_words = request.args.get('lexicon', '').split(',') if request.args.get('lexicon') else []
    
    filtered = []
    for c in candidates:
        if confidence_filter and c['confidence'] != confidence_filter:
            continue
        token_count = int(c['B_token_count'])
        if min_tokens and token_count < min_tokens:
            continue
        if max_tokens and token_count > max_tokens:
            continue
        score = int(c['confidence_score'])
        if min_score is not None and score < min_score:
            continue
        if max_score is not None and score > max_score:
            continue
        if search:
            searchable = f"{c['B_text']} {c['A_text']}".lower()
            if search not in searchable:
                continue
        if doc_filter and doc_filter not in c['doc'].lower():
            continue
        if continuation:
            why = c['why_candidate'].lower()
            if continuation == 'immediate' and 'immediately' not in why:
                continue
            elif continuation == 'windowed' and ('within' not in why or 'immediately' in why):
                continue
            elif continuation == 'none' and 'no continuation' not in why:
                continue
        if has_content and c['B_has_content'] != has_content:
            continue
        if is_question and c['B_is_question'] != is_question:
            continue
        if after_question and c['B_after_question'] != after_question:
            continue
        if a_backchannel and c['A_looks_like_backchannel'] != a_backchannel:
            continue
        if lexicon_words:
            # Check if B_tokens contains any of the selected lexicon words
            b_tokens = c.get('B_tokens', '').lower().split()
            # Check for exact word match (word boundaries)
            has_match = False
            for word in lexicon_words:
                if word and word.lower() in b_tokens:
                    has_match = True
                    break
            if not has_match:
                continue
        filtered.append(c)
    
    # Apply sorting
    if sort_by == 'score_desc':
        filtered.sort(key=lambda x: int(x['confidence_score']), reverse=True)
    elif sort_by == 'score_asc':
        filtered.sort(key=lambda x: int(x['confidence_score']))
    elif sort_by == 'tokens_asc':
        filtered.sort(key=lambda x: int(x['B_token_count']))
    elif sort_by == 'tokens_desc':
        filtered.sort(key=lambda x: int(x['B_token_count']), reverse=True)
    
    # Create CSV in memory
    output = io.StringIO()
    if filtered:
        writer = csv.DictWriter(output, fieldnames=filtered[0].keys())
        writer.writeheader()
        writer.writerows(filtered)
    
    # Create response
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=backchannel_candidates_filtered.csv'
    return response

@app.route('/api/export-annotations/<user_name>')
def export_annotations(user_name):
    conn = sqlite3.connect('annotations.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''SELECT user_name, candidate_id, doc, a_sent_id, b_sent_id, vote, timestamp 
                 FROM annotations 
                 WHERE user_name = ?
                 ORDER BY timestamp''', (user_name,))
    
    annotations = [dict(row) for row in c.fetchall()]
    conn.close()
    
    output = io.StringIO()
    if annotations:
        writer = csv.DictWriter(output, fieldnames=['user_name', 'candidate_id', 'doc', 'a_sent_id', 'b_sent_id', 'vote', 'timestamp'])
        writer.writeheader()
        writer.writerows(annotations)
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=annotations_{user_name}.csv'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
