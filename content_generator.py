import os
import requests
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def add_to_notion(title, content, tags=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    properties = {
        "标题": {"title": [{"text": {"content": title}}]},
        "内容": {"rich_text": [{"text": {"content": content}}]},
        "状态": {"select": {"name": "待审核"}},
        "AI生成": {"checkbox": True},
        "发布时间": {"date": {"start": datetime.now().isoformat()}}
    }
    
    if tags:
        properties["标签"] = {"multi_select": [{"name": tag} for tag in tags]}
    
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Added: {title} - {response.status_code}")
    return response.status_code == 200

if __name__ == "__main__":
    # 测试发布
    add_to_notion(
        "ChineseRocks 测试文章", 
        "这是从 GitHub Actions 自动发布的内容。\n\n摇滚不死！",
        tags=["朋克", "独立"]
    )
    print("Done!")
