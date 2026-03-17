/**
 * ChineseRocks 新聞加載器 - 完整版
 */
(function() {
    var allNews = [];
    var currentCategory = 'all';
    var remainingReads = 3;

    document.addEventListener('DOMContentLoaded', function() {
        loadNewsData();
        updateQuotaDisplay();
    });

    function loadNewsData() {
        fetch('data/news.json?t=' + Date.now(), {cache: 'no-store'})
            .then(function(res) { return res.json(); })
            .then(function(data) {
                allNews = data.data && data.data.all ? data.data.all : [];
                allNews.sort(function(a, b) {
                    return new Date(b.published_date || b.created_time || 0) - new Date(a.published_date || a.created_time || 0);
                });
                updateDisplay(allNews);
            })
            .catch(function(e) {
                console.error('加载失败:', e);
            });
    }

    function updateDisplay(news) {
        renderHero(news);
        renderList(news);
        renderTags(allNews);
        renderPicks(allNews);
    }

    function checkIsPremium(article) {
        if (article.is_premium === true) return true;
        if (article.tags && article.tags.indexOf('會員專享') !== -1) return true;
        return false;
    }

    function renderHero(news) {
        var heroMain = document.getElementById('hero-main');
        var heroSide = document.getElementById('hero-side');
        if (!heroMain || !news.length) return;

        var main = news[0];
        var isPremium = checkIsPremium(main);

        document.getElementById('hero-img').src = main.cover_image || getDefaultImage();
        document.getElementById('hero-tag').textContent = main.category || '新聞';
        document.getElementById('hero-title').textContent = main.title || '無標題';
        document.getElementById('hero-excerpt').textContent = (main.content || '').substring(0, 120) + '...';
        document.getElementById('hero-date').textContent = formatDate(main.published_date);

        var heroPremium = document.getElementById('hero-premium');
        if (heroPremium) {
            heroPremium.innerHTML = isPremium ? '<span style="color:#FFD700;">★ 會員專享</span>' : '';
        }

        heroMain.onclick = function() { openArticle(main); };

        // 右侧2小图
        heroSide.innerHTML = '';
        for (var i = 1; i < Math.min(3, news.length); i++) {
            var n = news[i];
            var div = document.createElement('article');
            div.className = 'side-card';
            div.innerHTML = '<img src="' + (n.cover_image || getDefaultImage()) + '" onerror="this.src=getDefaultImage()">' +
                '<div class="side-overlay"><span class="side-tag">' + (n.category || '新聞') + '</span>' +
                '<h3 class="side-title">' + (n.title || '無標題') + '</h3></div>';
            div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
            heroSide.appendChild(div);
        }
    }

    function renderList(news) {
        var container = document.getElementById('news-list');
        var list = news.slice(3);
        if (!list.length) {
            container.innerHTML = '<div style="text-align:center;padding:2rem;grid-column:1/-1;">该分类暂无更多新闻</div>';
            return;
        }
        container.innerHTML = '';

        for (var i = 0; i < list.length; i++) {
            var n = list[i];
            var isPremium = checkIsPremium(n);
            var cardClass = isPremium ? 'news-card premium' : 'news-card';

            var div = document.createElement('article');
            div.className = cardClass;
            div.innerHTML = '<div class="news-thumb"><img src="' + (n.cover_image || getDefaultImage()) + '"></div>' +
                '<div class="news-content">' +
                '<span class="news-category">' + (n.category || '新聞') + '</span>' +
                '<h3 class="news-title">' + (n.title || '無標題') + '</h3>' +
                '<p class="news-excerpt">' + (n.content || '').substring(0, 100) + '...</p>' +
                '<div class="news-footer">' +
                '<div class="news-meta"><span>' + formatDate(n.published_date) + '</span>' +
                (isPremium ? '<span style="color:#B8860B;font-weight:700;">★ 會員專享</span>' : '') +
                '</div></div></div>';
            div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
            container.appendChild(div);
        }
    }

    function renderTags(news) {
        var container = document.getElementById('tag-cloud');
        if (!container) return;
        var tags = [];
        for (var i = 0; i < news.length; i++) {
            if (news[i].tags) {
                for (var j = 0; j < news[i].tags.length; j++) {
                    var tag = news[i].tags[j];
                    if (tags.indexOf(tag) === -1 && tag !== '會員專享' && tag !== '編輯精選') {
                        tags.push(tag);
                    }
                }
            }
        }
        container.innerHTML = tags.slice(0, 12).map(function(t) {
            return '<button class="tag-item" onclick="filterByTag(' + JSON.stringify(t) + ', this)">#' + t + '</button>';
        }).join('');
    }

    function renderPicks(news) {
        var container = document.getElementById('editors-pick');
        if (!container) return;
        var picks = [];
        for (var i = 0; i < news.length; i++) {
            if (news[i].featured || (news[i].tags && (news[i].tags.indexOf('編輯精選') !== -1 || news[i].tags.indexOf('编辑精选') !== -1))) {
                picks.push(news[i]);
            }
        }
        var display = picks.length > 0 ? picks.slice(0, 4) : news.slice(0, 4);
        container.innerHTML = display.map(function(n) {
            return '<div class="pick-item" onclick="openArticle(' + JSON.stringify(n) + ')">' +
                '<img src="' + (n.cover_image || getDefaultImage()) + '" class="pick-thumb">' +
                '<div class="pick-content"><h4>' + n.title + '</h4><span>' + (n.category || '新聞') + '</span></div></div>';
        }).join('');
    }

    window.filterNews = function(category, btn) {
        currentCategory = category;
        var buttons = document.querySelectorAll('.category-btn');
        for (var i = 0; i < buttons.length; i++) {
            buttons[i].classList.remove('active');
        }
        btn.classList.add('active');

        var filtered = category === 'all' ? allNews : allNews.filter(function(n) {
            return (n.category === category) || (n.tags && n.tags.indexOf(category) !== -1);
        });
        updateDisplay(filtered);
        // 不滚动，只刷新内容
    };

    window.filterByTag = function(tag, btn) {
        var filtered = allNews.filter(function(n) { return n.tags && n.tags.indexOf(tag) !== -1; });
        updateDisplay(filtered);
    };

    window.openArticle = function(article) {
        if (!isMember() && remainingReads <= 0) {
            showMobilePaywall();
            return;
        }
        if (checkIsPremium(article) && !isMember()) {
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

    function getDefaultImage() {
        return 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop';
    }

    function formatDate(date) {
        if (!date) return '';
        var d = new Date(date);
        return d.getFullYear() + '.' + (d.getMonth() + 1) + '.' + d.getDate();
    }

    function isMember() {
        return localStorage.getItem('userLoggedIn') === 'true';
    }

    function updateQuotaDisplay() {
        var el = document.getElementById('remainingReads');
        if (el) el.textContent = remainingReads;
    }

    window.showMobilePaywall = function() {
        var modal = document.getElementById('mobilePaywallModal');
        if (modal) modal.classList.add('active');
    };

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
    };
})();
