/**
 * ChineseRocks 新聞加載器 - 最終修復版
 */
(function() {
    'use strict';

    var allNews = [];
    var currentCategory = 'all';
    var remainingReads = 3;

    document.addEventListener('DOMContentLoaded', function() {
        console.log('📰 新聞加載器 v3 啟動');
        loadNewsData();
        updateQuotaDisplay();
    });

    function loadNewsData() {
        fetch('data/news.json?t=' + Date.now(), {
            cache: 'no-store',
            headers: { 'Accept': 'application/json' }
        })
        .then(function(res) { 
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json(); 
        })
        .then(function(data) {
            console.log('✓ 數據加載成功');

            if (Array.isArray(data)) {
                allNews = data;
            } else if (data.data && data.data.all) {
                allNews = data.data.all;
            } else {
                allNews = [];
            }

            console.log('文章數:', allNews.length);

            // 排序
            allNews.sort(function(a, b) {
                var dateA = new Date(a.publishDate || a.published_date || a.date || 0);
                var dateB = new Date(b.publishDate || b.published_date || b.date || 0);
                return dateB - dateA;
            });

            updateDisplay(allNews);
        })
        .catch(function(e) {
            console.error('加載失敗:', e);
        });
    }

    function updateDisplay(news) {
        if (!news || !news.length) {
            console.warn('沒有新聞數據');
            return;
        }
        renderHero(news);
        renderList(news);
        renderTags(allNews);
        renderPicks(allNews);
    }

    function checkIsPremium(article) {
        if (article.is_premium === true || article.isPremium === true) return true;
        if (article.tags && article.tags.indexOf('會員專享') !== -1) return true;
        return false;
    }

    // 🔧 獲取圖片URL
    function getImageUrl(article) {
        var url = article.coverImage || article.cover_image || article.image || article.cover;
        return url || getDefaultImage();
    }

    function renderHero(news) {
        var heroMain = document.getElementById('hero-main');
        var heroSide = document.getElementById('hero-side');
        if (!heroMain || !news.length) return;

        var main = news[0];
        var isPremium = checkIsPremium(main);

        console.log('主文章:', main.title, '圖片:', getImageUrl(main).substring(0, 50));

        // 主圖
        var heroImg = document.getElementById('hero-img');
        if (heroImg) {
            heroImg.onerror = function() { this.src = getDefaultImage(); };
            heroImg.src = getImageUrl(main);
        }

        if (document.getElementById('hero-tag')) 
            document.getElementById('hero-tag').textContent = main.category || '新聞';
        if (document.getElementById('hero-title')) 
            document.getElementById('hero-title').textContent = main.title || '無標題';
        if (document.getElementById('hero-excerpt')) {
            var content = main.content || main.excerpt || main.summary || '';
            document.getElementById('hero-excerpt').textContent = content.substring(0, 120) + '...';
        }
        if (document.getElementById('hero-date')) 
            document.getElementById('hero-date').textContent = formatDate(main.publishDate || main.published_date || main.date);
        if (document.getElementById('hero-premium')) 
            document.getElementById('hero-premium').innerHTML = isPremium ? '<span style="color:#FFD700;">★ 會員專享</span>' : '';

        heroMain.onclick = function() { openArticle(main); };

        // 右側2小圖
        if (heroSide) {
            heroSide.innerHTML = '';
            for (var i = 1; i < Math.min(3, news.length); i++) {
                (function(article, index) {
                    var imgUrl = getImageUrl(article);
                    console.log('側邊' + index + ':', article.title, '圖片:', imgUrl.substring(0, 50));

                    var div = document.createElement('article');
                    div.className = 'side-card';
                    div.innerHTML = '<img src="' + imgUrl + '" onerror="this.src=\'' + getDefaultImage() + '\'">' +
                        '<div class="side-overlay"><span class="side-tag">' + (article.category || '新聞') + '</span>' +
                        '<h3 class="side-title">' + (article.title || '無標題') + '</h3></div>';
                    div.onclick = function() { openArticle(article); };
                    heroSide.appendChild(div);
                })(news[i], i);
            }
        }
    }

    function renderList(news) {
        var container = document.getElementById('news-list');
        if (!container) return;

        var list = news.slice(3);
        if (!list.length) {
            container.innerHTML = '<div style="text-align:center;padding:2rem;grid-column:1/-1;">暫無更多新聞</div>';
            return;
        }
        container.innerHTML = '';

        for (var i = 0; i < list.length; i++) {
            (function(article, index) {
                var isPremium = checkIsPremium(article);
                var cardClass = isPremium ? 'news-card premium' : 'news-card';
                var imgUrl = getImageUrl(article);

                console.log('列表' + index + ':', article.title, '圖片:', imgUrl.substring(0, 50));

                var div = document.createElement('article');
                div.className = cardClass;
                div.innerHTML = '<div class="news-thumb"><img src="' + imgUrl + '" onerror="this.src=\'' + getDefaultImage() + '\'"></div>' +
                    '<div class="news-content">' +
                    '<span class="news-category">' + (article.category || '新聞') + '</span>' +
                    '<h3 class="news-title">' + (article.title || '無標題') + '</h3>' +
                    '<p class="news-excerpt">' + (article.content || article.excerpt || '').substring(0, 100) + '...</p>' +
                    '<div class="news-footer">' +
                    '<div class="news-meta"><span>' + formatDate(article.publishDate || article.published_date || article.date) + '</span>' +
                    (isPremium ? '<span style="color:#B8860B;font-weight:700;">★ 會員專享</span>' : '') +
                    '</div></div></div>';
                div.onclick = function() { openArticle(article); };
                container.appendChild(div);
            })(list[i], i);
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
            if (news[i].featured || (news[i].tags && news[i].tags.indexOf('編輯精選') !== -1)) {
                picks.push(news[i]);
            }
        }
        var display = picks.length > 0 ? picks.slice(0, 4) : news.slice(0, 4);
        container.innerHTML = display.map(function(n) {
            return '<div class="pick-item" onclick="openArticleById(' + JSON.stringify(n.id) + ')">' +
                '<img src="' + getImageUrl(n) + '" class="pick-thumb" onerror="this.src=\'' + getDefaultImage() + '\'">' +
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
    };

    window.filterByTag = function(tag, btn) {
        var filtered = allNews.filter(function(n) { return n.tags && n.tags.indexOf(tag) !== -1; });
        updateDisplay(filtered);
    };

    window.openArticleById = function(id) {
        var article = allNews.find(function(n) { return n.id === id; });
        if (article) openArticle(article);
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
        if (article.source_url || article.sourceUrl) {
            window.open(article.source_url || article.sourceUrl, '_blank');
        } else {
            alert('文章詳情頁開發中...\n' + article.title);
        }
    };

    function getDefaultImage() {
        return 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=500&fit=crop';
    }

    function formatDate(date) {
        if (!date) return '';
        var d = new Date(date);
        if (isNaN(d.getTime())) return '';
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
