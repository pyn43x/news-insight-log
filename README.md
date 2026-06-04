# 뉴스 인사이트 로그

뉴스 기사 URL을 입력하면 본문을 자동 수집하고, AI가 논평을 생성해주는 웹 애플리케이션입니다.
claude를 이용한 바이브 코딩으로 구현했습니다.

## 주요 기능
- 기사 URL 입력 시 Jina Reader API로 본문 자동 수집
- Claude API를 활용한 AI 논평 생성
- 인사이트 저장 및 아카이브 관리 (SQLite)

## 사용 기술
- Python, Flask
- Jina Reader API
- Claude API
- SQLite

## 실행 방법
```bash
pip install -r requirements.txt
export CLAUDE_API_KEY=your_api_key_here
python app.py
```
