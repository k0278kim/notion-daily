from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
import os
from fastapi.responses import HTMLResponse
from datetime import datetime
from fastapi import Header, HTTPException

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
    allow_headers=["*", "api-key"],   # Authorization, Content-Type 등
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
def fetch_notion(api_key: str = Header(None, alias="Api-Key")):
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

        res = requests.post(url, headers=headers, json={})

        if res.status_code != 200:
            return {"error": res.status_code, "message": res.text}

        return res.json()

def block_to_markdown(block, depth=0):
    """한 블록을 Markdown으로 변환"""
    t = block["type"]
    indent = "  " * depth  # 들여쓰기 (공백 2칸)

    if t == "paragraph":
        text = "".join([x["text"]["content"] for x in block[t]["rich_text"]])
        return indent + text + "\n"

    elif t.startswith("heading"):
        text = "".join([x["text"]["content"] for x in block[t]["rich_text"]])
        level = int(t[-1])
        return "#" * level + " " + text + "\n"

    elif t == "bulleted_list_item":
        text = "".join([x["text"]["content"] for x in block[t]["rich_text"]])
        return f"{indent}- {text}\n"

    elif t == "numbered_list_item":
        text = "".join([x["text"]["content"] for x in block[t]["rich_text"]])
        return f"{indent}1. {text}\n"

    else:
        return indent + "\n"


def fetch_block_children(block_id, depth=0):
    """Notion 블록 재귀 탐색"""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return []

    results = res.json().get("results", [])
    mds = []

    for block in results:
        mds.append(block_to_markdown(block, depth))

        if block.get("has_children", False):
            # 자식 블록 재귀적으로 불러오기
            mds.extend(fetch_block_children(block["id"], depth + 1))

    return mds


@app.get("/fetch_notion_doc_md")
def fetch_notion_doc_md(page_id: str, api_key: str = Header(None, alias="Api-Key")):
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    page_id = page_id.replace("-", "")
    md_blocks = fetch_block_children(page_id)
    return md_blocks

    
def response_to_md(res):
    results = res["results"]
    mds = []
    for row in results:
        mds.append(block_to_markdown(row))
    return mds

@app.get("/fetch_notion_snippet")
def fetch_notion_snippet_ids(date, api_key: str = Header(None, alias="Api-Key")):
    print("ㅗㅑ", api_key, os.getenv("API_SECRET_KEY"))
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
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
                    content = fetch_notion_doc_md(i["id"])
                    result.append({
                        "id": i["id"],
                        "name": names,
                        "relations": relations,
                        "who": [j["name"] for j in i["properties"]["Who"]["multi_select"]],
                        "who_email": [USER_EMAIL[j["name"]] for j in i["properties"]["Who"]["multi_select"]],
                        "content": content
                    })

        return result

@app.get("/fetch_notion_snippet_compare_check")
def fetch_notion_snippet_compare_check(date, api_key: str = Header(None, alias="Api-Key")):
    print("ㅗㅑ", api_key, os.getenv("API_SECRET_KEY"))
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        result = {
            "result": []
        }
        notion_snippet_ids = fetch_notion_snippet_ids(date)
        snippets = fetch_snippet(date, date)

        for notion in notion_snippet_ids:
            for snippet in snippets:
                if (notion["who_email"] and notion["who_email"][0] == snippet["user_email"]):
                    print(notion["content"], snippet["content"])
                    if (("\n".join(notion["content"])) == (snippet["content"])):
                        result["result"].append({ "user_email": notion["who_email"][0], "check": 1 })
                    else:
                        result["result"].append({ "user_email": notion["who_email"][0], "check": 2 })

        for user_email in USER_EMAIL.values():
            isin = False
            for dat in result["result"]:
                if (dat["user_email"] == user_email):
                    isin = True
            if (not isin):
                result["result"].append({ "user_email": user_email, "check": 0 })

        return result

@app.get("/fetch_notion_page_ids")
def fetch_notion_page_ids(api_key: str = Header(None, alias="Api-Key")):
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
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



@app.get("/fetch_snippet")
def fetch_snippet(date_from, date_to, api_key: str = Header(None, alias="Api-Key")):

    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
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
def add_snippet(snippet: Snippet, api_key: str = Header(None, alias="Api-Key")):

    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
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