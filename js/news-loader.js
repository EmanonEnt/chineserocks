// News Loader - 從 data/news.json 加載新聞
(function() {
    const NEWS_JSON_URL = 'data/news.json';

    // 加載新聞數據
    async function loadNews() {
        try {
            console.log('📰 開始加載新聞...');

            // 添加時間戳防止緩存
            const response = await fetch(`${NEWS_JSON_URL}?t=${Date.now()}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('✅ 新聞數據:', data);

            if (!data.news || data.news.length === 0) {
                console.log('⚠️ 沒有新聞數據');
                return;
            }

            renderNews(data.news);

        } catch (error) {
            console.error('❌ 加載新聞失敗:', error);
        }
    }

    // 渲染新聞到頁面
    function renderNews(newsList) {
        console.log(`📰 總共 ${newsList.length} 條新聞`);

        // 根據新聞數量決定布局
        if (newsList.length === 1) {
            // 只有1條：全寬大圖
            updateLayoutSingle();
            updateFeaturedNews(newsList[0], true);
            updateSideNews([]);
        } else if (newsList.length === 2) {
            // 只有2條：左大圖 + 右1個（調整為50/50布局）
            updateLayoutTwo();
            updateFeaturedNews(newsList[0], false);
            updateSideNews([newsList[1]]);
        } else {
            // 3條或以上：左大圖 + 右2個（標準布局）
            updateLayoutStandard();
            updateFeaturedNews(newsList[0], false);
            updateSideNews(newsList.slice(1, 3));
        }
    }

    // 單條新聞布局（全寬）
    function updateLayoutSingle() {
        const container = document.querySelector('.news-grid, .news-container');
        if (container) {
            container.style.gridTemplateColumns = '1fr';
            container.style.display = 'block';
        }
        const sideContainer = document.querySelector('.side-news, .news-sidebar');
        if (sideContainer) {
            sideContainer.style.display = 'none';
        }
    }

    // 兩條新聞布局（50/50）
    function updateLayoutTwo() {
        const container = document.querySelector('.news-grid, .news-container');
        if (container) {
            container.style.gridTemplateColumns = '1fr 1fr';
            container.style.gap = '20px';
        }

        // 調整大圖區域
        const featuredSection = document.querySelector('.featured-news, .news-main');
        if (featuredSection) {
            featuredSection.style.height = '400px';
        }

        // 調整側邊區域為單個大卡片
        const sideContainer = document.querySelector('.side-news, .news-sidebar');
        if (sideContainer) {
            sideContainer.style.display = 'flex';
            sideContainer.style.flexDirection = 'column';
            sideContainer.style.gap = '0';
        }
    }

    // 標準布局（大圖 + 2小圖）
    function updateLayoutStandard() {
        const container = document.querySelector('.news-grid, .news-container');
        if (container) {
            container.style.gridTemplateColumns = '2fr 1fr';
            container.style.gap = '20px';
        }

        const featuredSection = document.querySelector('.featured-news, .news-main');
        if (featuredSection) {
            featuredSection.style.height = '500px';
        }

        const sideContainer = document.querySelector('.side-news, .news-sidebar');
        if (sideContainer) {
            sideContainer.style.display = 'flex';
            sideContainer.style.flexDirection = 'column';
            sideContainer.style.gap = '15px';
        }
    }

    // 更新大圖新聞
    function updateFeaturedNews(news, isFullWidth) {
        const featuredImg = document.querySelector('.featured-news-img, .news-main-image');
        const featuredTitle = document.querySelector('.featured-news-title, .news-main-title');
        const featuredSummary = document.querySelector('.featured-news-summary, .news-main-summary');
        const featuredLink = document.querySelector('.featured-news-link');

        if (featuredImg) {
            featuredImg.src = news.image;
            featuredImg.alt = news.title;
            if (isFullWidth) {
                featuredImg.style.height = '500px';
                featuredImg.style.objectFit = 'cover';
            }
        }

        if (featuredTitle) {
            featuredTitle.textContent = news.title;
        }

        if (featuredSummary) {
            featuredSummary.textContent = news.summary || '';
            if (isFullWidth) {
                featuredSummary.style.maxWidth = '800px';
            }
        }

        if (featuredLink) {
            featuredLink.href = news.sourceUrl || '#';
        }

        const categoryTag = document.querySelector('.featured-news-category, .news-category');
        if (categoryTag && news.category) {
            categoryTag.textContent = news.category;
        }

        console.log('✅ 大圖新聞已更新:', news.title);
    }

    // 更新側邊新聞列表
    function updateSideNews(newsList) {
        const sideContainer = document.querySelector('.side-news, .news-sidebar');

        if (!sideContainer) {
            console.log('⚠️ 未找到側邊新聞容器');
            return;
        }

        // 清空現有內容
        sideContainer.innerHTML = '';

        if (newsList.length === 0) {
            sideContainer.style.display = 'none';
            return;
        }

        // 生成側邊新聞 HTML
        newsList.forEach((news, index) => {
            const newsItem = document.createElement('div');
            newsItem.className = 'side-news-item';

            // 如果只有1個側邊新聞，讓它更高
            const isSingle = newsList.length === 1;

            newsItem.innerHTML = `
                <a href="${news.sourceUrl || '#'}" class="side-news-link" style="
                    display: flex;
                    flex-direction: column;
                    text-decoration: none;
                    color: inherit;
                    height: ${isSingle ? '400px' : 'auto'};
                ">
                    <div class="side-news-image" style="
                        width: 100%;
                        height: ${isSingle ? '250px' : '120px'};
                        overflow: hidden;
                        border-radius: 8px;
                        margin-bottom: 10px;
                    ">
                        <img src="${news.image}" alt="${news.title}" loading="lazy" style="
                            width: 100%;
                            height: 100%;
                            object-fit: cover;
                            transition: transform 0.3s;
                        " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    </div>
                    <div class="side-news-content" style="flex: 1;">
                        <span class="side-news-category" style="
                            display: inline-block;
                            background: #ff0066;
                            color: white;
                            padding: 2px 8px;
                            border-radius: 4px;
                            font-size: 12px;
                            margin-bottom: 5px;
                        ">${news.category || '新聞'}</span>
                        <h4 class="side-news-title" style="
                            margin: 0 0 5px 0;
                            font-size: ${isSingle ? '18px' : '14px'};
                            line-height: 1.3;
                            color: #333;
                        ">${news.title}</h4>
                        <p class="side-news-summary" style="
                            margin: 0;
                            font-size: 13px;
                            color: #666;
                            line-height: 1.4;
                            display: -webkit-box;
                            -webkit-line-clamp: 2;
                            -webkit-box-orient: vertical;
                            overflow: hidden;
                        ">${news.summary || ''}</p>
                    </div>
                </a>
            `;
            sideContainer.appendChild(newsItem);
        });

        console.log(`✅ 側邊新聞已更新: ${newsList.length} 條`);
    }

    // 頁面加載完成後執行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadNews);
    } else {
        loadNews();
    }

    // 每5分鐘自動刷新
    setInterval(loadNews, 5 * 60 * 1000);

})();
