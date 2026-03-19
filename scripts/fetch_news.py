#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseRocks 新闻抓取脚本 v8.8.8 - 中國源更新版
- 修復週五 04:00 雙重觸發問題
- 更新台灣 RSS 源，添加更多可用源
- 優化圖片抓取邏輯
- 添加深晨 DOPM 和播客源
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

# 嚴格搖滾風格分類
MUSIC_GENRES = {
    "PUNK & HARDCORE": {
        "keywords": ["punk", "朋克", "hardcore", "硬核", "emo", "screamo", "post-hardcore", "oi", "crust"],
        "weight": 10
    },
    "HEAVY & METAL": {
        "keywords": ["metal", "金屬", "heavy", "thrash", "death metal", "black metal", "doom", "sludge", "stoner", "grindcore"],
        "weight": 10
    },
    "INDIE & ALTERNATIVE": {
        "keywords": ["indie", "獨立", "alternative", "另類", "lo-fi", "shoegaze", "dream pop", "britpop", "grunge"],
        "weight": 9
    },
    "SKA & REGGAE": {
        "keywords": ["ska", "reggae", "雷鬼", "dub", "rocksteady", "ska-punk"],
        "weight": 8
    },
    "GARAGE & PSYCHEDELIC": {
        "keywords": ["garage", "車庫", "psychedelic", "迷幻", "space rock", "krautrock"],
        "weight": 7
    },
    "FOLK & ROOTS ROCK": {
        "keywords": ["folk", "民謠", "roots", "country rock", "americana", "bluegrass", "blues rock", "southern rock"],
        "weight": 7
    },
    "ART & EXPERIMENTAL": {
        "keywords": ["experimental", "實驗", "avant-garde", "noise", "post-rock", "後搖", "math rock", "prog", "progressive"],
        "weight": 6
    },
    "ROCK 通用": {
        "keywords": ["rock", "搖滾", "band", "樂隊", "guitar", "吉他", "bass", "drum", "live", "演出"],
        "weight": 5
    }
}

# 嚴格排除所有非搖滾音樂
EXCLUDE_GENRES = [
    "k-pop", "j-pop", "c-pop", "mandopop", "cantopop", 
    "pop music", "teen pop", "synth-pop", "electropop",
    "hip-hop", "rap", "trap", "r&b", "soul", "funk", "disco",
    "edm", "electronic", "house", "techno", "trance", "dubstep", 
    "drum and bass", "dnb", "ambient", "idm",
    "classical", "opera", "jazz", "new age", "world music"
]

