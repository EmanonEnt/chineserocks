// news-loader-v2.js - ChineseRocks 新闻加载器
// 功能：从 data/news.json 加载新闻，支持优先标签排序

(function() {
    'use strict';

    // 优先标签配置 - 这些标签会优先显示并有特殊样式
    const PRIORITY_TAGS = [
        'TheNoname', '無名', '無名樂隊', 'THE NONAME',
        'PUNK', 'Punk', 'punk', 'PUNK & HARDCORE',
        '龐克', '庞克', '硬核', 'Hardcore'
    ];

    // 优先标签样式类名
    const PRIORITY_CLASS = 'priority-tag';

    // 新闻数据缓存
    let newsData = [];
    let currentFilter = 'all';
    let currentTag = null;

    // 初始化
    document.addEventListener('DOMContentLoaded', init);

    function init() {
        loadNewsData();
        initTagCloud();
    }

    // 从 data/news.json 加载新闻数据
    async function loadNewsData() {
        try {
            const response = await fetch('data/news.json?t=' + Date.now());
            if (!response.ok) throw new Error('Failed to load news');

            newsData = await response.json();
            console.log('[NewsLoader] Loaded', newsData.length, 'articles');

            // 处理并渲染新闻
            processAndRenderNews();
        } catch (error) {
            console.error('[NewsLoader] Error:', error);
            // 如果加载失败，保持页面原有静态内容
        }
    }

    // 处理新闻数据 - 排序和分类
    function processAndRenderNews() {
        // 1. 按优先级排序（有优先标签的文章排在前面）
        const sortedNews = sortByPriority(newsData);

        // 2. 分离头条和普通新闻
        const heroNews = sortedNews.filter(n => n.isHero || n.isHeadline).slice(0, 3);
        const normalNews = sortedNews.filter(n => !n.isHero && !n.isHeadline);

        // 3. 渲染头条区
        if (heroNews.length > 0) {
            renderHeroSection(heroNews);
        }

        // 4. 渲染新闻列表
        renderNewsList(normalNews);

        // 5. 生成热门标签
        generateHotTags(sortedNews);
    }

    // 按优先级排序
    function sortByPriority(articles) {
        return articles.sort((a, b) => {
            const aPriority = hasPriorityTag(a) ? 1 : 0;
            const bPriority = hasPriorityTag(b) ? 1 : 0;

            if (aPriority !== bPriority) {
                return bPriority - aPriority; // 优先标签排前面
            }

            // 同优先级按日期排序（新的在前）
            return new Date(b.date || 0) - new Date(a.date || 0);
        });
    }

    // 检查文章是否包含优先标签
    function hasPriorityTag(article) {
        const text = (article.title + ' ' + (article.tags || []).join(' ')).toLowerCase();
        return PRIORITY_TAGS.some(tag => text.includes(tag.toLowerCase()));
    }

    // 获取文章的优先标签
    function getPriorityTags(article) {
        const tags = article.tags || [];
        return tags.filter(tag => 
            PRIORITY_TAGS.some(pt => tag.toLowerCase().includes(pt.toLowerCase()))
        );
    }

    // 渲染头条区
    function renderHeroSection(heroNews) {
        const heroMain = document.querySelector('.hero-main');
        const heroSide = document.querySelector('.hero-side');

        if (!heroMain || !heroSide) return;

        // 主头条
        if (heroNews[0]) {
            const main = heroNews[0];
            const isPriority = hasPriorityTag(main);
            heroMain.innerHTML = `
                <img src="${main.image || main.cover}" alt="${main.title}">
                <div class="hero-overlay">
                    <span class="hero-tag ${main.category || 'exclusive'} ${isPriority ? PRIORITY_CLASS : ''}">
                        ${main.tag || main.categoryName || '獨家'}
                    </span>
                    <h2 class="hero-title">${main.title}</h2>
                    <p class="hero-excerpt">${main.excerpt || main.summary || ''}</p>
                    <div class="hero-meta">
                        <span>${formatDate(main.date)}</span>
                        <span>閱讀時間 ${main.readTime || '5'} 分鐘</span>
                        ${main.isPremium ? '<span>★ 會員專享</span>' : ''}
                    </div>
                </div>
            `;
            heroMain.onclick = () => handleArticleClick(main);
        }

        // 侧边头条
        heroSide.innerHTML = heroNews.slice(1, 3).map(news => {
            const isPriority = hasPriorityTag(news);
            return `
                <article class="side-card" data-id="${news.id}">
                    <img src="${news.image || news.cover}" alt="${news.title}">
                    <div class="side-overlay">
                        <span class="side-tag ${isPriority ? PRIORITY_CLASS : ''}">${news.tag || news.categoryName || '新聞'}</span>
                        <h3 class="side-title">${news.title}</h3>
                    </div>
                </article>
            `;
        }).join('');

        // 绑定点击事件
        heroSide.querySelectorAll('.side-card').forEach((card, idx) => {
            card.onclick = () => handleArticleClick(heroNews[idx + 1]);
        });
    }

    // 渲染新闻列表
    function renderNewsList(news) {
        const newsList = document.getElementById('newsList');
        if (!newsList) return;

        // 保留加载更多按钮
        const loadMore = newsList.querySelector('.load-more');

        // 清除现有新闻卡片（保留加载更多）
        const existingCards = newsList.querySelectorAll('.news-card');
        existingCards.forEach(card => card.remove());

        // 渲染新卡片
        news.forEach(item => {
            const card = createNewsCard(item);
            newsList.insertBefore(card, loadMore);
        });

        // 应用当前筛选
        applyFilter();
    }

    // 创建新闻卡片
    function createNewsCard(news) {
        const isPremium = news.isPremium || news.memberOnly;
        const isPriority = hasPriorityTag(news);
        const priorityTags = getPriorityTags(news);

        const card = document.createElement('article');
        card.className = `news-card ${isPremium ? 'premium' : ''}`;
        card.dataset.category = news.category || 'feature';
        card.dataset.id = news.id;

        if (priorityTags.length > 0) {
            card.dataset.priorityTag = priorityTags[0];
        }

        card.innerHTML = `
            <div class="news-thumb">
                <img src="${news.image || news.cover}" alt="${news.title}" loading="lazy">
            </div>
            <div class="news-content">
                <span class="news-category ${isPriority ? PRIORITY_CLASS : ''}">
                    ${news.categoryName || news.category || '新聞'}
                    ${isPriority ? ' ★' : ''}
                </span>
                <h3 class="news-title">${news.title}</h3>
                <p class="news-excerpt">${news.excerpt || news.summary || ''}</p>
                <div class="news-footer">
                    <div class="news-meta">
                        <span>${formatDate(news.date)}</span>
                        <span>閱讀 ${news.readTime || '5'} 分鐘</span>
                        ${isPremium ? '<span style="color: #B8860B; font-weight: 700;">★ 會員專享</span>' : ''}
                    </div>
                    <div class="news-actions">
                        <button class="action-btn" onclick="event.stopPropagation(); toggleFav(this, '${news.title.replace(/'/g, "\'")}')">☆</button>
                        <button class="action-btn" onclick="event.stopPropagation(); shareArticle('${news.title.replace(/'/g, "\'")}')">↗</button>
                    </div>
                </div>
            </div>
        `;

        card.onclick = () => handleArticleClick(news);
        return card;
    }

    // 生成热门标签
    function generateHotTags(articles) {
        const tagCloud = document.getElementById('tagCloud');
        if (!tagCloud) return;

        // 统计标签出现频率
        const tagCount = {};
        articles.forEach(article => {
            const tags = article.tags || [];
            tags.forEach(tag => {
                tagCount[tag] = (tagCount[tag] || 0) + 1;
            });
        });

        // 按频率排序，取前12个
        const hotTags = Object.entries(tagCount)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 12)
            .map(([tag]) => tag);

        // 合并优先标签（确保它们显示在前面）
        const priorityDisplayTags = ['TheNoname無名', '龐克', '迷笛音樂節'];
        const finalTags = [...new Set([...priorityDisplayTags, ...hotTags])].slice(0, 12);

        // 渲染标签
        tagCloud.innerHTML = finalTags.map(tag => {
            const isPriority = PRIORITY_TAGS.some(pt => 
                tag.toLowerCase().includes(pt.toLowerCase())
            );
            return `<button class="tag-item ${isPriority ? PRIORITY_CLASS : ''}" onclick="filterByTag('${tag}', this)">#${tag}</button>`;
        }).join('');
    }

    // 初始化标签云点击事件
    function initTagCloud() {
        // 标签筛选功能已由全局函数处理
    }

    // 应用当前筛选
    function applyFilter() {
        const newsCards = document.querySelectorAll('.news-card');

        newsCards.forEach(card => {
            let shouldShow = true;

            // 分类筛选
            if (currentFilter !== 'all' && card.dataset.category !== currentFilter) {
                shouldShow = false;
            }

            // 标签筛选
            if (currentTag && !card.dataset.priorityTag?.includes(currentTag)) {
                shouldShow = false;
            }

            card.style.display = shouldShow ? 'flex' : 'none';
        });
    }

    // 处理文章点击
    function handleArticleClick(article) {
        // 调用页面原有的处理函数
        if (window.handleArticleClick) {
            const tempElement = document.createElement('div');
            tempElement.className = article.isPremium ? 'news-card premium' : 'news-card';
            window.handleArticleClick(tempElement, article.title);
        }

        // 实际跳转
        window.location.href = `article.html?id=${article.id}&title=${encodeURIComponent(article.title)}`;
    }

    // 格式化日期
    function formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
    }

    // 暴露全局方法供页面调用
    window.NewsLoader = {
        refresh: loadNewsData,
        filterByCategory: function(category) {
            currentFilter = category;
            applyFilter();
        },
        filterByTag: function(tag) {
            currentTag = tag;
            applyFilter();
        }
    };

})();
