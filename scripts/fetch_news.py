#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChineseRocks 新闻抓取脚本 v13 - RSS源排查修复版
- 修复：移除不可用的独立音乐资讯和街声中国源
- 修复：Notion API query方法改为databases.query
- 新增：Unite Asia (亚洲朋克/硬核/金属专业媒体)
"""

import os
import sys
import json
import hashlib
import re
import argparse
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from difflib import SequenceMatcher
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

DAYS_LIMIT = 30
SIMILARITY_THRESHOLD = 0.88
INTER_SOURCE_THRESHOLD = 0.75
MIN_CONTENT_LENGTH = 50

# 嚴格搖滾風格分類
MUSIC_GENRES = {
    "PUNK & HARDCORE": {
        "keywords": ["punk", "朋克", "hardcore", "硬核", "emo", "screamo", "post-hardcore", "oi", "crust", "street punk"],
        "weight": 10
    },
    "HEAVY & METAL": {
        "keywords": ["metal", "金屬", "heavy", "thrash", "death metal", "black metal", "doom", "sludge", "stoner", "grindcore", "nu metal"],
        "weight": 10
    },
    "INDIE & ALTERNATIVE": {
        "keywords": ["indie", "獨立", "alternative", "另類", "lo-fi", "shoegaze", "dream pop", "britpop", "grunge", "indie rock"],
        "weight": 9
    },
    "SKA & REGGAE": {
        "keywords": ["ska", "reggae", "雷鬼", "dub", "rocksteady", "ska-punk", "two-tone"],
        "weight": 8
    },
    "GARAGE & PSYCHEDELIC": {
        "keywords": ["garage", "車庫", "psychedelic", "迷幻", "space rock", "krautrock", "acid rock"],
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
        "keywords": ["rock", "搖滾", "band", "樂隊", "guitar", "吉他", "bass", "drum", "live", "演出", "concert", "tour"],
        "weight": 5
    }
}

# 嚴格排除所有非搖滾音樂
EXCLUDE_GENRES = [
    "k-pop", "j-pop", "c-pop", "mandopop", "cantopop", 
    "pop music", "teen pop", "synth-pop", "electropop", "bubblegum pop",
    "hip-hop", "rap", "trap", "drill", "r&b", "soul", "funk", "disco", "neo-soul",
    "edm", "electronic", "house", "techno", "trance", "dubstep", 
    "drum and bass", "dnb", "ambient", "idm", "glitch", "synthwave",
    "classical", "opera", "jazz", "new age", "world music", "new wave",
    "acoustic pop", "folk pop", "indie pop"
]

# v13 RSS 源配置 - 已排查可用性
SOURCES = {
    "china": [
        {
            "name": "Live China Music", 
            "url": "https://livechinamusic.com/feed", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 10
        },
        {
            "name": "Wooozy-地下音樂", 
            "url": "https://wooozy.cn/feed", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 9
        },
        {
            "name": "独立音樂資訊", 
            "url": "https://www.indie-music.com/feed", 
            "enabled": False,
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：网站无法访问"
        },
        {
            "name": "街聲-中國", 
            "url": "https://streetvoice.cn/feed/", 
            "enabled": False,
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：RSS返回HTML页面而非XML"
        },
        {
            "name": "網易雲-原創音樂", 
            "url": "https://rsshub.app/ncm/playlist/2884035", 
            "enabled": False,
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：RSSHub公共实例不稳定"
        },
        {
            "name": "知乎-搖滾樂話題", 
            "url": "https://rsshub.app/zhihu/topic/19550718", 
            "enabled": False,
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：RSSHub限制20条"
        },
        {
            "name": "知乎-獨立音樂話題", 
            "url": "https://rsshub.app/zhihu/topic/19550408", 
            "enabled": False,
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：RSSHub限制20条"
        },
        {
            "name": "豆瓣音樂-樂評", 
            "url": "https://rsshub.app/douban/music/latest", 
            "enabled": False, 
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：RSSHub公共实例反爬严重"
        },
        {
            "name": "摩登天空-網易號", 
            "url": "https://rsshub.app/163/dy/T1509089140270", 
            "enabled": False, 
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：网易号反爬机制"
        },
        {
            "name": "Solidot-文化", 
            "url": "https://rsshub.app/solidot/culture", 
            "enabled": False,
            "category": "新聞",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：摇滚相关内容极少"
        },
    ],

    "taiwan": [
        {
            "name": "深晨DOPM", 
            "url": "https://deepperfectmorning.com/blog?format=rss", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 10
        },
        {
            "name": "Blow吹音樂-人物", 
            "url": "https://blow.streetvoice.com/c/people/feed/", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 9
        },
        {
            "name": "Blow吹音樂-議題", 
            "url": "https://blow.streetvoice.com/c/issue/feed/", 
            "enabled": True, 
            "category": "新聞",
            "priority": 2,
            "quality_score": 8
        },
        {
            "name": "小明拆台MingStrike", 
            "url": "https://mingstrike.com/feed/audio.xml", 
            "enabled": True, 
            "category": "新聞",
            "priority": 3,
            "quality_score": 7
        },
    ],

    "hongkong": [
        {
            "name": "HKFP-文化", 
            "url": "https://hongkongfp.com/culture/feed/", 
            "enabled": True, 
            "category": "新聞",
            "priority": 2,
            "quality_score": 6
        },
    ],

    "international": [
        {
            "name": "Unite Asia", 
            "url": "https://uniteasia.org/feed", 
            "enabled": True, 
            "category": "國際",
            "priority": 1,
            "quality_score": 10,
            "inter_source_key": True,
            "description": "亚洲朋克、硬核、金属音乐专业媒体"
        },
        {
            "name": "Pitchfork", 
            "url": "https://pitchfork.com/rss/news", 
            "enabled": True, 
            "category": "國際",
            "priority": 1,
            "quality_score": 10,
            "inter_source_key": True
        },
        {
            "name": "Rolling Stone", 
            "url": "https://www.rollingstone.com/music/feed/", 
            "enabled": True, 
            "category": "國際",
            "priority": 1,
            "quality_score": 9,
            "inter_source_key": True
        },
        {
            "name": "NME", 
            "url": "https://www.nme.com/news/music/feed", 
            "enabled": True, 
            "category": "國際",
            "priority": 3,
            "quality_score": 6,
            "limit_override": 1
        },
        {
            "name": "Kerrang", 
            "url": "https://www.kerrang.com/feed", 
            "enabled": True, 
            "category": "國際",
            "priority": 3,
            "quality_score": 7,
            "limit_override": 1
        },
        {
            "name": "Stereogum", 
            "url": "https://www.stereogum.com/feed", 
            "enabled": False, 
            "category": "國際",
            "priority": 99,
            "quality_score": 0,
            "reason": "v13禁用：与Pitchfork/NME重复率过高"
        },
    ],

    "test": [
        {
            "name": "深晨DOPM-測試", 
            "url": "https://deepperfectmorning.com/blog?format=rss", 
            "enabled": True, 
            "category": "新聞",
            "priority": 1,
            "quality_score": 10
        },
    ]
}


class ContentDeduplicator:
    def __init__(self, threshold=SIMILARITY_THRESHOLD):
        self.threshold = threshold
        self.inter_source_threshold = INTER_SOURCE_THRESHOLD
        self.seen_contents = []
        self.seen_urls = set()
        self.existing_titles = set()

    def normalize_url(self, url):
        if not url:
            return ""
        url = re.sub(r'[?&](utm_source|utm_medium|utm_campaign|utm_content|fbclid|gclid)=[^&]*', '', url)
        url = url.rstrip('?')
        url = url.replace('http://', 'https://')
        url = url.replace('https://www.', 'https://')
        return url.lower().strip()

    def create_fingerprint(self, title, summary):
        text = f"{title} {summary}".lower()
        chinese_words = re.findall(r'[一-龥]{2,6}', text)
        english_words = re.findall(r'\b[a-z]{4,}\b', text)
        keywords = list(dict.fromkeys(chinese_words + english_words))
        return ' '.join(keywords[:30])

    def extract_event_key(self, title):
        noise_words = ['announces', 'releases', 'new', 'album', 'single', 'video', 
                       'tour', 'live', 'death', 'dies', 'interview', 'review',
                       '宣布', '发布', '新专辑', '单曲', 'MV', '巡演', '去世', '专访']
        text = title.lower()
        for word in noise_words:
            text = text.replace(word, '')
        names = re.findall(r'\b[A-Z][a-zA-Z]+\b|[一-龥]{2,4}', text)
        return ' '.join(sorted(set(names)))[:50]

    def calculate_similarity(self, text1, text2):
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()

    def is_duplicate(self, title, summary, url, source_type=""):
        normalized_url = self.normalize_url(url)
        if normalized_url and normalized_url in self.seen_urls:
            return True, "URL重复"

        clean_title = re.sub(r'[^\w一-龥]', '', title.lower())
        if clean_title in self.existing_titles:
            return True, "Notion中已存在"

        fingerprint = self.create_fingerprint(title, summary)
        event_key = self.extract_event_key(title)

        for seen_fp, seen_title, seen_event in self.seen_contents:
            if title.lower().strip() == seen_title.lower().strip():
                return True, "标题完全匹配"

            similarity = self.calculate_similarity(fingerprint, seen_fp)
            if similarity >= self.threshold:
                return True, f"内容相似度{similarity:.0%}"

            if source_type == "international" and event_key and seen_event:
                event_sim = self.calculate_similarity(event_key, seen_event)
                if event_sim >= self.inter_source_threshold and len(event_key) > 10:
                    return True, f"国际源事件重复{event_sim:.0%}"

        return False, None

    def add_content(self, title, summary, url, source_type=""):
        fingerprint = self.create_fingerprint(title, summary)
        event_key = self.extract_event_key(title)
        self.seen_contents.append((fingerprint, title, event_key))
        normalized_url = self.normalize_url(url)
        if normalized_url:
            self.seen_urls.add(normalized_url)

    def load_existing_from_notion(self, notion_client, db_id, days=14):
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            # 修复：使用正确的Notion API调用方式
            response = notion_client.databases.query(
                database_id=db_id,
                filter={
                    "property": "發布時間",
                    "date": {"after": cutoff}
                }
            )

            for page in response.get('results', []):
                try:
                    title_prop = page['properties'].get('標題', {})
                    if title_prop and 'title' in title_prop and title_prop['title']:
                        title = title_prop['title'][0]['text']['content']
                        clean_title = re.sub(r'[^\w一-龥]', '', title.lower())
                        self.existing_titles.add(clean_title)
                except:
                    continue

            print(f"  📚 从Notion加载了 {len(self.existing_titles)} 条已有标题(近{days}天)")
            return len(self.existing_titles)
        except Exception as e:
            print(f"  ⚠️ 加载Notion已有标题失败: {e}")
            return 0


class NewsFetcher:
    def __init__(self, source_type="china", limit=5):
        self.notion = Client(auth=NOTION_TOKEN)
        self.source_type = source_type
        self.limit = limit
        self.stats = {
            "total": 0, "added": 0, "skipped": 0, "exists": 0, 
            "failed": 0, "image_uploaded": 0, "filtered": 0,
            "too_old": 0, "duplicate_content": 0, "low_quality": 0,
            "notion_duplicate": 0, "inter_source_dup": 0
        }
        self.articles = []
        self.cloudinary_enabled = all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ])
        self.cutoff_date = datetime.now() - timedelta(days=DAYS_LIMIT)
        self.deduplicator = ContentDeduplicator()

    def fetch_all(self):
        print("\n" + "="*70)
        print("ChineseRocks 新闻抓取系统 v13 - RSS源排查修复版")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"模式: {self.source_type}")
        print(f"每源限制: {self.limit} 条")
        print(f"日期限制: 近{DAYS_LIMIT}天內 (截止: {self.cutoff_date.strftime('%Y-%m-%d')})")
        print(f"相似度阈值: {SIMILARITY_THRESHOLD:.0%} (源内) / {INTER_SOURCE_THRESHOLD:.0%} (国际源间)")
        print(f"Cloudinary: {'已啟用' if self.cloudinary_enabled else '未啟用'}")
        print("="*70)

        if NOTION_TOKEN:
            self.deduplicator.load_existing_from_notion(self.notion, NEWS_DB_ID, days=14)

        sources = SOURCES.get(self.source_type, [])
        enabled_sources = [s for s in sources if s["enabled"]]
        enabled_sources.sort(key=lambda x: x.get("priority", 99))

        print(f"\n抓取 {len(enabled_sources)} 个源 (已按优先级排序)")
        print("-"*50)

        for source in sources:
            if not source["enabled"]:
                reason = source.get("reason", "已禁用")
                print(f"[{source['name']}] ⚠️ {reason}")
                continue
            self._fetch_source(source)

        print(f"\n抓取完成: 共 {len(self.articles)} 条")
        print(f"  - 内容去重过滤: {self.stats['duplicate_content']} 条")
        print(f"  - 国际源间去重: {self.stats['inter_source_dup']} 条")
        print(f"  - Notion已存在: {self.stats['notion_duplicate']} 条")
        print(f"  - 低质量过滤: {self.stats['low_quality']} 条")
        print(f"  - 非搖滾过滤: {self.stats['filtered']} 条")
        print(f"  - 過期文章(>{DAYS_LIMIT}天): {self.stats['too_old']} 条")
        return self.articles

    def _fetch_source(self, source):
        try:
            priority = source.get("priority", 3)
            quality = source.get("quality_score", 5)
            limit = source.get("limit_override", self.limit)
            desc = source.get("description", "")

            print(f"[{source['name']}] (优先级:{priority}, 质量分:{quality}, 限制:{limit})")
            if desc:
                print(f"  ℹ️ {desc}")

            retries = 3
            feed = None
            for i in range(retries):
                try:
                    feed = feedparser.parse(source['url'])
                    if feed.entries:
                        break
                except Exception as e:
                    if i < retries - 1:
                        print(f"  🔄 重试 {i+1}/{retries}...")
                        import time
                        time.sleep(2)
                    else:
                        raise

            if not feed or not feed.entries:
                print(f"  ⚠️ 無法獲取 RSS 內容或源無效")
                return

            count = 0
            filtered_count = 0
            too_old_count = 0
            duplicate_count = 0
            inter_dup_count = 0
            notion_dup_count = 0
            low_quality_count = 0

            for entry in feed.entries:
                if count >= limit:
                    break

                published_date = self._parse_date(entry)
                if published_date:
                    try:
                        pub_dt = datetime.strptime(published_date, "%Y-%m-%d")
                        if pub_dt < self.cutoff_date:
                            too_old_count += 1
                            continue
                    except:
                        pass

                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                summary = self._clean_html(summary)

                if len(summary) < MIN_CONTENT_LENGTH:
                    low_quality_count += 1
                    continue

                link = entry.get('link', '')
                is_dup, dup_reason = self.deduplicator.is_duplicate(
                    title, summary, link, 
                    source_type=self.source_type
                )
                if is_dup:
                    if "Notion中已存在" in dup_reason:
                        notion_dup_count += 1
                    elif "国际源" in dup_reason:
                        inter_dup_count += 1
                    else:
                        duplicate_count += 1
                    print(f"    🔄 跳过: {dup_reason} - {title[:30]}...")
                    continue

                genres = self._detect_genres(entry)
                if not genres:
                    filtered_count += 1
                    continue

                article = self._parse_entry(entry, source, genres)
                if article:
                    self.deduplicator.add_content(
                        article['title'], 
                        article['summary'], 
                        article['link'],
                        source_type=self.source_type
                    )
                    self.articles.append(article)
                    count += 1

            print(f"  ✅ 成功 {count} 条 (去重{duplicate_count}, 源间去重{inter_dup_count}, Noton已存在{notion_dup_count}, 低质量{low_quality_count}, 风格过滤{filtered_count}, 过期{too_old_count})")
            self.stats["duplicate_content"] += duplicate_count
            self.stats["inter_source_dup"] += inter_dup_count
            self.stats["notion_duplicate"] += notion_dup_count
            self.stats["low_quality"] += low_quality_count
            self.stats["filtered"] += filtered_count
            self.stats["too_old"] += too_old_count

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            self.stats["failed"] += 1

    def _detect_genres(self, entry):
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
        try:
            if 'media_content' in entry:
                for media in entry.media_content:
                    if media.get('type', '').startswith('image/'):
                        return media.get('url', '')
                    if media.get('url'):
                        return media['url']

            if 'media_thumbnail' in entry and entry.media_thumbnail:
                return entry.media_thumbnail[0].get('url', '')

            if 'enclosures' in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('image/'):
                        return enc.get('href', '')

            content = entry.get('content', [{}])[0].get('value', '') if 'content' in entry else entry.get('summary', entry.get('description', ''))

            if content:
                soup = BeautifulSoup(content, 'html.parser')
                img = soup.find('img')
                if img:
                    img_url = img.get('src', '')
                    if img_url and img_url.startswith('/'):
                        link = entry.get('link', '')
                        if link:
                            from urllib.parse import urljoin
                            img_url = urljoin(link, img_url)
                    return img_url

            source_name = source.get('name', '').lower()
            if 'blow' in source_name or 'dopm' in source_name or '深晨' in source_name:
                if 'description' in entry:
                    soup = BeautifulSoup(entry.description, 'html.parser')
                    img = soup.find('img')
                    if img and img.get('src'):
                        return img['src']

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
        print("-"*70)
        print(f"过滤统计:")
        print(f"  - 内容去重: {self.stats['duplicate_content']} 条")
        print(f"  - 国际源间去重: {self.stats['inter_source_dup']} 条")
        print(f"  - Notion已存在: {self.stats['notion_duplicate']} 条")
        print(f"  - 低质量: {self.stats['low_quality']} 条")
        print(f"  - 非搖滾: {self.stats['filtered']} 条")
        print(f"  - 過期(>{DAYS_LIMIT}天): {self.stats['too_old']} 条")
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
