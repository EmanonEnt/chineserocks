#!/usr/bin/env python3
"""
ChineseRocks 新闻发布系统
从Notion获取已发布文章，生成前端JSON
"""

import os
import json
import re
from datetime import datetime
from notion_client import Client

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

def fetch_published_articles():
    """从Notion获取已发布的文章"""
    if not NOTION_TOKEN:
        print("❌ 错误: NOTION_TOKEN 未设置")
        return []
    
    notion = Client(auth=NOTION_TOKEN)
    articles = []
    
    try:
        # 新版API调用方式
        response = notion.databases.query(
            database_id=NEWS_DB_ID,
            filter={"property": "狀態", "status": {"equals": "已發布"}},
            sorts=[{"timestamp": "created_time", "direction": "descending"}],
            page_size=100
        )
        
        for page in response.get('results', []):
            props = page.get('properties', {})
            
            # 提取标签
            tags = extract_multi_select(props, '標籤')
            
            # 检测是否会员专享
            is_premium = (
                '會員專享' in tags or
                extract_checkbox(props, '是否會員專享') or
                '獨家' in tags
            )
            
            # 提取封面图
            cover_url = extract_url(props, '封面圖')
            if not cover_url:
                cover_url = get_default_image()
            
            article = {
                "id": page['id'],
                "title": extract_title(props),
                "content": extract_content(props),
                "summary": extract_content(props)[:150] + "...",
                "category": extract_select(props, '類型'),
                "tags": tags,
                "status": extract_status(props),
                "source_url": extract_url(props, '來源'),
                "published_date": extract_date(props, '發布時間'),
                "is_ai_generated": extract_checkbox(props, 'AI生成'),
                "featured": extract_checkbox(props, '頭條'),
                "is_premium": is_premium,
                "cover_image": cover_url
            }
            
            articles.append(article)
            print(f"✓ {article['title'][:40]}...")
            
    except Exception as e:
        print(f"❌ 获取文章失败: {e}")
        return []
    
    return articles

def extract_title(props):
    try:
        title_prop = props.get('標題', props.get('title', {}))
        if 'title' in title_prop and title_prop['title']:
            return title_prop['title'][0]['text']['content']
    except:
        pass
    return "无标题"

def extract_content(props):
    try:
        content_prop = props.get('內容', props.get('content', {}))
        if 'rich_text' in content_prop and content_prop['rich_text']:
            return content_prop['rich_text'][0]['text']['content']
    except:
        pass
    return ""

def extract_select(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'select' in prop and prop['select']:
            return prop['select']['name']
    except:
        pass
    return ""

def extract_status(props):
    try:
        prop = props.get('狀態', {})
        if 'status' in prop and prop['status']:
            return prop['status']['name']
    except:
        pass
    return ""

def extract_multi_select(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'multi_select' in prop:
            return [tag['name'] for tag in prop['multi_select']]
    except:
        pass
    return []

def extract_url(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'url' in prop:
            return prop['url']
    except:
        pass
    return ""

def extract_date(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'date' in prop and prop['date']:
            return prop['date']['start']
    except:
        pass
    return datetime.now().strftime('%Y-%m-%d')

def extract_checkbox(props, prop_name):
    try:
        prop = props.get(prop_name, {})
        if 'checkbox' in prop:
            return prop['checkbox']
    except:
        pass
    return False

def get_default_image():
    return "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop"

def save_to_json(articles):
    """保存到JSON文件"""
    output = {
        "updated_at": datetime.now().isoformat(),
        "total_count": len(articles),
        "data": {
            "all": articles,
            "hero": articles[:3] if len(articles) >= 3 else articles,
            "latest": articles
        }
    }
    
    os.makedirs('data', exist_ok=True)
    
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 已保存 {len(articles)} 篇文章到 data/news.json")

def main():
    print("="*60)
    print("🎸 ChineseRocks 新闻发布系统")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    articles = fetch_published_articles()
    
    if not articles:
        print("⚠️ 没有已发布的文章")
        # 创建空文件防止前端报错
        save_to_json([])
        return
    
    save_to_json(articles)
    
    print("="*60)
    print(f"📊 总计: {len(articles)} 篇文章")
    print("="*60)

if __name__ == "__main__":
    main()