# 完整新聞源配置 - v8.8.7 最終版
SOURCES = {
        "china": [
        {
            "name": "豆瓣音樂-搖滾", 
            "url": "https://www.douban.com/feed/review/music", 
            "enabled": True, 
            "category": "新聞",
        },
        # 主唱死了 - 上海地下音樂播客 (已驗證可用)
        {
            "name": "主唱死了-器樂搖滾播客", 
            "url": "https://zhuchangsile.xyz/episodes/feed.xml", 
            "enabled": True, 
            "category": "新聞",
        },
        # Live China Music - 中國獨立音樂現場報導 (權威源)
        {
            "name": "Live China Music-獨立音樂現場", 
            "url": "https://livechinamusic.com/feed", 
            "enabled": True, 
            "category": "新聞",
        },
        # China Music Radar - 中國音樂產業趨勢分析
        {
            "name": "China Music Radar-音樂產業", 
            "url": "https://chinamusicradar.com/feed", 
            "enabled": True, 
            "category": "新聞",
        },
        # Wooozy - 中國地下/主流音樂 (2009年創立的老牌媒體)
        {
            "name": "Wooozy-地下音樂", 
            "url": "https://wooozy.cn/feed", 
            "enabled": True, 
            "category": "新聞",
        },
        # 摩登天空 - 網易號 RSS (通過 RSSHub)
        {
            "name": "摩登天空-網易號", 
            "url": "https://rsshub.app/163/dy/T1509089140270", 
            "enabled": True, 
            "category": "新聞",
        },
        # StreetVoice 街聲中國站
        {
            "name": "街聲-中國獨立音樂", 
            "url": "https://streetvoice.cn/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
        # Blow 吹音樂 - Line Toady 標籤 (獨立音樂大小事)
        {
            "name": "Blow-Line Toady", 
            "url": "https://blow.streetvoice.com/t/line-toady/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
        # 一碗雜炊 - StreetVoice 播客
        {
            "name": "一碗雜炊-街聲播客", 
            "url": "https://streetvoice.com/blowyourheart/podcast/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
        # 滾圈海底撈 - 微博演出 RSS (通過 RSSHub)
        {
            "name": "滾圈海底撈-演出信息", 
            "url": "https://rsshub.app/weibo/user/3691972875", 
            "enabled": False,  # 需要微博 Cookie，暫時禁用
            "category": "新聞",
        },
        # 巡演 RSS - 微博演出信息 (通過 RSSHub)
        {
            "name": "巡演RSS-演出播報", 
            "url": "https://rsshub.app/weibo/user/3691972875", 
            "enabled": False,  # 需要微博 Cookie，暫時禁用
            "category": "新聞",
        },
    ],

    "taiwan": [
        # Blow 吹音樂系列 (已驗證可用，有圖片)
        {
            "name": "Blow吹音樂", 
            "url": "https://blow.streetvoice.com/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
        {
            "name": "Blow吹音樂-人物", 
            "url": "https://blow.streetvoice.com/c/people/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
        {
            "name": "Blow吹音樂-議題", 
            "url": "https://blow.streetvoice.com/c/issue/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
        {
            "name": "Blow吹音樂-新聞", 
            "url": "https://blow.streetvoice.com/c/news/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
        # 深晨 DOPM (台灣獨立音樂網站)
        {
            "name": "深晨DOPM", 
            "url": "https://deepperfectmorning.com/blog?format=rss", 
            "enabled": True, 
            "category": "新聞",
        },
        # 小明拆台 (獨立音樂播客)
        {
            "name": "小明拆台MingStrike", 
            "url": "https://mingstrike.com/feed/audio.xml", 
            "enabled": True, 
            "category": "新聞",
        },
    ],

    "hongkong": [
        {
            "name": "KKBOX-香港", 
            "url": "https://www.kkbox.com/hk/tc/rss/news.xml", 
            "enabled": True, 
            "category": "新聞",
        },
    ],

    "international": [
        {
            "name": "Pitchfork", 
            "url": "https://pitchfork.com/rss/news", 
            "enabled": True, 
            "category": "國際",
        },
        {
            "name": "Rolling Stone", 
            "url": "https://www.rollingstone.com/music/feed/", 
            "enabled": True, 
            "category": "國際",
        },
        {
            "name": "NME", 
            "url": "https://www.nme.com/news/music/feed", 
            "enabled": True, 
            "category": "國際",
        },
        {
            "name": "Kerrang", 
            "url": "https://www.kerrang.com/feed", 
            "enabled": True, 
            "category": "國際",
        },
        {
            "name": "Louder Sound", 
            "url": "https://www.loudersound.com/feeds/all", 
            "enabled": True, 
            "category": "國際",
        },
        {
            "name": "Ultimate Classic Rock", 
            "url": "https://ultimateclassicrock.com/feed/", 
            "enabled": True, 
            "category": "國際",
        },
    ],

    "test": [
        {
            "name": "Blow吹音樂", 
            "url": "https://blow.streetvoice.com/feed/", 
            "enabled": True, 
            "category": "新聞",
        },
    ]
}

class NewsFetcher:
    def __init__(self, source_type="china", limit=5):
        self.notion = Client(auth=NOTION_TOKEN)
        self.source_type = source_type
        self.limit = limit
        self.stats = {
            "total": 0, "added": 0, "skipped": 0, "exists": 0, 
            "failed": 0, "image_uploaded": 0, "filtered": 0
        }
        self.articles = []
        self.cloudinary_enabled = all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ])

    def fetch_all(self):
        print("\n" + "="*70)
        print("ChineseRocks 新闻抓取系统 v8.8.8 - 中國源更新版")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"模式: {self.source_type}")
        print(f"每源限制: {self.limit} 条")
        print(f"Cloudinary: {'已啟用' if self.cloudinary_enabled else '未啟用'}")
        print("="*70)

        sources = SOURCES.get(self.source_type, [])
        enabled_sources = [s for s in sources if s["enabled"]]
        print(f"\n抓取 {len(enabled_sources)} 個搖滾音樂源")
        print("-"*50)

        for source in sources:
            if source["enabled"]:
                self._fetch_source(source)
            else:
                print(f"[{source['name']}] 已禁用")

        print(f"\n抓取完成: 共 {len(self.articles)} 条 (過濾 {self.stats['filtered']} 條)")
        return self.articles

    def _fetch_source(self, source):
        try:
            print(f"[{source['name']}]")
            feed = feedparser.parse(source['url'])

            if not feed.entries:
                print(f"  ⚠️ 無法獲取 RSS 內容或源無效")
                return

            count = 0
            filtered_count = 0

            for entry in feed.entries:
                if count >= self.limit:
                    break

                genres = self._detect_genres(entry)
                if not genres:
                    filtered_count += 1
                    continue

                article = self._parse_entry(entry, source, genres)
                if article:
                    self.articles.append(article)
                    count += 1

            print(f"  ✅ 成功獲取 {count} 条 (過濾 {filtered_count} 條)")
            self.stats["filtered"] += filtered_count

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            self.stats["failed"] += 1

    def _detect_genres(self, entry):
        """嚴格檢測文章音樂風格"""
        title = entry.get('title', '').lower()
        summary = entry.get('summary', entry.get('description', '')).lower()
        text = f"{title} {summary}"

        for exclude in EXCLUDE_GENRES:
            if exclude in text:
                return []

        matched_genres = []
        for genre_name, genre_info in MUSIC_GENRES.items():
            for keyword in genre_info["keywords"]:
                if keyword.lower() in text:
                    matched_genres.append((genre_name, genre_info["weight"]))
                    break

        matched_genres.sort(key=lambda x: x[1], reverse=True)
        return [g[0] for g in matched_genres[:3]]

    def _parse_entry(self, entry, source, genres):
        try:
            summary = entry.get('summary', entry.get('description', ''))
            summary = self._clean_html(summary)

            published = self._parse_date(entry)
            image = self._extract_image_improved(entry, source)

            if image and self.cloudinary_enabled:
                print(f"    📤 上傳圖片...")
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
                "genres": genres
            }
        except Exception as e:
            print(f"    解析條目失敗: {e}")
            return None

    def _extract_image_improved(self, entry, source):
        """優化圖片提取邏輯，支持更多格式"""
        try:
            # 1. 檢查 media_content (RSS 2.0 media 模組)
            if 'media_content' in entry:
                for media in entry.media_content:
                    if media.get('type', '').startswith('image/'):
                        return media.get('url', '')
                    if media.get('url'):
                        return media['url']

            # 2. 檢查 media_thumbnail
            if 'media_thumbnail' in entry and entry.media_thumbnail:
                return entry.media_thumbnail[0].get('url', '')

            # 3. 檢查 enclosures
            if 'enclosures' in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('image/'):
                        return enc.get('href', '')

            # 4. 從 content 中提取圖片
            content = entry.get('content', [{}])[0].get('value', '') if 'content' in entry else                      entry.get('summary', entry.get('description', ''))

            if content:
                soup = BeautifulSoup(content, 'html.parser')
                img = soup.find('img')
                if img:
                    img_url = img.get('src', '')
                    # 處理相對路徑
                    if img_url and img_url.startswith('/'):
                        link = entry.get('link', '')
                        if link:
                            from urllib.parse import urljoin
                            img_url = urljoin(link, img_url)
                    return img_url

            # 5. 針對特定源的特殊處理
            source_name = source.get('name', '').lower()
            if 'blow' in source_name:
                if 'description' in entry:
                    soup = BeautifulSoup(entry.description, 'html.parser')
                    img = soup.find('img')
                    if img and img.get('src'):
                        return img['src']

            # 深晨 DOPM 特殊處理
            if 'dopm' in source_name or '深晨' in source_name:
                # 深晨使用 Squarespace，圖片可能在 description 中
                if 'description' in entry:
                    soup = BeautifulSoup(entry.description, 'html.parser')
                    img = soup.find('img')
                    if img and img.get('src'):
                        return img['src']

            # 6. 檢查 feed 級別的圖片 (某些 RSS 在 channel 層級)
            if hasattr(entry, 'source'):
                feed_data = entry.get('source', {})
                if hasattr(feed_data, 'image') and feed_data.image:
                    return feed_data.image.get('url', '')

        except Exception as e:
            print(f"    圖片提取失敗: {e}")

        return ''

    def _upload_to_cloudinary(self, image_url, source_name):
        try:
            image_url = image_url.strip()
            if not image_url.startswith(('http://', 'https://')):
                return None

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
            print(f"    ⚠️ 上傳失敗: {e}")
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

            tags = [{"name": "新聞"}, {"name": article['source_name']}]

            for genre in article.get('genres', []):
                if genre != "ROCK 通用":
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
            error_msg = str(e)
            if "token" in error_msg.lower() or "unauthorized" in error_msg.lower():
                print(f"    🔴 Notion API Token 無效，請檢查 Secrets 設置")
            else:
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
        print(f"過濾非搖滾: {self.stats['filtered']} 条")
        print("="*70)

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
                       choices=['china', 'taiwan', 'hongkong', 'international', 'test'])
    parser.add_argument('--limit', type=int, default=5, help='每源抓取數量')
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("🔴 錯誤: NOTION_TOKEN 未設置")
        print("請在 GitHub Secrets 中設置 NOTION_TOKEN")
        sys.exit(1)

    fetcher = NewsFetcher(source_type=args.source, limit=args.limit)
    fetcher.fetch_all()

    if fetcher.articles:
        fetcher.sync_to_notion()

    fetcher.print_report()

if __name__ == "__main__":
    main()
