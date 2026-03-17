/**
 * ChineseRocks 新聞加載器
 * 從 data/news.json 動態加載新聞內容
 */

(function() {
    'use strict';

    // 全局變量
    let allNews = [];
    let currentCategory = 'all';
    let remainingReads = 3;
    let newsData = null;

    // 初始化
    document.addEventListener('DOMContentLoaded', () => {
        loadNewsData();
        updateQuotaDisplay();
    });

    // 加載新聞數據
    async function loadNewsData() {
        try {
            const res = await fetch('data/news.json?t=' + Date.now(), {cache: 'no-store'});
            if (!res.ok) throw new Error('HTTP ' + res.status);

            newsData = await res.json();
            allNews = newsData.data?.all || newsData.data?.latest || [];

            console.log('加載新聞:', allNews.length, '條');

            if (allNews.length === 0) {
                showEmptyState();
                return;
            }

            renderHeroSection(allNews);
            renderNewsList(allNews);
            renderTags(allNews);
            renderEditorsPick(allNews);
        } catch (e) {
            console.error('加載失敗:', e);
            showErrorState();
        }
    }

    // 顯示空狀態
    function showEmptyState() {
        const heroMain = document.getElementById('hero-main');
        const heroSide = document.getElementById('hero-side');
        const newsList = document.getElementById('news-list');

        if (heroMain) heroMain.style.display = 'none';
        if (heroSide) heroSide.innerHTML = '';
        if (newsList) {
            newsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📰</div>
                    <h3>暫無新聞</h3>
                    <p>請在 Notion 後台添加新聞後發布</p>
                </div>
            `;
        }

        const tagCloud = document.getElementById('tag-cloud');
        const editorsPick = document.getElementById('editors-pick');
        if (tagCloud) tagCloud.innerHTML = '<span style="color:#999;">暫無標籤</span>';
        if (editorsPick) editorsPick.innerHTML = '<span style="color:#999;">暫無精選</span>';
    }

    // 顯示錯誤狀態
    function showErrorState() {
        const newsList = document.getElementById('news-list');
        if (newsList) {
            newsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <h3>加載失敗</h3>
                    <p>請檢查網絡連接或刷新頁面重試</p>
                    <button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1rem;background:#FF0066;color:white;border:none;border-radius:4px;cursor:pointer;">重新加載</button>
                </div>
            `;
        }
    }

    // 渲染頭條區
    function renderHeroSection(news) {
        if (news.length === 0) return;

        const main = news[0];
        const heroMain = document.getElementById('hero-main');
        const heroImg = document.getElementById('hero-img');

        if (!heroMain || !heroImg) return;

        heroImg.src = main.cover_image || main.image || getDefaultImage();
        heroImg.alt = main.title || '新聞圖片';
        heroImg.onerror = function() {
            this.src = getDefaultImage();
        };

        const heroTag = document.getElementById('hero-tag');
        const heroTitle = document.getElementById('hero-title');
        const heroExcerpt = document.getElementById('hero-excerpt');
        const heroDate = document.getElementById('hero-date');
        const heroPremium = document.getElementById('hero-premium');

        if (heroTag) heroTag.textContent = main.category || '新聞';
        if (heroTitle) heroTitle.textContent = main.title || '無標題';

        const excerpt = (main.content || main.summary || '').substring(0, 120);
        if (heroExcerpt) heroExcerpt.textContent = excerpt ? excerpt + '...' : '';

        const dateStr = main.published_date || main.created_time || '';
        if (heroDate) heroDate.textContent = formatDate(dateStr);

        if (heroPremium) {
            if (main.is_premium || (main.tags && main.tags.includes('會員專享'))) {
                heroPremium.innerHTML = '<span style="color:#FFD700;">★ 會員專享</span>';
            } else {
                heroPremium.textContent = '';
            }
        }

        heroMain.onclick = () => handleArticleClick(main);

        const sideContainer = document.getElementById('hero-side');
        if (!sideContainer) return;

        sideContainer.innerHTML = '';

        const sideNews = news.slice(1, 3);
        if (sideNews.length === 0) {
            sideContainer.style.display = 'none';
        } else {
            sideContainer.style.display = 'flex';
            sideNews.forEach(n => {
                const sideCard = document.createElement('article');
                sideCard.className = 'side-card';
                sideCard.onclick = () => handleArticleClick(n);

                const imgUrl = n.cover_image || n.image || getDefaultImage();
                const tag = n.category || '新聞';
                const title = n.title || '無標題';

                sideCard.innerHTML = `
                    <img src="${imgUrl}" alt="${title}" onerror="this.src='${getDefaultImage()}'">
                    <div class="side-overlay">
                        <span class="side-tag">${tag}</span>
                        <h3 class="side-title">${title}</h3>
                    </div>
                `;
                sideContainer.appendChild(sideCard);
            });
        }
    }

    // 渲染新聞列表
    function renderNewsList(news) {
        const container = document.getElementById('news-list');
        if (!container) return;

        let filtered = news;
        if (currentCategory !== 'all') {
            filtered = news.filter(n => {
                const cat = n.category || '';
                const tags = n.tags || [];
                return cat === currentCategory || tags.includes(currentCategory);
            });
        }

        const listNews = filtered.slice(3);

        if (listNews.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <h3>該分類暫無更多新聞</h3>
                </div>
            `;
            return;
        }

        container.innerHTML = '';

        listNews.forEach(n => {
            const isPremium = n.is_premium || (n.tags && n.tags.includes('會員專享'));
            const cardClass = isPremium ? 'news-card premium' : 'news-card';
            const imgUrl = n.cover_image || n.image || getDefaultImage();
            const excerpt = (n.content || n.summary || '').substring(0, 100);
            const dateStr = formatDate(n.published_date || n.created_time || '');

            const card = document.createElement('article');
            card.className = cardClass;
            card.setAttribute('data-category', n.category || '');
            card.onclick = () => handleArticleClick(n);

            card.innerHTML = `
                <div class="news-thumb">
                    <img src="${imgUrl}" alt="${n.title || '新聞'}" loading="lazy" onerror="this.src='${getDefaultImage()}'">
                </div>
                <div class="news-content">
                    <span class="news-category">${n.category || '新聞'}</span>
                    <h3 class="news-title">${n.title || '無標題'}</h3>
                    <p class="news-excerpt">${excerpt ? excerpt + '...' : '暫無摘要'}</p>
                    <div class="news-footer">
                        <div class="news-meta">
                            <span>${dateStr}</span>
                            ${isPremium ? '<span style="color:#B8860B;font-weight:700;">★ 會員專享</span>' : ''}
                        </div>
                        <div class="news-actions">
                            <button class="action-btn" onclick="event.stopPropagation(); toggleFav(this, '${(n.title || '').replace(/'/g, "\'")}')">☆</button>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });

        if (filtered.length > 3 + listNews.length) {
            const loadMoreDiv = document.createElement('div');
            loadMoreDiv.className = 'load-more';
            loadMoreDiv.innerHTML = `
                <button class="load-more-btn" onclick="loadMore()">加載更多 LOAD MORE</button>
            `;
            container.appendChild(loadMoreDiv);
        }
    }

    // 渲染標籤
    function renderTags(news) {
        const container = document.getElementById('tag-cloud');
        if (!container) return;

        const allTags = new Set();

        news.forEach(n => {
            if (n.tags && Array.isArray(n.tags)) {
                n.tags.forEach(tag => {
                    if (tag && !tag.includes('會員專享')) {
                        allTags.add(tag);
                    }
                });
            }
        });

        const tags = Array.from(allTags).slice(0, 12);

        if (tags.length === 0) {
            container.innerHTML = '<span style="color:#999;">暫無標籤</span>';
            return;
        }

        container.innerHTML = tags.map(tag => 
            `<button class="tag-item" onclick="filterByTag('${tag.replace(/'/g, "\'")}', this)">#${tag}</button>`
        ).join('');
    }

    // 渲染編輯精選
    function renderEditorsPick(news) {
        const container = document.getElementById('editors-pick');
        if (!container) return;

        const picks = news.filter(n => {
            if (!n.tags) return false;
            return n.tags.includes('編輯精選') || n.tags.includes('编辑精选') || n.featured;
        }).slice(0, 4);

        const displayPicks = picks.length > 0 ? picks : news.slice(0, 4);

        if (displayPicks.length === 0) {
            container.innerHTML = '<span style="color:#999;">暫無精選</span>';
            return;
        }

        container.innerHTML = displayPicks.map(n => {
            const imgUrl = n.cover_image || n.image || getDefaultImage();
            return `
                <div class="pick-item" onclick='handleArticleClick(${JSON.stringify(n).replace(/'/g, "&#39;")})'>
                    <img src="${imgUrl}" alt="" class="pick-thumb" onerror="this.src='${getDefaultImage()}'">
                    <div class="pick-content">
                        <h4>${n.title || '無標題'}</h4>
                        <span>${n.category || '新聞'}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 分類篩選
    window.filterNews = function(category, btn) {
        currentCategory = category;
        document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderNewsList(allNews);

        const newsList = document.getElementById('news-list');
        if (newsList) {
            newsList.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    // 標籤篩選
    window.filterByTag = function(tag, btn) {
        const filtered = allNews.filter(n => {
            if (!n.tags) return false;
            return n.tags.includes(tag) || (n.title && n.title.includes(tag));
        });

        currentCategory = 'tag:' + tag;
        renderNewsList(filtered);

        document.querySelectorAll('.tag-item').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');

        document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
    };

    // 處理文章點擊
    window.handleArticleClick = function(article) {
        console.log('點擊文章:', article.title);

        if (!isMember() && remainingReads <= 0) {
            showMobilePaywall();
            return;
        }

        const isPremium = article.is_premium || (article.tags && article.tags.includes('會員專享'));
        if (isPremium && !isMember()) {
            showMobilePaywall();
            return;
        }

        if (!isMember()) {
            remainingReads--;
            updateQuotaDisplay();
        }

        if (article.source_url) {
            window.open(article.source_url, '_blank');
        } else {
            alert('文章詳情頁功能開發中...\n標題: ' + article.title);
        }
    };

    window.handleHeroClick = function() {
        if (allNews.length > 0) {
            window.handleArticleClick(allNews[0]);
        }
    };

    // 工具函數
    function getDefaultImage() {
        return 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop';
    }
    window.getDefaultImage = getDefaultImage;

    function formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return dateStr;
            return date.toLocaleDateString('zh-TW', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            }).replace(/\//g, '.');
        } catch (e) {
            return dateStr;
        }
    }
    window.formatDate = formatDate;

    function isMember() {
        return localStorage.getItem('userLoggedIn') === 'true';
    }
    window.isMember = isMember;

    function updateQuotaDisplay() {
        const el = document.getElementById('remainingReads');
        if (el) el.textContent = remainingReads;
    }
    window.updateQuotaDisplay = updateQuotaDisplay;

    function showMobilePaywall() {
        const modal = document.getElementById('mobilePaywallModal');
        if (modal) modal.classList.add('active');
    }
    window.showMobilePaywall = showMobilePaywall;

    window.closeMobilePaywall = function() {
        const modal = document.getElementById('mobilePaywallModal');
        if (modal) modal.classList.remove('active');
    };

    window.toggleFav = function(btn, title) {
        if (!isMember()) {
            alert('請先登入');
            return;
        }
        btn.classList.toggle('active');
        btn.textContent = btn.classList.contains('active') ? '★' : '☆';

        let favorites = JSON.parse(localStorage.getItem('newsFavorites') || '[]');
        if (btn.classList.contains('active')) {
            favorites.push(title);
        } else {
            favorites = favorites.filter(t => t !== title);
        }
        localStorage.setItem('newsFavorites', JSON.stringify(favorites));
    };

    window.loadMore = function() {
        alert('加載更多功能（演示）');
    };

    // 點擊彈窗外部關閉
    const mobilePaywallModal = document.getElementById('mobilePaywallModal');
    if (mobilePaywallModal) {
        mobilePaywallModal.addEventListener('click', function(e) {
            if (e.target === this) {
                window.closeMobilePaywall();
            }
        });
    }

})();
