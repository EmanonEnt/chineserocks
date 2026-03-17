/**
 * ChineseRocks 新聞加載器 - 修復版
 * 修復：排序、右侧2个新闻、分类过滤
 */

(function() {
    'use strict';

    let allNews = [];
    let currentCategory = 'all';
    let remainingReads = 3;

    document.addEventListener('DOMContentLoaded', () => {
        loadNewsData();
        updateQuotaDisplay();
    });

    async function loadNewsData() {
        try {
            const res = await fetch('data/news.json?t=' + Date.now() + '&r=' + Math.random(), {
                cache: 'no-store',
                headers: {'Cache-Control': 'no-cache'}
            });

            if (!res.ok) throw new Error('HTTP ' + res.status);

            const newsData = await res.json();
            allNews = newsData.data?.all || newsData.data?.latest || [];

            // 🔧 修复1：按发布日期排序（最新的在前）
            allNews.sort((a, b) => {
                const dateA = new Date(a.published_date || a.created_time || 0);
                const dateB = new Date(b.published_date || b.created_time || 0);
                return dateB - dateA;
            });

            console.log('✅ 加载新闻:', allNews.length, '条');

            if (allNews.length === 0) {
                showEmptyState();
                return;
            }

            renderHeroSection(allNews);
            renderNewsList(allNews);
            renderTags(allNews);
            renderEditorsPick(allNews);
        } catch (e) {
            console.error('❌ 加载失败:', e);
            showErrorState();
        }
    }

    function checkIsPremium(article) {
        if (article.is_premium === true) return true;
        if (article.tags && Array.isArray(article.tags)) {
            return article.tags.includes('會員專享');
        }
        return false;
    }

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
    }

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
            if (checkIsPremium(main)) {
                heroPremium.innerHTML = '<span style="color:#FFD700;">★ 會員專享</span>';
            } else {
                heroPremium.textContent = '';
            }
        }

        heroMain.onclick = () => handleArticleClick(main);

        // 🔧 修复2：右侧显示2个新闻
        const sideContainer = document.getElementById('hero-side');
        if (!sideContainer) return;

        sideContainer.innerHTML = '';

        // 取第2和第3条新闻（如果存在）
        const sideNews = [];
        if (news.length > 1) sideNews.push(news[1]);
        if (news.length > 2) sideNews.push(news[2]);

        if (sideNews.length === 0) {
            sideContainer.style.display = 'none';
        } else {
            sideContainer.style.display = 'flex';
            sideContainer.style.flexDirection = 'column';
            sideContainer.style.gap = '20px';

            sideNews.forEach(n => {
                const sideCard = document.createElement('article');
                sideCard.className = 'side-card';
                sideCard.style.flex = '1';
                sideCard.onclick = () => handleArticleClick(n);

                const imgUrl = n.cover_image || n.image || getDefaultImage();
                const tag = n.category || '新聞';
                const title = n.title || '無標題';

                sideCard.innerHTML = `
                    <img src="${imgUrl}" alt="${title}" onerror="this.src='${getDefaultImage()}'" style="width:100%;height:100%;object-fit:cover;">
                    <div class="side-overlay">
                        <span class="side-tag">${tag}</span>
                        <h3 class="side-title">${title}</h3>
                    </div>
                `;
                sideContainer.appendChild(sideCard);
            });
        }
    }

    function renderNewsList(news) {
        const container = document.getElementById('news-list');
        if (!container) return;

        // 过滤分类
        let filtered = news;
        if (currentCategory !== 'all') {
            filtered = news.filter(n => {
                const cat = n.category || '';
                const tags = n.tags || [];

                // 🔧 修复3：分类映射（英文按钮 -> 中文分类）
                const catMap = {
                    'exclusive': '獨家',
                    'live': '現場',
                    'feature': '專題',
                    'international': '國際',
                    'releases': '新發行'
                };

                const targetCat = catMap[currentCategory] || currentCategory;
                return cat === targetCat || tags.includes(targetCat);
            });
        }

        // 跳过前3条（已经在Hero区域显示）
        const listNews = filtered.slice(3);

        if (listNews.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column:1/-1;">
                    <div class="empty-state-icon">📭</div>
                    <h3>該分類暫無更多新聞</h3>
                </div>
            `;
            return;
        }

        container.innerHTML = '';

        listNews.forEach(n => {
            const isPremium = checkIsPremium(n);
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
    }

    function renderTags(news) {
        const container = document.getElementById('tag-cloud');
        if (!container) return;

        const allTags = new Set();

        news.forEach(n => {
            if (n.tags && Array.isArray(n.tags)) {
                n.tags.forEach(tag => {
                    if (tag && !tag.includes('會員專享') && !tag.includes('編輯精選')) {
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

    function renderEditorsPick(news) {
        const container = document.getElementById('editors-pick');
        if (!container) return;

        const picks = news.filter(n => {
            if (n.featured === true) return true;
            if (!n.tags) return false;
            return n.tags.includes('編輯精選') || n.tags.includes('编辑精选');
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

    // 🔧 修复4：分类过滤函数
    window.filterNews = function(category, btn) {
        currentCategory = category;

        // 更新按钮样式
        document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // 重新渲染新闻列表（会根据currentCategory过滤）
        renderNewsList(allNews);

        // 滚动到新闻列表
        const newsList = document.getElementById('news-list');
        if (newsList) {
            newsList.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

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

    window.handleArticleClick = function(article) {
        console.log('点击文章:', article.title);

        if (!isMember() && remainingReads <= 0) {
            showMobilePaywall();
            return;
        }

        const isPremium = checkIsPremium(article);
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

    // 点击弹窗外部关闭
    const mobilePaywallModal = document.getElementById('mobilePaywallModal');
    if (mobilePaywallModal) {
        mobilePaywallModal.addEventListener('click', function(e) {
            if (e.target === this) {
                window.closeMobilePaywall();
            }
        });
    }

})();
