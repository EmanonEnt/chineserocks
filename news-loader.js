/**
 * ChineseRocks 新聞加載器 - 修復版
 * 修復：圖片不顯示問題
 */
(function() {
    var allNews = [];
    var currentCategory = 'all';
    // ===== 分類雙語映射 =====
    var categoryBilingualMap = {
        '獨家': '獨家 EXCLUSIVE',
        '現場': '現場 LIVE',
        '專題': '專題 FEATURE',
        '國際': '國際 INTERNATIONAL',
        '新發行': '新發行 RELEASES',
        '新聞': '新聞 NEWS',
        '音樂': '音樂 MUSIC'
    };

    function translateCategory(category) {
        if (!category) return '新聞 NEWS';
        // 如果已經是雙語格式，直接返回
        if (category.indexOf(' ') !== -1 && /[a-zA-Z]/.test(category)) {
            return category;
        }
        return categoryBilingualMap[category] || category + ' NEWS';
    }
    // ==========================


    var remainingReads = 3;

    document.addEventListener('DOMContentLoaded', function() {
        loadNewsData();
        updateQuotaDisplay();
    });

    function loadNewsData() {
        // 添加时间戳防止缓存
        fetch('data/news.json?t=' + Date.now(), {
            cache: 'no-store',
            headers: { 'Accept': 'application/json' }
        })
        .then(function(res) { 
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json(); 
        })
        .then(function(data) {
            console.log('✓ 數據加載成功:', data);

            // 兼容多種數據格式
            if (Array.isArray(data)) {
                allNews = data;
            } else if (data.data && data.data.all) {
                allNews = data.data.all;
            } else if (data.articles) {
                allNews = data.articles;
            } else {
                allNews = [];
            }

            console.log('✓ 解析到 ' + allNews.length + ' 篇文章');

            // 排序
            allNews.sort(function(a, b) {
                var dateA = new Date(b.published_date || b.publishDate || b.date || b.created_time || 0);
                var dateB = new Date(a.published_date || a.publishDate || a.date || a.created_time || 0);
                return dateA - dateB;
            });

            updateDisplay(allNews);
        })
        .catch(function(e) {
            console.error('✗ 加載失敗:', e);
            showError('新聞加載失敗，請檢查網絡連接');
        });
    }

    function showError(msg) {
        var heroMain = document.getElementById('hero-main');
        if (heroMain) {
            heroMain.innerHTML = '<div style="padding:40px;text-align:center;color:#ff0066;">' + msg + '</div>';
        }
    }

    function updateDisplay(news) {
        if (!news || !news.length) {
            console.warn('沒有新聞數據');
            return;
        }
        renderHero(news);
        renderList(news);
        renderTags(allNews);
        renderPicks(news);
    }

    function checkIsPremium(article) {
        if (article.is_premium === true) return true;
        if (article.isPremium === true) return true;
        if (article.tags && article.tags.indexOf('會員專享') !== -1) return true;
        return false;
    }

    // 🔧 修復：統一獲取圖片URL函數
    function getImageUrl(article) {
        // 嘗試多種可能的字段名
        var url = article.cover_image || article.coverImage || article.image || article.cover || article.thumbnail;

        if (!url) {
            console.warn('文章沒有圖片:', article.title);
            return getDefaultImage();
        }

        // 檢查是否是Notion過期URL
        if (url.indexOf('notion.so') !== -1 || url.indexOf('amazonaws.com') !== -1) {
            console.log('Notion圖片URL:', url.substring(0, 50) + '...');
        }

        return url;
    }

    function renderHero(news) {
        var heroMain = document.getElementById('hero-main');
        var heroSide = document.getElementById('hero-side');
        if (!heroMain || !news.length) return;

        var main = news[0];
        var isPremium = checkIsPremium(main);
        var imageUrl = getImageUrl(main);

        console.log('主圖URL:', imageUrl);

        // 🔧 修復：添加圖片加載錯誤處理
        var heroImg = document.getElementById('hero-img');
        if (heroImg) {
            heroImg.onerror = function() {
                console.error('主圖加載失敗，使用默認圖');
                this.src = getDefaultImage();
            };
            heroImg.onload = function() {
                console.log('✓ 主圖加載成功');
            };
            heroImg.src = imageUrl;
        }

        var heroTag = document.getElementById('hero-tag');
        if (heroTag) heroTag.textContent = translateCategory(main.category);

        var heroTitle = document.getElementById('hero-title');
        if (heroTitle) heroTitle.textContent = main.title || '無標題';

        var heroExcerpt = document.getElementById('hero-excerpt');
        if (heroExcerpt) {
            var content = main.content || main.excerpt || main.summary || '';
            heroExcerpt.textContent = content.substring(0, 120) + (content.length > 120 ? '...' : '');
        }

        var heroDate = document.getElementById('hero-date');
        if (heroDate) heroDate.textContent = formatDate(main.published_date || main.publishDate || main.date);

        var heroPremium = document.getElementById('hero-premium');
        if (heroPremium) {
            heroPremium.innerHTML = isPremium ? '<span style="color:#FFD700;">★ 會員專享</span>' : '';
        }

        heroMain.onclick = function() { openArticle(main); };

        // 右側2小圖
        if (heroSide) {
            heroSide.innerHTML = '';
            for (var i = 1; i < Math.min(3, news.length); i++) {
                var n = news[i];
                var sideImageUrl = getImageUrl(n);

                var div = document.createElement('article');
                div.className = 'side-card';
                div.innerHTML = '<img src="' + sideImageUrl + '" onerror="this.onerror=null;this.src=\'' + getDefaultImage() + '\'">' +
                    '<div class="side-overlay"><span class="side-tag">' + translateCategory(n.category) + '</span>' +
                    '<h3 class="side-title">' + (n.title || '無標題') + '</h3></div>';
                div.onclick = (function(article) { return function() { openArticle(article); }; })(n);
                heroSide.appendChild(div);
            }
        }
    }

    function renderList(news) {
        var container = document.getElementById('news-list');
        if (!container) return;

        var list = news.slice(3);
        if (!list.length) {
            container.innerHTML = '<div style="text-align:center;padding:2rem;grid-column:1/-1;">該分類暫無更多新聞</div>';
            return;
        }
        container.innerHTML = '';

        for (var i = 0; i < list.length; i++) {
            var n = list[i];
            var isPremium = checkIsPremium(n);
            var cardClass = isPremium ? 'news-card premium' : 'news-card';
            var listImageUrl = getImageUrl(n);

            var div = document.createElement('article');
            div.className = cardClass;
            div.innerHTML = '<div class="news-thumb"><img src="' + listImageUrl + '" onerror="this.onerror=null;this.src=\'' + getDefaultImage() + '\'"></div>' +
                '<div class="news-content">' +
                '<span class="news-category">' + translateCategory(n.category) + '</span>' +
                '<h3 class="news-title">' + (n.title || '無標題') + '</h3>' +
                '<p class="news-excerpt">' + (n.content || n.excerpt || '').substring(0, 100) + '...</p>' +
                '<div class="news-footer">' +
                '<div class="news-meta"><span>' + formatDate(n.published_date || n.publishDate || n.date) + '</span>' +
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
        var display = picks.length > 0 ? picks.slice(0, 6) : news.slice(0, 6);
        container.innerHTML = display.map(function(n) {
            var pickImageUrl = getImageUrl(n);
            return '<div class="pick-item" onclick="openArticle(' + JSON.stringify(n).replace(/"/g, '&quot;') + ')">' +
                '<img src="' + pickImageUrl + '" class="pick-thumb" onerror="this.onerror=null;this.src=\'' + getDefaultImage() + '\'">' +
                '<div class="pick-content"><h4>' + n.title + '</h4><span>' + translateCategory(n.category) + '</span></div></div>';
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
            // 檢查原始 category、雙語轉換後的 category，或 tags
            var catMatch = n.category === category || 
                          translateCategory(n.category) === category ||
                          n.category === category.split(' ')[0]; // 匹配中文部分
            var tagMatch = n.tags && n.tags.indexOf(category) !== -1;
            return catMatch || tagMatch;
        });
        updateDisplay(filtered);
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
        if (article.source_url || article.sourceUrl) {
            window.open(article.source_url || article.sourceUrl, '_blank');
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
