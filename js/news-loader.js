// news-loader-v3.js - ChineseRocks 新闻加载器
// 功能：从 data/news.json 加载新闻

(function() {
    'use strict';

    const PRIORITY_TAGS = [
        'TheNoname', '無名', '無名樂隊', 'THE NONAME',
        'PUNK', 'Punk', 'punk', 'PUNK & HARDCORE',
        '龐克', '庞克', '硬核', 'Hardcore'
    ];

    const PRIORITY_CLASS = 'priority-tag';
    let newsData = [];

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        console.log('[NewsLoader] 初始化...');
        loadNewsData();
    }

    async function loadNewsData() {
        try {
            const response = await fetch('data/news.json?t=' + Date.now());
            if (!response.ok) {
                throw new Error('Failed to load news: ' + response.status);
            }

            const jsonData = await response.json();
            console.log('[NewsLoader] 加载的原始数据:', jsonData);

            // 支持两种格式：直接数组或包含 data 字段的对象
            if (jsonData.data) {
                newsData = jsonData.data.all || jsonData.data.latest || [];
            } else if (Array.isArray(jsonData)) {
                newsData = jsonData;
            } else {
                newsData = jsonData.all || jsonData.latest || [];
            }

            console.log('[NewsLoader] 解析到', newsData.length, '篇文章');

            if (newsData.length > 0) {
                processAndRenderNews();
            } else {
                console.warn('[NewsLoader] 没有新闻数据');
            }
        } catch (error) {
            console.error('[NewsLoader] 错误:', error);
        }
    }

    function processAndRenderNews() {
        // 按优先级排序
        const sortedNews = sortByPriority(newsData);

        // 分离头条和普通新闻
        const heroNews = sortedNews.filter(n => n.featured || n.isHero).slice(0, 3);
        const normalNews = sortedNews.filter(n => !n.featured && !n.isHero);

        // 渲染
        if (heroNews.length > 0) {
            renderHeroSection(heroNews);
        }
        renderNewsList(normalNews);
        generateHotTags(sortedNews);
    }

    function sortByPriority(articles) {
        return articles.sort((a, b) => {
            const aPriority = hasPriorityTag(a) ? 1 : 0;
            const bPriority = hasPriorityTag(b) ? 1 : 0;
            if (aPriority !== bPriority) {
                return bPriority - aPriority;
            }
            return new Date(b.published_date || b.created_time || 0) - new Date(a.published_date || a.created_time || 0);
        });
    }

    function hasPriorityTag(article) {
        const text = (article.title + ' ' + (article.tags || []).join(' ')).toLowerCase();
        return PRIORITY_TAGS.some(tag => text.includes(tag.toLowerCase()));
    }

    function renderHeroSection(heroNews) {
        const heroMain = document.querySelector('.hero-main');
        const heroSide = document.querySelector('.hero-side');

        if (!heroMain || !heroSide) return;

        // 主头条
        if (heroNews[0]) {
            const main = heroNews[0];
            heroMain.innerHTML = `
                <img src="${main.cover_image || main.cover}" alt="${main.title}">
                <div class="hero-overlay">
                    <span class="hero-tag ${main.category || 'exclusive'} ${hasPriorityTag(main) ? PRIORITY_CLASS : ''}">
                        ${main.tags && main.tags[0] ? main.tags[0] : '獨家'}
                    </span>
                    <h2 class="hero-title">${main.title}</h2>
                    <p class="hero-excerpt">${main.content ? main.content.substring(0, 100) + '...' : ''}</p>
                    <div class="hero-meta">
                        <span>${formatDate(main.published_date)}</span>
                        ${main.is_premium ? '<span>★ 會員專享</span>' : ''}
                    </div>
                </div>
            `;
            heroMain.onclick = () => handleArticleClick(main);
        }

        // 侧边头条
        heroSide.innerHTML = heroNews.slice(1, 3).map(news => `
            <article class="side-card" data-id="${news.id}">
                <img src="${news.cover_image || news.cover}" alt="${news.title}">
                <div class="side-overlay">
                    <span class="side-tag ${hasPriorityTag(news) ? PRIORITY_CLASS : ''}">${news.tags && news.tags[0] ? news.tags[0] : '新聞'}</span>
                    <h3 class="side-title">${news.title}</h3>
                </div>
            </article>
        `).join('');

        heroSide.querySelectorAll('.side-card').forEach((card, idx) => {
            card.onclick = () => handleArticleClick(heroNews[idx + 1]);
        });
    }

    function renderNewsList(news) {
        const newsList = document.getElementById('newsList');
        if (!newsList) return;

        const loadMore = newsList.querySelector('.load-more');
        newsList.querySelectorAll('.news-card').forEach(card => card.remove());

        news.forEach(item => {
            const card = createNewsCard(item);
            newsList.insertBefore(card, loadMore);
        });
    }

    function createNewsCard(news) {
        const isPremium = news.is_premium || news.memberOnly;
        const card = document.createElement('article');
        card.className = `news-card ${isPremium ? 'premium' : ''}`;
        card.dataset.id = news.id;

        card.innerHTML = `
            <div class="news-thumb">
                <img src="${news.cover_image || news.cover}" alt="${news.title}" loading="lazy">
            </div>
            <div class="news-content">
                <span class="news-category ${hasPriorityTag(news) ? PRIORITY_CLASS : ''}">
                    ${news.category || (news.tags && news.tags[0]) || '新聞'}
                    ${hasPriorityTag(news) ? ' ★' : ''}
                </span>
                <h3 class="news-title">${news.title}</h3>
                <p class="news-excerpt">${news.content ? news.content.substring(0, 80) + '...' : ''}</p>
                <div class="news-footer">
                    <div class="news-meta">
                        <span>${formatDate(news.published_date)}</span>
                        ${isPremium ? '<span style="color: #B8860B; font-weight: 700;">★ 會員專享</span>' : ''}
                    </div>
                </div>
            </div>
        `;

        card.onclick = () => handleArticleClick(news);
        return card;
    }

    function generateHotTags(articles) {
        const tagCloud = document.getElementById('tagCloud');
        if (!tagCloud) return;

        const tagCount = {};
        articles.forEach(article => {
            (article.tags || []).forEach(tag => {
                tagCount[tag] = (tagCount[tag] || 0) + 1;
            });
        });

        const hotTags = Object.entries(tagCount)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 12)
            .map(([tag]) => tag);

        const priorityDisplayTags = ['TheNoname無名', '龐克', '迷笛音樂節'];
        const finalTags = [...new Set([...priorityDisplayTags, ...hotTags])].slice(0, 12);

        tagCloud.innerHTML = finalTags.map(tag => {
            const isPriority = PRIORITY_TAGS.some(pt => tag.toLowerCase().includes(pt.toLowerCase()));
            return `<button class="tag-item ${isPriority ? PRIORITY_CLASS : ''}" onclick="filterByTag('${tag}')">#${tag}</button>`;
        }).join('');
    }

    function handleArticleClick(article) {
        window.location.href = `article.html?id=${article.id}&title=${encodeURIComponent(article.title)}`;
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
    }

    // 暴露全局方法
    window.NewsLoader = {
        refresh: loadNewsData
    };
})();
