#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseRocks 新闻抓取脚本 v6.1 - 完整搖滾風格版
包含所有搖滾子類型：SKA & REGGAE, HEAVY & METAL, POP ROCK, 
ART & EXPERIMENTAL, INDIE & ALTERNATIVE, FOLK & ROOTS ROCK, PUNK & HARDCORE
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

# Cloudinary 配置
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NEWS_DB_ID = os.getenv("NEWS_DB_ID", "3229f94580b78029ba1bf49e33e7e46c")

# 完整音樂風格分類
MUSIC_GENRES = {
    "PUNK & HARDCORE": {
        "keywords": ["punk", "朋克", "hardcore", "硬核", "emo", "screamo", "post-hardcore"],
        "weight": 10
    },
    "HEAVY & METAL": {
        "keywords": ["metal", "金屬", "heavy", "thrash", "death metal", "black metal", "doom", "sludge"],
        "weight": 10
    },
    "INDIE & ALTERNATIVE": {
        "keywords": ["indie", "獨立", "alternative", "另類", "lo-fi", "shoegaze", "dream pop"],
        "weight": 9
    },
    "SKA & REGGAE": {
        "keywords": ["ska", "reggae", "雷鬼", "dub", "rocksteady"],
        "weight": 8
    },
    "POP ROCK": {
        "keywords": ["pop rock", "power pop", "indie pop", "synth-pop", "garage rock"],
        "weight": 7
    },
    "FOLK & ROOTS ROCK": {
        "keywords": ["folk", "民謠", "roots", "country rock", "americana", "bluegrass", "blues rock"],
        "weight": 7
    },
    "ART & EXPERIMENTAL": {
        "keywords": ["experimental", "實驗", "avant-garde", "noise", "post-rock", "後搖", "math rock", "prog", "progressive"],
        "weight": 6
    },
    "ROCK 通用": {
        "keywords": ["rock", "搖滾", "band", "樂隊", "guitar", "吉他", "bass", "drum"],
        "weight": 5
    }
}

# 排除的流行音樂類型
EXCLUDE_GENRES = ["k-pop", "hip-hop", "rap", "edm", "electronic dance", "pop music", "r&b", "soul"]

SOURCES = {
    "china": [
        {"name": "豆瓣音樂-搖滾", "url": "https://www.douban.com/feed/review/music", "enabled": True, "category": "新聞"},
    ],
    "international": [
        {"name": "Pitchfork", "url": "https://pitchfork.com/rss/news", "enabled": True, "category": "國際"},
        {"name": "Rolling Stone", "url": "https://www.rollingstone.com/music/feed/", "enabled": True, "category": "國際"},
        {"name": "NME", "url": "https://www.nme.com/news/music/feed", "enabled": True, "category": "國際"},
        {"name": "Kerrang", "url": "https://www.kerrang.com/feed", "enabled": True, "category": "國際"},
        {"name": "Louder Sound", "url": "https://www.loudersound.com/feeds/all", "enabled": True, "category": "國際"},
        {"name": "Ultimate Classic Rock", "url": "https://ultimateclassicrock.com/feed/", "enabled": True, "category": "國際"},
    ],
    "hongkong_taiwan": [
        {"name": "KKBOX-搖滾", "url": "https://www.kkbox.com/hk/tc/rss/news.xml", "enabled": True, "category": "新聞"},
    ],
    "test": [
        {"name": "豆瓣音樂", "url": "https://www.douban.com/feed/review/music", "enabled": True, "category": "新聞"},
    ]
}

