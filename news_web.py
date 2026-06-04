# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import requests
import sqlite3
import os
from datetime import datetime
import anthropic

app = Flask(__name__)

# DB 초기화
def init_db():
    db_path = os.path.join(os.path.dirname(__file__), 'insight_log.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        title TEXT,
        image TEXT,
        summary TEXT,
        content TEXT,
        tags TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def scrape_article(url):
    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(jina_url, headers=headers, timeout=15)
        resp.raise_for_status()
        markdown = resp.text.strip()

        if not markdown:
            return {"error": "본문을 추출할 수 없습니다."}

        lines = markdown.split('\n')
        title = "제목 없음"
        text = markdown
        for i, line in enumerate(lines):
            if line.startswith('# '):
                title = line[2:].strip()
                text = '\n'.join(lines[i+1:]).strip()
                break

        summary = text[:300] + "..." if len(text) > 300 else text

        return {
            "title": title,
            "summary": summary,
            "text": text,
            "image": "",
            "source": "jina"
        }

    except requests.exceptions.Timeout:
        return {"error": "요청 시간이 초과됐습니다. 다시 시도해 주세요."}
    except requests.exceptions.ConnectionError:
        return {"error": "URL에 연결할 수 없습니다. 주소를 확인해 주세요."}
    except Exception as e:
        return {"error": f"스크래핑 중 오류가 발생했습니다: {str(e)}"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze_url():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL을 입력해 주세요."}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    result = scrape_article(url)
    return jsonify(result)


@app.route("/api/save", methods=["POST"])
def save_insight():
    data = request.get_json()
    url = data.get("url", "")
    title = data.get("title", "")
    image = data.get("image", "")
    summary = data.get("summary", "")
    content = data.get("content", "")
    tags = data.get("tags", "")

    if not url or not content:
        return jsonify({"error": "URL과 내용은 필수입니다."}), 400

    db_path = os.path.join(os.path.dirname(__file__), 'insight_log.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''INSERT INTO insights (url, title, image, summary, content, tags, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (url, title, image, summary, content, tags, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return jsonify({"message": "저장되었습니다."})


@app.route("/api/update_insight", methods=["POST"])
def update_insight():
    data = request.get_json()
    id = data.get("id")
    content = data.get("content", "").strip()

    if not id or not content:
        return jsonify({"error": "ID와 내용은 필수입니다."}), 400

    db_path = os.path.join(os.path.dirname(__file__), 'insight_log.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('UPDATE insights SET content = ? WHERE id = ?', (content, id))
    conn.commit()
    conn.close()

    return jsonify({"message": "수정되었습니다."})


@app.route("/api/delete_insight/<int:id>", methods=["DELETE"])
def delete_insight(id):
    db_path = os.path.join(os.path.dirname(__file__), 'insight_log.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM insights WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "삭제되었습니다."})


@app.route("/api/feedback", methods=["POST"])
def get_feedback():
    data = request.get_json()
    summary = data.get("summary", "")
    insight = data.get("insight", "")

    if not summary or not insight:
        return jsonify({"error": "요약과 인사이트는 필수입니다."}), 400

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = f"너는 날카롭고 통찰력 있는 사회학자이자 글쓰기 코치야. 다음 기사 내용과 나의 분석을 읽고, 내 생각의 논리적 허점을 짚어주거나 더 깊이 생각해 볼 만한 새로운 관점(질문)을 3줄 이내로 제시해 줘.\n\n기사 내용: {summary}\n\n나의 분석: {insight}"

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        feedback = message.content[0].text.strip()
        return jsonify({"feedback": feedback})
    except Exception as e:
        return jsonify({"error": f"AI 피드백 생성 중 오류: {str(e)}"}), 500


@app.route("/archive")
def archive():
    db_path = os.path.join(os.path.dirname(__file__), 'insight_log.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT id, url, title, image, summary, content, tags, created_at FROM insights ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()

    insights = []
    for row in rows:
        insights.append({
            "id": row[0],
            "url": row[1],
            "title": row[2],
            "image": row[3],
            "summary": row[4],
            "content": row[5],
            "tags": row[6],
            "created_at": row[7]
        })

    return render_template("archive.html", insights=insights)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5001)
