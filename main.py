from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
import os
from fastapi.responses import HTMLResponse
from datetime import datetime

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 허용할 Origin 지정 (배포된 Next.js 도메인 포함)
origins = [
    "http://localhost:3000",          # 개발용
    "https://your-next-app.vercel.app",  # 배포된 Next.js 도메인
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST 등
    allow_headers=["*"],   # Authorization, Content-Type 등
)


load_dotenv()  # .env 파일 읽기

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
SNIPPET_TOKEN = os.getenv("SNIPPET_TOKEN")

DATABASE_TITLE_ID = "Name"
DATABASE_AREA = "Area/Resource"
DATABASE_SNIPPET_ID = "27645c06-3330-80d7-b46d-d88b0dda1ab8"

USER_EMAIL = {
    "뚜뚜": "ocean1229@gachon.ac.kr",
    "양털": "k0278kim@gachon.ac.kr",
    "도다리": "rimx2@gachon.ac.kr"
}

app = FastAPI()

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

@app.get("/now")
def get_server_time():
    now = datetime.now()  # 서버 시간
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "iso": now.isoformat()
    }

@app.get("/fetch_notion")
def fetch_notion():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    res = requests.post(url, headers=headers, json={})

    if res.status_code != 200:
        return {"error": res.status_code, "message": res.text}

    return res.json()

def block_to_markdown(block):
    t = block["type"]
    if t == "paragraph":
        text = "".join([x["text"]["content"] for x in block[t]["rich_text"]])
        return text + "\n"
    elif t.startswith("heading"):
        text = "".join([x["text"]["content"] for x in block[t]["rich_text"]])
        level = int(t[-1])
        return "#" * level + " " + text + "\n"
    elif t == "bulleted_list_item":
        text = "- ".join([x["text"]["content"] for x in block[t]["rich_text"]])
        return f"- {text}\n"
    elif t == "numbered_list_item":
        text = "".join([x["text"]["content"] for x in block[t]["rich_text"]])
        return f"1. {text}\n"
    else:
        return ""  # 다른 타입은 필요시 확장
    
def response_to_md(res):
    results = res["results"]
    mds = []
    for row in results:
        mds.append(block_to_markdown(row))
    return mds

@app.get("/fetch_notion_snippet")
def fetch_notion_snippet_ids(date):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    res = requests.post(url, headers=headers, json={})
    result = []

    if res.status_code != 200:
        return {"error": res.status_code, "message": res.text}
    
    res = res.json()["results"]
    
    for i in res:
        relations = []
        for j in i["properties"][DATABASE_AREA]["relation"]:
            relations.append(j["id"])
        if (DATABASE_SNIPPET_ID in relations and i["properties"]["날짜"]["date"]):
            notion_date = i["properties"]["날짜"]["date"]["start"]
            if (notion_date == date):
                type = i["properties"][DATABASE_TITLE_ID]["type"]
                names = []
                for j in i["properties"][DATABASE_TITLE_ID][type]:
                    names.append(j["text"]["content"])
                result.append({
                    "id": i["id"],
                    "name": names,
                    "relations": relations,
                    "who": [j["name"] for j in i["properties"]["Who"]["multi_select"]],
                    "who_email": [USER_EMAIL[j["name"]] for j in i["properties"]["Who"]["multi_select"]]
                })

    return result

@app.get("/fetch_notion_page_ids")
def fetch_notion_page_ids():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    res = requests.post(url, headers=headers, json={})
    result = []

    if res.status_code != 200:
        return {"error": res.status_code, "message": res.text}
    
    res = res.json()["results"]
    
    for i in res:
        type = i["properties"][DATABASE_TITLE_ID]["type"]
        result.append({
            "id": i["id"],
            "name": [j["text"]["content"] for j in i["properties"][DATABASE_TITLE_ID][type]],
            "who": [j["name"] for j in i["properties"]["Who"]["multi_select"]]
        })

    return result


@app.get("/fetch_notion_doc_md")
def fetch_notion_doc_md(page_id):
    page_id = page_id.replace("-", "")

    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return {"error": res.status_code, "message": res.text}
        
    result = response_to_md(res.json())

    return result

@app.get("/fetch_snippet")
def fetch_snippet(date_from, date_to):

    url = f"https://n8n.1000.school/webhook/ae38a67a-6dbd-4404-8a54-74c565b1868e?api_id={SNIPPET_TOKEN}&date_from={date_from}&date_to={date_to}"
    res = requests.get(url)

    if res.status_code != 200:
        return {"error": res.status_code, "message": res.text}

    return res.json()[0]["snippets"]

from pydantic import BaseModel

class Snippet(BaseModel):
    user_email: str
    snippet_date: str
    content: str

@app.post("/add_snippet")
def add_snippet(snippet: Snippet):
    url = "https://n8n.1000.school/webhook/0a43fbad-cc6d-4a5f-8727-b387c27de7c8/"
    data = {
        "user_email": snippet.user_email,
        "api_id": SNIPPET_TOKEN,
        "snippet_date": snippet.snippet_date,
        "content": snippet.content
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/html"   # ← text/html 응답을 원한다는 힌트
    }
    print(data)
    res = requests.post(url, json=data, headers=headers)

    if res.status_code != 200:
        return {"error": res.status_code, "message": res.text}

    return res.json()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <body>
        <h1>Notion DB 조회</h1>
        <input type="text" id="textid" />
        <input type="text" id="snippetid" placeholder="snippet 작성" />
        <button onclick="fetchPageIds()">페이지 ID 가져오기</button>
        <button onclick="fetchData()">자세히 조회하기</button>
        <button onclick="fetchDocData(document.getElementById('textid').value)">md</button>
        <button onclick="fetchSnippet('2025-09-22', '2025-09-22')">스니펫 불러오기</button>
        <button onclick="addSnippet('k0278kim@gachon.ac.kr', '2025-09-23', document.getElementById('snippetid').value)">스니펫 작성</button>
        <div style="display: flex;">
            <pre id="output" style=""></pre>
            <pre id="output2" style=""></pre>
        </div>
        <script>

          async function fetchPageIds() {
            const res = await fetch('/fetch_notion_page_ids');
            const data = await res.json();
            document.getElementById('output').textContent = JSON.stringify(data, null, 2);
          }

          async function fetchData() {
            const res = await fetch('/fetch_notion');
            const data = await res.json();
            document.getElementById('output').textContent = JSON.stringify(data, null, 2);
          }

          async function fetchDocData(id) {
            const res = await fetch('/fetch_notion_doc_md?page_id='+id);
            const data = await res.json();
            document.getElementById('output2').textContent = JSON.stringify(data, null, 2);
          }

          async function fetchSnippet(date_from, date_to) {
            const res = await fetch('/fetch_snippet?date_from='+date_from+'&date_to='+date_to);
            const data = await res.json();
            console.log(data);
          }
          async function addSnippet(email, date, content) {
            console.log("addSnippet");
            const data = {
                user_email: email,
                snippet_date: date,
                content: content
            };
            const res = await fetch("/add_snippet", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            console.log("서버 응답:", result);
            }
        </script>
      </body>
    </html>
    """