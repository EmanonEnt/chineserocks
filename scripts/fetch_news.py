#!/usr/bin/env python3
"""
ChineseRocks 新闻抓取脚本 v4.4 - 字段匹配修復版
"""

import os
import sys
import json
import hashlib
import re
import argparse
from datetime import datetime
import feedparser
import requests
from notion_client import Client
from bs4 import BeautifulSoup

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

SOURCES = {
    "china": [
        {"name": "豆瓣音乐", "url": "https://www.douban.com/feed/review/music", "enabled": True},
    ],
    "test": [
        {"name": "测试源", "url": "https://www.douban.com/feed/review/music", "enabled": True},
    ]
}

class NewsFetcher:
    def __init__(self, source_type="china", limit=1):
        self.notion = Client(auth=NOTION_TOKEN)
        self.source_type = source_type
        self.limit = limit
        self.stats = {"total": 0, "added": 0, "skipped": 0, "exists": 0}
        self.articles = []

    def fetch_all(self):
        print("\n" + "="*70)
        print("🎸 ChineseRocks 新闻抓取系统 v4.4")
        print(f" 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*70)

        sources = SOURCES.get(self.source_type, [])
        print(f"\n📡 抓取 {len([s for s in sources if s['enabled']])} 个源")
        print("-"*50)

        for source in sources:
            if source["enabled"]:
                self._fetch_source(source)

        print(f"\n📊 抓取完成: 共 {len(self.articles)} 条")
        return self.articles

    def _fetch_source(self, source):
        try:
            print(f"📡 [{source['name']}]")
            feed = feedparser.parse(source['url'])

            count = 0
            for entry in feed.entries[:self.limit]:
                article = self._parse_entry(entry, source)
                if article:
                    self.articles.append(article)
                    count += 1

            print(f" ✅ 获取 {count} 条")

        except Exception as e:
            print(f" ❌ 失败: {e}")

    def _parse_entry(self, entry, source):
        summary = entry.get('summary', entry.get('description', ''))
        summary = self._clean_html(summary)

        return {
            "title": entry.get('title', ''),
            "link": entry.get('link', ''),
            "summary": summary[:500],
            "source_name": source['name'],
        }

    def _clean_html(self, html):
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def sync_to_notion(self):
        print("\n💾 同步到 Notion")
        print("-"*50)

        added = 0
        exists = 0

        for article in self.articles:
            if self._check_exists(article['title']):
                print(f" ⏭️ 已存在: {article['title'][:40]}...")
                exists += 1
                continue

            if self._add_to_notion(article):
                added += 1
                print(f" ✅ 新增: {article['title'][:40]}...")
            else:
                print(f" ❌ 失败: {article['title'][:40]}...")

        self.stats["added"] = added
        self.stats["exists"] = exists
        return added

    def _check_exists(self, title):
        try:
            response = self.notion.databases.query(
                database_id=NEWS_DB_ID,
                filter={
                    "property": "標題",
                    "title": {"equals": title}
                }
            )
            return len(response['results']) > 0
        except Exception as e:
            print(f" ⚠️ 检查存在性失败: {e}")
            return False

    def _add_to_notion(self, article):
        try:
            # 正確字段名（根據截圖）
            properties = {
                "標題": {"title": [{"text": {"content": article['title'][:150]}}]},
                "內容": {"rich_text": [{"text": {"content": article['summary'][:2000]}}]},
                "狀態": {"select": {"name": "待審核"}},
                "類型": {"select": {"name": "新聞"}},  # 不是"分類"！
                "標籤": {"multi_select": [{"name": "新聞"}, {"name": "自動抓取"}]},
                "來源": {"url": article['link']},
                "發布時間": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},  # 不是"發布日期"！
                "AI生成": {"checkbox": False},
                "是否會員專享": {"checkbox": False},
            }

            self.notion.pages.create(
                parent={"database_id": NEWS_DB_ID},
                properties=properties
            )
            return True
        except Exception as e:
            print(f" ❌ Notion API 错误: {e}")
            import traceback
            traceback.print_exc()
            return False

    def print_report(self):
        print("\n" + "="*70)
        print("📈 执行报告")
        print("="*70)
        print(f" 总抓取: {len(self.articles)} 条")
        print(f" 新增入库: {self.stats['added']} 条")
        print(f" 已存在: {self.stats['exists']} 条")
        print("="*70)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='test', choices=['china', 'test'], help='抓取源类型')
    parser.add_argument('--limit', type=int, default=1, help='每源抓取数量')
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("❌ 错误: NOTION_TOKEN 未设置")
        sys.exit(1)

    fetcher = NewsFetcher(source_type=args.source, limit=args.limit)
    fetcher.fetch_all()

    if fetcher.articles:
        fetcher.sync_to_notion()

    fetcher.print_report()

if __name__ == "__main__":
    main()
