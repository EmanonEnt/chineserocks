/**
 * ChineseRocks 新聞加載器
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
                document.getElementById('news-list').innerHTML = '<div style="text-align:center;padding:2rem;">加载失败，请刷新重试</div>';
            });
    }

    function updateDisplay(news) {
        renderHero(news);
        renderList(news);
        renderTags(allNews);
        renderPicks(allNews);
    }

    function renderHero(news) {
        var heroMain = document.getElementById('hero-main');
        var heroSide = document.getElementById('hero-side');
        if (!heroMain || !news.length) return;

        // 第1篇 - 大图
        var main = news[0];
        document.getElementById('hero-img').src = main.cover_image || getDefaultImage();
        document.getElementById('hero-tag').textContent = main.category || '新聞';
        document.getElementById('hero-title').textContent = main.title || '無標題';
        document.getElementById('hero-excerpt').textContent = (main.content || '').substring(0, 120) + '...';
        document.getElementById('hero-date').textContent = formatDate(main.published_date);
        heroMain.onclick = function() { openArticle(main); };

        // 第2、3篇 - 小图
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
            container.innerHTML = '<div style="text-align:center;padding:2rem;">该分类暂无更多新闻</div>';
            return;
        }
        container.innerHTML = '';
        for (var i = 0; i < list.length; i++) {
            var n = list[i];
            var div = document.createElement('article');
            div.className = 'news-card';
            div.innerHTML = '<div class="news-thumb"><img src="' + (n.cover_image || getDefaultImage()) + '"></div>' +
                '<div class="news-content"><span class="news-category">' + (n.category || '新聞') + '</span>' +
                '<h3 class="news-title">' + (n.title || '無標題') + '</h3>' +
                '<p class="news-excerpt">' + (n.content || '').substring(0, 100) + '...</p></div>';
            div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
            container.appendChild(div);
        }
    }

    function renderTags(news) {
        var container = document.getElementById('tag-cloud');
        var tags = [];
        for (var i = 0; i < news.length; i++) {
            if (news[i].tags) {
                for (var j = 0; j < news[i].tags.length; j++) {
                    if (tags.indexOf(news[i].tags[j]) === -1) tags.push(news[i].tags[j]);
                }
            }
        }
        container.innerHTML = tags.slice(0, 12).map(function(t) {
            return '<button class="tag-item" onclick="filterByTag(">' + t + '</button>';
        }).join('');
    }

    function renderPicks(news) {
        var container = document.getElementById('editors-pick');
        var picks = news.filter(function(n) { return n.featured; }).slice(0, 4);
        container.innerHTML = picks.map(function(n) {
            return '<div class="pick-item"><img src="' + (n.cover_image || getDefaultImage()) + '" class="pick-thumb">' +
                '<div class="pick-content"><h4>' + n.title + '</h4></div></div>';
        }).join('');
    }

    window.filterNews = function(category, btn) {
        currentCategory = category;
        document.querySelectorAll('.category-btn').forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');

        var filtered = category === 'all' ? allNews : allNews.filter(function(n) {
            return (n.category === category) || (n.tags && n.tags.indexOf(category) !== -1);
        });
        updateDisplay(filtered);
    };

    window.filterByTag = function(tag) {
        updateDisplay(allNews.filter(function(n) { return n.tags && n.tags.indexOf(tag) !== -1; }));
    };

    function openArticle(article) {
        if (article.source_url) window.open(article.source_url, '_blank');
    }

    function getDefaultImage() {
        return 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop';
    }

    function formatDate(date) {
        if (!date) return '';
        var d = new Date(date);
        return d.getFullYear() + '.' + (d.getMonth() + 1) + '.' + d.getDate();
    }

    function isMember() { return localStorage.getItem('userLoggedIn') === 'true'; }
    function updateQuotaDisplay() {
        var el = document.getElementById('remainingReads');
        if (el) el.textContent = remainingReads;
    }
})();