class NewsFetcher:
    def __init__(self, source_type="china", limit=5):
        self.notion = Client(auth=NOTION_TOKEN)
        self.source_type = source_type
        self.limit = limit
        self.stats = {"total": 0, "added": 0, "skipped": 0, "exists": 0, "failed": 0, "image_uploaded": 0, "filtered": 0}
        self.articles = []
        self.cloudinary_enabled = all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ])

    def fetch_all(self):
        print("\n" + "="*70)
        print("ChineseRocks 新闻抓取系统 v6.1 - 完整搖滾風格版")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"模式: {self.source_type}")
        print(f"每源限制: {self.limit} 条")
        print(f"Cloudinary: {'已啟用' if self.cloudinary_enabled else '未啟用'}")
        print("="*70)

        sources = SOURCES.get(self.source_type, [])
        enabled_sources = [s for s in sources if s["enabled"]]
        print(f"\n抓取 {len(enabled_sources)} 个搖滾音樂源")
        print("-"*50)

        for source in sources:
            if source["enabled"]:
                self._fetch_source(source)
            else:
                print(f"[{source['name']}] 已禁用")

        print(f"\n抓取完成: 共 {len(self.articles)} 条 (已過濾非搖滾內容)")
        return self.articles

    def _fetch_source(self, source):
        try:
            print(f"[{source['name']}]")
            feed = feedparser.parse(source['url'])

            if not feed.entries:
                print(f"  ⚠️ 無法獲取 RSS 內容")
                return

            count = 0
            filtered_count = 0

            for entry in feed.entries:
                if count >= self.limit:
                    break

                # 檢查是否為搖滾內容
                genres = self._detect_genres(entry)
                if not genres:
                    filtered_count += 1
                    continue

                article = self._parse_entry(entry, source, genres)
                if article:
                    self.articles.append(article)
                    count += 1

            print(f"  ✅ 成功獲取 {count} 条 (過濾 {filtered_count} 條非搖滾內容)")

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            self.stats["failed"] += 1

    def _detect_genres(self, entry):
        """檢測文章音樂風格，返回匹配的風格列表"""
        text = f"{entry.get('title', '')} {entry.get('summary', '')} {entry.get('description', '')}".lower()

        # 檢查是否為排除的流行音樂
        for exclude in EXCLUDE_GENRES:
            if exclude in text:
                return []

        # 檢測匹配的風格
        matched_genres = []
        for genre_name, genre_info in MUSIC_GENRES.items():
            for keyword in genre_info["keywords"]:
                if keyword.lower() in text:
                    matched_genres.append((genre_name, genre_info["weight"]))
                    break

        # 按權重排序
        matched_genres.sort(key=lambda x: x[1], reverse=True)
        return [g[0] for g in matched_genres[:3]]  # 返回前3個最匹配的風格

    def _parse_entry(self, entry, source, genres):
        """解析 RSS 條目"""
        try:
            summary = entry.get('summary', entry.get('description', ''))
            summary = self._clean_html(summary)

            published = self._parse_date(entry)
            image = self._extract_image(entry)

            # 上傳圖片到 Cloudinary
            if image and self.cloudinary_enabled:
                print(f"    上傳圖片到 Cloudinary...")
                image = self._upload_to_cloudinary(image, source['name'])
                if image:
                    self.stats["image_uploaded"] += 1

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
                "genres": genres  # 音樂風格標籤
            }
        except Exception as e:
            print(f"    解析條目失敗: {e}")
            return None

    def _upload_to_cloudinary(self, image_url, source_name):
        """上傳圖片到 Cloudinary"""
        try:
            public_id = f"chineserocks/{source_name}_{hashlib.md5(image_url.encode()).hexdigest()[:12]}"

            result = cloudinary.uploader.upload(
                image_url,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
                folder="chineserocks"
            )

            print(f"    ✅ 上傳成功")
            return result['secure_url']

        except Exception as e:
            print(f"    ⚠️ 上傳失敗，使用原圖")
            return image_url

    def _parse_date(self, entry):
        try:
            date_str = entry.get('published', entry.get('updated', entry.get('pubDate', '')))
            if date_str:
                dt = date_parser.parse(date_str)
                return dt.strftime("%Y-%m-%d")
            else:
                return datetime.now().strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")

    def _extract_image(self, entry):
        try:
            if 'media_content' in entry:
                for media in entry.media_content:
                    if media.get('type', '').startswith('image/'):
                        return media.get('url', '')

            if 'enclosures' in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('image/'):
                        return enc.get('href', '')

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
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def sync_to_notion(self):
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
                print(f"  ✅ {article['title'][:40]}... [{', '.join(article['genres'][:2])}]")
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
        try:
            if self._check_exists_http(article['title']):
                return "exists"

            # 構建標籤
            tags = [{"name": "新聞"}, {"name": "自動抓取"}, {"name": article['source_name']}]

            # 添加音樂風格標籤
            for genre in article.get('genres', []):
                if genre != "ROCK 通用":  # 不添加通用標籤
                    tags.append({"name": genre})

            if article['category'] == "國際":
                tags.append({"name": "國際"})

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
        try:
            import urllib.request
            url = f"https://api.notion.com/v1/databases/{NEWS_DB_ID}/query"
            headers = {
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            data = {"filter": {"property": "標題", "title": {"equals": title[:100]}}}
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return len(result.get('results', [])) > 0
        except:
            return False

    def print_report(self):
        print("\n" + "="*70)
        print("執行報告")
        print("="*70)
        print(f"總抓取: {len(self.articles)} 条")
        print(f"圖片上傳: {self.stats['image_uploaded']} 张")
        print(f"新增入庫: {self.stats['added']} 条")
        print(f"已存在: {self.stats['exists']} 条")
        print(f"失敗: {self.stats['failed']} 条")
        print("="*70)

        # 風格統計
        if self.articles:
            print("\n風格分佈:")
            genre_count = {}
            for article in self.articles:
                for genre in article.get('genres', []):
                    genre_count[genre] = genre_count.get(genre, 0) + 1
            for genre, count in sorted(genre_count.items(), key=lambda x: x[1], reverse=True):
                print(f"  {genre}: {count} 条")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='test', 
                       choices=['china', 'international', 'hongkong_taiwan', 'test'])
    parser.add_argument('--limit', type=int, default=5, help='每源抓取數量')
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
