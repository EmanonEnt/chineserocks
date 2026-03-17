/**
 * ChineseRocks 新聞加載器 - 分類布局版本
 */

(function() {
    'use strict';

    let allNews = [];
    let currentCategory = 'all';
    let remainingReads = 3;

    document.addEventListener('DOMContentLoaded', function() {
        loadNewsData();
        updateQuotaDisplay();
    });

    function loadNewsData() {
        fetch('data/news.json?t=' + Date.now(), {cache: 'no-store'})
            .then(function(res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function(newsData) {
                allNews = newsData.data && newsData.data.all ? newsData.data.all : [];

                // 按发布日期排序
                allNews.sort(function(a, b) {
                    var dateA = new Date(a.published_date || a.created_time || 0);
                    var dateB = new Date(b.published_date || b.created_time || 0);
                    return dateB - dateA;
                });

                console.log('加载新闻:', allNews.length, '条');

                if (allNews.length === 0) {
                    showEmptyState();
                    return;
                }

                // 初始显示全部
                updateDisplay(allNews);
            })
            .catch(function(e) {
                console.error('加载失败:', e);
                showErrorState();
            });
    }

    function updateDisplay(news) {
        // 更新Hero区域（前3篇）
        renderHeroSection(news);
        // 更新下方列表（从第4篇开始）
        renderNewsList(news);
        // 更新标签和精选
        renderTags(allNews);
        renderEditorsPick(allNews);
    }

    function checkIsPremium(article) {
        if (article.is_premium === true) return true;
        if (article.tags && Array.isArray(article.tags)) {
            return article.tags.indexOf('會員專享') !== -1;
        }
        return false;
    }

    function showEmptyState() {
        var heroMain = document.getElementById('hero-main');
        var heroSide = document.getElementById('hero-side');
        var newsList = document.getElementById('news-list');

        if (heroMain) heroMain.style.display = 'none';
        if (heroSide) heroSide.innerHTML = '';
        if (newsList) {
            newsList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📰</div><h3>暫無新聞</h3></div>';
        }
    }

    function showErrorState() {
        var newsList = document.getElementById('news-list');
        if (newsList) {
            newsList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>加載失敗</h3><button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1rem;background:#FF0066;color:white;border:none;border-radius:4px;">重新加載</button></div>';
        }
    }

    function renderHeroSection(news) {
        var heroMain = document.getElementById('hero-main');
        var heroSide = document.getElementById('hero-side');

        if (!heroMain || !heroSide) return;

        if (news.length === 0) {
            heroMain.style.display = 'none';
            heroSide.style.display = 'none';
            return;
        }

        heroMain.style.display = 'block';
        heroSide.style.display = 'flex';

        // 第1篇 - 左侧大图
        var main = news[0];
        var heroImg = document.getElementById('hero-img');
        var heroTag = document.getElementById('hero-tag');
        var heroTitle = document.getElementById('hero-title');
        var heroExcerpt = document.getElementById('hero-excerpt');
        var heroDate = document.getElementById('hero-date');
        var heroPremium = document.getElementById('hero-premium');

        if (heroImg) {
            heroImg.src = main.cover_image || main.image || getDefaultImage();
            heroImg.alt = main.title || '新聞圖片';
            heroImg.onerror = function() { this.src = getDefaultImage(); };
        }
        if (heroTag) heroTag.textContent = main.category || '新聞';
        if (heroTitle) heroTitle.textContent = main.title || '無標題';
        if (heroExcerpt) {
            var excerpt = (main.content || main.summary || '').substring(0, 120);
            heroExcerpt.textContent = excerpt ? excerpt + '...' : '';
        }
        if (heroDate) heroDate.textContent = formatDate(main.published_date || main.created_time || '');
        if (heroPremium) {
            heroPremium.innerHTML = checkIsPremium(main) ? '<span style="color:#FFD700;">★ 會員專享</span>' : '';
        }

        heroMain.onclick = function() { handleArticleClick(main); };

        // 第2、3篇 - 右侧小图
        heroSide.innerHTML = '';
        for (var i = 1; i < 3 && i < news.length; i++) {
            var n = news[i];
            var sideCard = document.createElement('article');
            sideCard.className = 'side-card';
            sideCard.onclick = (function(article) {
                return function() { handleArticleClick(article); };
            })(n);

            var imgUrl = n.cover_image || n.image || getDefaultImage();
            sideCard.innerHTML = 
                '<img src="' + imgUrl + '" alt="' + (n.title || '') + '" onerror="this.src='"+getDefaultImage()+"">' +
                '<div class="side-overlay">' +
                    '<span class="side-tag">' + (n.category || '新聞') + '</span>' +
                    '<h3 class="side-title">' + (n.title || '無標題') + '</h3>' +
                '</div>';
            heroSide.appendChild(sideCard);
        }
    }

    function renderNewsList(news) {
        var container = document.getElementById('news-list');
        if (!container) return;

        // 跳过前3篇（已在Hero显示）
        var listNews = news.slice(3);

        if (listNews.length === 0) {
            container.innerHTML = '<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state-icon">📭</div><h3>該分類暫無更多新聞</h3></div>';
            return;
        }

        container.innerHTML = '';

        for (var i = 0; i < listNews.length; i++) {
            var n = listNews[i];
            var isPremium = checkIsPremium(n);
            var cardClass = isPremium ? 'news-card premium' : 'news-card';
            var imgUrl = n.cover_image || n.image || getDefaultImage();
            var excerpt = (n.content || n.summary || '').substring(0, 100);
            var dateStr = formatDate(n.published_date || n.created_time || '');

            var card = document.createElement('article');
            card.className = cardClass;
            card.onclick = (function(article) {
                return function() { handleArticleClick(article); };
            })(n);

            card.innerHTML = 
                '<div class="news-thumb"><img src="' + imgUrl + '" alt="' + (n.title || '') + '" loading="lazy" onerror="this.src='"+getDefaultImage()+""></div>' +
                '<div class="news-content">' +
                    '<span class="news-category">' + (n.category || '新聞') + '</span>' +
                    '<h3 class="news-title">' + (n.title || '無標題') + '</h3>' +
                    '<p class="news-excerpt">' + (excerpt ? excerpt + '...' : '暫無摘要') + '</p>' +
                    '<div class="news-footer">' +
                        '<div class="news-meta">' +
                            '<span>' + dateStr + '</span>' +
                            (isPremium ? '<span style="color:#B8860B;font-weight:700;">★ 會員專享</span>' : '') +
                        '</div>' +
                        '<div class="news-actions">' +
                            '<button class="action-btn" onclick="event.stopPropagation(); toggleFav(this, '' + (n.title || '').replace(/'/g, "\'") + '')">☆</button>' +
                        '</div>' +
                    '</div>' +
                '</div>';
            container.appendChild(card);
        }
    }

    function renderTags(news) {
        var container = document.getElementById('tag-cloud');
        if (!container) return;

        var allTags = [];
        for (var i = 0; i < news.length; i++) {
            if (news[i].tags && Array.isArray(news[i].tags)) {
                for (var j = 0; j < news[i].tags.length; j++) {
                    var tag = news[i].tags[j];
                    if (tag && tag.indexOf('會員專享') === -1 && tag.indexOf('編輯精選') === -1) {
                        if (allTags.indexOf(tag) === -1) allTags.push(tag);
                    }
                }
            }
        }

        if (allTags.length === 0) {
            container.innerHTML = '<span style="color:#999;">暫無標籤</span>';
            return;
        }

        var html = '';
        for (var k = 0; k < Math.min(allTags.length, 12); k++) {
            html += '<button class="tag-item" onclick="filterByTag('' + allTags[k].replace(/'/g, "\'") + '', this)">#' + allTags[k] + '</button>';
        }
        container.innerHTML = html;
    }

    function renderEditorsPick(news) {
        var container = document.getElementById('editors-pick');
        if (!container) return;

        var picks = [];
        for (var i = 0; i < news.length; i++) {
            if (news[i].featured === true || (news[i].tags && (news[i].tags.indexOf('編輯精選') !== -1 || news[i].tags.indexOf('编辑精选') !== -1))) {
                picks.push(news[i]);
            }
        }

        var displayPicks = picks.length > 0 ? picks.slice(0, 4) : news.slice(0, 4);

        if (displayPicks.length === 0) {
            container.innerHTML = '<span style="color:#999;">暫無精選</span>';
            return;
        }

        var html = '';
        for (var j = 0; j < displayPicks.length; j++) {
            var n = displayPicks[j];
            var imgUrl = n.cover_image || n.image || getDefaultImage();
            html += '<div class="pick-item" onclick="handleArticleClick(' + JSON.stringify(n).replace(/'/g, "&#39;") + ')">' +
                '<img src="' + imgUrl + '" alt="" class="pick-thumb" onerror="this.src='"+getDefaultImage()+"">' +
                '<div class="pick-content"><h4>' + (n.title || '無標題') + '</h4><span>' + (n.category || '新聞') + '</span></div>' +
            '</div>';
        }
        container.innerHTML = html;
    }

    // 分类过滤
    window.filterNews = function(category, btn) {
        currentCategory = category;

        // 更新按钮样式
        var buttons = document.querySelectorAll('.category-btn');
        for (var i = 0; i < buttons.length; i++) {
            buttons[i].classList.remove('active');
        }
        btn.classList.add('active');

        // 过滤数据
        var filtered = allNews;
        if (category !== 'all') {
            filtered = [];
            for (var j = 0; j < allNews.length; j++) {
                var n = allNews[j];
                var cat = n.category || '';
                var tags = n.tags || [];
                if (cat === category || tags.indexOf(category) !== -1) {
                    filtered.push(n);
                }
            }
        }

        // 更新显示
        updateDisplay(filtered);

        // 滚动到新闻区域
        var newsList = document.getElementById('news-list');
        if (newsList) {
            newsList.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    window.filterByTag = function(tag, btn) {
        var filtered = [];
        for (var i = 0; i < allNews.length; i++) {
            if (allNews[i].tags && allNews[i].tags.indexOf(tag) !== -1) {
                filtered.push(allNews[i]);
            }
        }

        currentCategory = 'tag:' + tag;
        updateDisplay(filtered);

        var tagItems = document.querySelectorAll('.tag-item');
        for (var j = 0; j < tagItems.length; j++) {
            tagItems[j].classList.remove('active');
        }
        btn.classList.add('active');

        var catButtons = document.querySelectorAll('.category-btn');
        for (var k = 0; k < catButtons.length; k++) {
            catButtons[k].classList.remove('active');
        }
    };

    window.handleArticleClick = function(article) {
        if (!isMember() && remainingReads <= 0) {
            showMobilePaywall();
            return;
        }

        var isPremium = checkIsPremium(article);
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
            handleArticleClick(allNews[0]);
        }
    };

    function getDefaultImage() {
        return 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop';
    }
    window.getDefaultImage = getDefaultImage;

    function formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            var date = new Date(dateStr);
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
        var el = document.getElementById('remainingReads');
        if (el) el.textContent = remainingReads;
    }
    window.updateQuotaDisplay = updateQuotaDisplay;

    function showMobilePaywall() {
        var modal = document.getElementById('mobilePaywallModal');
        if (modal) modal.classList.add('active');
    }
    window.showMobilePaywall = showMobilePaywall;

    window.closeMobilePaywall = function() {
        var modal = document.getElementById('mobilePaywallModal');
        if (modal) modal.classList.remove('active');
    };

    window.toggleFav = function(btn, title) {
        if (!isMember()) {
            alert('請先登入');
            return;
        }
        btn.classList.toggle('active');
        btn.textContent = btn.classList.contains('active') ? '★' : '☆';

        var favorites = JSON.parse(localStorage.getItem('newsFavorites') || '[]');
        if (btn.classList.contains('active')) {
            favorites.push(title);
        } else {
            favorites = favorites.filter(function(t) { return t !== title; });
        }
        localStorage.setItem('newsFavorites', JSON.stringify(favorites));
    };

    window.loadMore = function() {
        alert('加載更多功能（演示）');
    };

})();
