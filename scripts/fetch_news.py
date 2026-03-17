#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseRocks 新闻抓取脚本 v5.1 - 修復版
修復 Notion API 調用和日期格式問題
"""

import os
import sys
import json
import hashlib
import re
import argparse
from datetime import datetime
from dateutil import parser as date_parser
import feedparser
import requests
from notion_client import Client
from bs4 import BeautifulSoup

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

# 擴展的新聞源配置
SOURCES = {
    "china": [
        {"name": "豆瓣音乐", "url": "https://www.douban.com/feed/review/music", "enabled": True, "category": "新聞"},
        {"name": "新浪音乐", "url": "https://rss.sina.com.cn/ent/music/focus15.xml", "enabled": True, "category": "新聞"},
    ],
    "international": [
        {"name": "Pitchfork", "url": "https://pitchfork.com/rss/news", "enabled": True, "category": "國際"},
        {"name": "Rolling Stone", "url": "https://www.rollingstone.com/music/feed/", "enabled": True, "category": "國際"},
        {"name": "NME", "url": "https://www.nme.com/news/music/feed", "enabled": True, "category": "國際"},
        {"name": "Stereogum", "url": "https://www.stereogum.com/feed", "enabled": True, "category": "國際"},
        {"name": "Consequence of Sound", "url": "https://consequenceofsound.net/feed", "enabled": True, "category": "國際"},
        {"name": "Billboard", "url": "https://www.billboard.com/feed/", "enabled": True, "category": "國際"},
    ],
    "hongkong_taiwan": [
        {"name": "KKBOX", "url": "https://www.kkbox.com/hk/tc/rss/news.xml", "enabled": True, "category": "新聞"},
    ],
    "test": [
        {"name": "豆瓣音乐", "url": "https://www.douban.com/feed/review/music", "enabled": True, "category": "新聞"},
    ]
}

class NewsFetcher:
    def __init__(self, source_type="china", limit=15):
        self.notion = Client(auth=NOTION_TOKEN)
        self.source_type = source_type
        self.limit = limit
        self.stats = {"total": 0, "added": 0, "skipped": 0, "exists": 0, "failed": 0}
        self.articles = []

    def fetch_all(self):
        print("\n" + "="*70)
        print("ChineseRocks 新闻抓取系统 v5.1")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"模式: {self.source_type}")
        print("="*70)

        sources = SOURCES.get(self.source_type, [])
        enabled_sources = [s for s in sources if s["enabled"]]
        print(f"\n抓取 {len(enabled_sources)} 个源")
        print("-"*50)

        for source in sources:
            if source["enabled"]:
                self._fetch_source(source)
            else:
                print(f"[{source['name']}] 已禁用")

        print(f"\n抓取完成: 共 {len(self.articles)} 条")
        return self.articles

    def _fetch_source(self, source):
        try:
            print(f"[{source['name']}]")
            feed = feedparser.parse(source['url'])

            count = 0
            for entry in feed.entries[:self.limit]:
                article = self._parse_entry(entry, source)
                if article:
                    self.articles.append(article)
                    count += 1

            print(f"  ✅ 成功獲取 {count} 条")

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            self.stats["failed"] += 1

    def _parse_entry(self, entry, source):
        """解析 RSS 條目"""
        try:
            summary = entry.get('summary', entry.get('description', ''))
            summary = self._clean_html(summary)

            # 修復日期解析
            published = self._parse_date(entry)

            # 獲取圖片
            image = self._extract_image(entry)

            # 生成唯一ID
            unique_id = hashlib.md5(
                f"{source['name']}_{entry.get('title', '')}".encode()
            ).hexdigest()[:12]

            return {
                "id": unique_id,
                "title": entry.get('title', '')[:200],
                "link": entry.get('link', ''),
                "summary": summary[:1000],
                "source_name": source['name'],
                "category": source.get('category', '新聞'),
                "published": published,
                "image": image,
            }
        except Exception as e:
            print(f"    解析條目失敗: {e}")
            return None

    def _parse_date(self, entry):
        """修復日期解析，返回 ISO 8601 格式"""
        try:
            # 嘗試多個日期字段
            date_str = entry.get('published', entry.get('updated', entry.get('pubDate', '')))

            if date_str:
                # 使用 dateutil 解析各種格式
                dt = date_parser.parse(date_str)
                return dt.strftime("%Y-%m-%d")
            else:
                # 默認今天
                return datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            print(f"    日期解析失敗，使用今天: {e}")
            return datetime.now().strftime("%Y-%m-%d")

    def _extract_image(self, entry):
        """從 RSS 條目提取圖片"""
        try:
            # 1. 檢查 media:content
            if 'media_content' in entry:
                for media in entry.media_content:
                    if media.get('type', '').startswith('image/'):
                        return media.get('url', '')

            # 2. 檢查 enclosures
            if 'enclosures' in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('image/'):
                        return enc.get('href', '')

            # 3. 從內容中提取
            content = entry.get('content', [{}])[0].get('value', '') if 'content' in entry else entry.get('summary', '')
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                img = soup.find('img')
                if img and img.get('src'):
                    return img['src']
        except:
            pass

        return ''

    def _clean_html(self, html):
        """清理 HTML 標籤"""
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def sync_to_notion(self):
        """同步到 Notion"""
        if not self.articles:
            print("\n沒有文章需要同步")
            return 0

        print("\n同步到 Notion")
        print("-"*50)

        added = 0
        exists = 0
        failed = 0

        for article in self.articles:
            result = self._add_to_notion(article)
            if result == "added":
                added += 1
                print(f"  ✅ {article['title'][:40]}...")
            elif result == "exists":
                exists += 1
                print(f"  ⏭️ 已存在: {article['title'][:30]}...")
            else:
                failed += 1
                print(f"  ❌ 失敗: {article['title'][:30]}...")

        self.stats["added"] = added
        self.stats["exists"] = exists
        self.stats["failed"] = failed
        return added

    def _add_to_notion(self, article):
        """添加單篇文章到 Notion - 修復版"""
        try:
            # 檢查是否已存在（使用 HTTP API 而不是 query 方法）
            if self._check_exists_http(article['title']):
                return "exists"

            # 準備標籤
            tags = [{"name": "新聞"}, {"name": "自動抓取"}, {"name": article['source_name']}]

            if article['category'] == "國際":
                tags.append({"name": "國際"})

            # 構建 properties
            properties = {
                "標題": {"title": [{"text": {"content": article['title'][:150]}}]},
                "內容": {"rich_text": [{"text": {"content": article['summary'][:2000]}}]},
                "狀態": {"select": {"name": "待審核"}},
                "類型": {"select": {"name": article['category']}},
                "標籤": {"multi_select": tags},
                "來源": {"url": article['link']} if article['link'] else {"url": None},
                "發布時間": {"date": {"start": article['published']}},
                "AI生成": {"checkbox": False},
                "是否會員專享": {"checkbox": False},
            }

            # 如果有圖片，添加到封面
            if article['image']:
                properties["封面圖"] = {
                    "files": [{"name": "cover", "external": {"url": article['image']}}]
                }

            self.notion.pages.create(
                parent={"database_id": NEWS_DB_ID},
                properties=properties
            )
            return "added"

        except Exception as e:
            print(f"    錯誤: {e}")
            return "failed"

    def _check_exists_http(self, title):
        """使用 HTTP API 檢查文章是否已存在"""
        try:
            import urllib.request

            url = f"https://api.notion.com/v1/databases/{NEWS_DB_ID}/query"
            headers = {
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }

            data = {
                "filter": {
                    "property": "標題",
                    "title": {
                        "equals": title[:100]
                    }
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return len(result.get('results', [])) > 0

        except Exception as e:
            print(f"    檢查存在性失敗: {e}")
            return False

    def print_report(self):
        """打印報告"""
        print("\n" + "="*70)
        print("執行報告")
        print("="*70)
        print(f"總抓取: {len(self.articles)} 条")
        print(f"新增入庫: {self.stats['added']} 条")
        print(f"已存在: {self.stats['exists']} 条")
        print(f"失敗: {self.stats['failed']} 条")
        print("="*70)

def main():
    parser = argparse.ArgumentParser(description="ChineseRocks 新聞抓取")
    parser.add_argument('--source', default='test', 
                       choices=['china', 'international', 'hongkong_taiwan', 'test'], 
                       help='抓取源類型')
    parser.add_argument('--limit', type=int, default=15, help='每源抓取數量')
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("錯誤: NOTION_TOKEN 未設置")
        sys.exit(1)

    fetcher = NewsFetcher(source_type=args.source, limit=args.limit)
    fetcher.fetch_all()

    if fetcher.articles:
        fetcher.sync_to_notion()

    fetcher.print_report()

if __name__ == "__main__":
    main()
