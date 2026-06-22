(function() {
  var app = document.getElementById('app');
  var S = { user: null, sec: 'masters', rating: 0, timer: null, cats: {}, searchQ: '' };

  var TABS = [
    { id: 'masters', l: 'Услуги', i: '🛠️' },
    { id: 'orders', l: 'Биржа', i: '📋' },
    { id: 'shops', l: 'Магазины', i: '🏪' },
    { id: 'jobs', l: 'Работа', i: '💼' },
    { id: 'guide', l: 'Справка', i: '❓' },
  ];

  function initVK() {
    return new Promise(function(resolve) {
      if (typeof VKBridge !== 'undefined') {
        VKBridge.send('VKWebAppInit')
          .then(function() { return VKBridge.send('VKWebAppGetUserInfo'); })
          .then(function(u) { S.user = { id: u.id, name: u.first_name + ' ' + u.last_name }; resolve(); })
          .catch(function() { S.user = { id: 0, name: 'Гость' }; resolve(); });
        return;
      }
      if (typeof VK !== 'undefined' || window.location.search.indexOf('vk_access_token') > -1 || document.referrer.indexOf('vk.com') > -1) {
        var s = document.createElement('script');
        s.src = 'https://unpkg.com/@vkontakte/vk-bridge@2.17.3/dist/vk-bridge.min.js';
        s.onload = function() {
          VKBridge.send('VKWebAppInit')
            .then(function() { return VKBridge.send('VKWebAppGetUserInfo'); })
            .then(function(u) { S.user = { id: u.id, name: u.first_name + ' ' + u.last_name }; resolve(); })
            .catch(function() { S.user = { id: 0, name: 'Гость' }; resolve(); });
        };
        s.onerror = function() { S.user = { id: 0, name: 'Тестер' }; resolve(); };
        document.head.appendChild(s);
        setTimeout(function() { S.user = S.user || { id: 0, name: 'Тестер' }; resolve(); }, 3000);
        return;
      }
      S.user = { id: 0, name: 'Тестер' };
      resolve();
    });
  }

  function esc(v) { return String(v || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function stars(n) { var f = Math.max(0, Math.min(5, Math.round(Number(n) || 0))); return '★'.repeat(f) + '☆'.repeat(5 - f); }
  function render(h) { app.innerHTML = h; }
  function toast(t) {
    var el = document.createElement('div');
    el.className = 'toast';
    el.textContent = t;
    document.body.appendChild(el);
    setTimeout(function() { el.remove(); }, 2500);
  }
  function go(h) {
    location.hash = h;
    route();
  }

  function hd(title, back) {
    return '<header class="hd"><div class="hd-inner">' +
      (back !== false ? '<button class="hd-back" onclick="APP.go(\'' + (back || 'masters') + '\')"><svg width="10" height="18" viewBox="0 0 10 18" fill="none"><path d="M9 1L1 9l8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' : '<div class="hd-spacer"></div>') +
      '<h1>' + esc(title) + '</h1><div class="hd-spacer"></div></div></header>';
  }

  function tb() {
    var html = '<nav class="tb">';
    for (var i = 0; i < TABS.length; i++) {
      var t = TABS[i];
      html += '<button class="tb-i ' + (S.sec === t.id ? 'on' : '') + '" onclick="APP.go(\'' + t.id + '\')">' +
        '<span class="tb-ic">' + t.i + '</span><span class="tb-l">' + t.l + '</span></button>';
    }
    html += '</nav>';
    return html;
  }

  function shell(title, back, content) {
    return '<div class="wrap">' + hd(title, back) + '<main class="ct">' + content + '</main>' + tb() + '</div>';
  }

  function skel() {
    return '<div class="wrap">' + hd('...') + '<main class="ct"><div class="sk"></div><div class="sk"></div><div class="sk"></div></main></div>';
  }

  function srch(sec, val, ph) {
    return '<div class="si"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8e8e93" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>' +
      '<input id="si-input" placeholder="' + (ph || 'Поиск...') + '" value="' + esc(val || '') + '" onkeydown="if(event.key===\'Enter\')APP.searchBtn(\'' + sec + '\')">' +
      '<button class="si-btn" onclick="APP.searchBtn(\'' + sec + '\')">Найти</button></div>';
  }

  function chips(cats, act, sec) {
    if (!cats || !cats.length) return '';
    var html = '<div class="ch"><button class="ci ' + (!act ? 'on' : '') + '" onclick="APP.flt(\'' + sec + '\',\'\')">Все</button>';
    for (var i = 0; i < cats.length; i++) {
      var c = cats[i];
      html += '<button class="ci ' + (String(act) === String(c.id) ? 'on' : '') + '" onclick="APP.flt(\'' + sec + '\',\'' + c.id + '\')">' + esc(c.name) + '</button>';
    }
    html += '</div>';
    return html;
  }

  function empty(t) { return '<div class="emp">' + (t || 'Пока пусто') + '</div>'; }

  function photoEl(photo, name, size) {
    size = size || 40;
    if (photo) {
      return '<img class="cd-photo" src="' + esc(photo) + '" alt="" style="width:' + size + 'px;height:' + size + 'px;border-radius:10px;object-fit:cover;flex-shrink:0">';
    }
    return '<div class="ca" style="width:' + size + 'px;height:' + size + 'px">' + esc((name || '?')[0]) + '</div>';
  }

  function cardC(item, onclick) {
    var v = item.verified ? '<span class="b v">✓</span>' : '';
    var r = item.votes_count > 0 ? '<span class="cr"><span class="st">' + stars(item.rating) + '</span> ' + item.rating + ' <em>' + item.votes_count + '</em></span>' : '';
    return '<button class="cd" onclick="' + onclick + '">' + photoEl(item.photo, item.name) + '<div class="ci2"><div class="ct2">' + esc(item.name) + v + '</div><div class="cs">' + esc((item.description || '').substring(0, 80)) + '</div><div class="cm">' + r + '</div></div><svg class="cw" width="8" height="14" viewBox="0 0 8 14" fill="none"><path d="M1 1l6 6-6 6" stroke="#c7c7cc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>';
  }

  function vipCard(item, onclick) {
    var v = item.verified ? '<span class="b v">✓</span>' : '';
    var r = item.votes_count > 0 ? '<span class="cr"><span class="st">' + stars(item.rating) + '</span> ' + item.rating + '</span>' : '';
    return '<button class="cd vip-card" onclick="' + onclick + '">' +
      (item.photo
        ? '<img class="cd-photo" src="' + esc(item.photo) + '" alt="" style="width:48px;height:48px;border-radius:12px;object-fit:cover;flex-shrink:0">'
        : '<div class="vip-avatar">' + esc((item.name || item.company_name || '?')[0]) + '</div>') +
      '<div class="ci2"><div class="ct2">' + esc(item.name || item.company_name) + v + '</div><div class="cs">' + esc((item.description || '').substring(0, 60)) + '</div><div class="cm">' + r + '</div></div></button>';
  }

  function shuffle(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
    return arr;
  }

  function vipSlider(title, items, onclickFn) {
    if (!items || !items.length) return '';
    var shuffled = shuffle(items.slice());
    var html = '';
    for (var i = 0; i < shuffled.length; i++) {
      html += vipCard(shuffled[i], onclickFn(shuffled[i]));
    }
    return '<div class="vip-section"><div class="vip-title">⭐ ' + esc(title) + '</div><div class="vip-scroll">' + html + '</div></div>';
  }

  function jobC(j) {
    return '<button class="cd" onclick="APP.openJob(' + j.id + ')"><div class="ca">💼</div><div class="ci2"><div class="ct2">' + esc(j.company_name) + '</div><div class="cs">' + esc((j.vacancy_text || j.description || '').substring(0, 100)) + '</div></div><svg class="cw" width="8" height="14" viewBox="0 0 8 14" fill="none"><path d="M1 1l6 6-6 6" stroke="#c7c7cc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>';
  }

  function revC(r) {
    return '<div class="rv"><div class="rv-h"><span class="rv-n">' + esc(r.user_name || 'Аноним') + '</span><span class="st">' + stars(r.rating) + '</span></div><p>' + esc(r.text) + '</p></div>';
  }

  function requisitesBlock() {
    var cards = [
      { bank: 'Сбербанк', number: '2202 2063 3271 2038' },
      { bank: 'Альфа', number: '2200 1545 3229 7719' },
      { bank: 'Озон', number: '2204 3210 8798 2542' },
    ];
    var html = '<div class="bl"><h3>Реквизиты</h3>';
    for (var i = 0; i < cards.length; i++) {
      html += '<div class="req-row"><span class="req-label">' + esc(cards[i].bank) + ':</span> ' +
        '<span class="req-num">' + esc(cards[i].number) + '</span>' +
        '<button class="req-copy" onclick="APP.copyNum(\'' + cards[i].number + '\', this)">Копировать</button></div>';
    }
    html += '</div>';
    return html;
  }

  function copyNum(num, btn) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(num.replace(/\s/g, '')).then(function() {
        if (btn) { btn.textContent = '✓ Скопировано'; setTimeout(function() { btn.textContent = 'Копировать'; }, 1500); }
        toast('Номер скопирован');
      });
    } else {
      var ta = document.createElement('textarea');
      ta.value = num.replace(/\s/g, '');
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      if (btn) { btn.textContent = '✓ Скопировано'; setTimeout(function() { btn.textContent = 'Копировать'; }, 1500); }
      toast('Номер скопирован');
    }
  }

  function setupPhotoPreview(inputId, previewId) {
    var input = document.getElementById(inputId);
    var preview = document.getElementById(previewId);
    if (!input || !preview) return;
    input.addEventListener('change', function() {
      var file = input.files[0];
      if (file) {
        var reader = new FileReader();
        reader.onload = function(e) {
          S._pendingPhoto = e.target.result;
          preview.innerHTML = '<img src="' + e.target.result + '" style="width:80px;height:80px;border-radius:10px;object-fit:cover">';
        };
        reader.readAsDataURL(file);
      } else {
        S._pendingPhoto = null;
        preview.innerHTML = '';
      }
    });
  }

  // ── MASTERS ──
  function showMasters(p) {
    p = p || {};
    S.sec = 'masters';
    S.searchQ = p.search || '';
    Promise.all([API.getMasterCategories(), API.getMasters(p), API.getRecommendedMasters()])
      .then(function(res) {
        var cats = res[0], data = res[1], vip = res[2];
        S.cats.masters = cats;
        var content = vipSlider('VIP Мастера', vip.items, function(item) { return 'APP.openM(' + item.id + ')'; });
        content += srch('masters', p.search, 'Найти мастера...');
        content += chips(cats, p.category_id, 'masters');
        var items = '';
        for (var i = 0; i < data.items.length; i++) {
          items += cardC(data.items[i], 'APP.openM(' + data.items[i].id + ')');
        }
        content += items ? '<div class="ls">' + items + '</div>' : empty();
        render(shell('Услуги', false, content));
      })
      .catch(function(e) { console.error(e); render(shell('Услуги', false, empty('Ошибка загрузки'))); });
  }

  function openM(id) {
    render(skel());
    Promise.all([API.getMaster(id), API.getMasterReviews(id)])
      .then(function(res) {
        var m = res[0], rv = res[1];
        var isOwner = S.user && S.user.id && m.owner_vk_id === S.user.id;
        var content = '<div class="pf">';
        if (m.photo) {
          content += '<img src="' + esc(m.photo) + '" alt="" style="width:80px;height:80px;border-radius:50%;object-fit:cover;margin:0 auto 10px;display:block">';
        } else {
          content += '<div class="pa">' + esc((m.name || '?')[0]) + '</div>';
        }
        content += '<h2>' + esc(m.name) + '</h2>';
        if (m.verified) content += '<span class="b v">✓ Проверенный</span>';
        content += '<div class="ps"><span class="st">' + stars(m.rating) + '</span><span>' + (m.rating || '—') + '</span><span>·</span><span>' + (m.votes_count || 0) + ' оценок</span><span>·</span><span>👁 ' + (m.views_count || 0) + '</span></div></div>';
        content += '<div class="bl"><h3>Описание</h3><p>' + esc(m.description || 'Нет описания') + '</p></div>';
        if (m.contacts) content += '<div class="bl"><h3>Контакты</h3><p class="ct3">' + esc(m.contacts) + '</p></div>';
        if (isOwner) content += '<div style="margin-top:10px"><button class="btn edit-btn" onclick="APP.editM(' + m.id + ')">Редактировать</button></div>';
        content += '<div class="bl"><h3>Отзывы (' + rv.length + ')</h3>';
        if (rv.length) { for (var i = 0; i < rv.length; i++) content += revC(rv[i]); }
        else content += '<p class="mt">Пока нет отзывов</p>';
        content += '</div><div class="bb"><button class="btn p" onclick="APP.rf(\'master\',' + m.id + ')">Оставить отзыв</button></div>';
        render(shell(m.name, 'masters', content));
      })
      .catch(function(e) { console.error(e); render(shell('Ошибка', 'masters', empty('Не найден'))); });
  }

  // ── EDIT MASTER ──
  function editM(id) {
    render(skel());
    Promise.all([API.getMaster(id), API.getMasterCategories()])
      .then(function(res) {
        var m = res[0], cats = res[1];
        var opts = '<option value="">Без категории</option>';
        for (var i = 0; i < cats.length; i++) {
          opts += '<option value="' + cats[i].id + '"' + (m.category_id == cats[i].id ? ' selected' : '') + '>' + esc(cats[i].name) + '</option>';
        }
        var content = '<div class="fm">' +
          '<label>Название</label><input id="em-name" value="' + esc(m.name) + '">' +
          '<label>Описание</label><textarea id="em-desc" rows="3">' + esc(m.description) + '</textarea>' +
          '<label>Контакты</label><input id="em-contacts" value="' + esc(m.contacts) + '">' +
          '<label>Категория</label><select id="em-cat">' + opts + '</select>' +
          '<label>Фото</label><input type="file" id="em-photo" accept="image/*" class="fm-file">' +
          '<div id="em-photo-preview" class="photo-preview">' + (m.photo ? '<img src="' + esc(m.photo) + '" style="width:80px;height:80px;border-radius:10px;object-fit:cover">' : '') + '</div>' +
          '<button class="btn p" onclick="APP.saveM(' + id + ')">Сохранить</button></div>';
        S._pendingPhoto = m.photo || null;
        render(shell('Редактирование', 'performers', content));
        setupPhotoPreview('em-photo', 'em-photo-preview');
      });
  }

  function saveM(id) {
    var body = {
      owner_vk_id: S.user.id,
      name: document.getElementById('em-name').value.trim(),
      description: document.getElementById('em-desc').value.trim(),
      contacts: document.getElementById('em-contacts').value.trim(),
      photo: S._pendingPhoto || '',
      category_id: document.getElementById('em-cat').value ? Number(document.getElementById('em-cat').value) : null,
    };
    S._pendingPhoto = null;
    if (!body.name) return toast('Введите название');
    API.updateMaster(id, body).then(function() {
      toast('Сохранено!'); openM(id);
    }).catch(function() { toast('Ошибка'); });
  }

  // ── SHOPS ──
  function showShops(p) {
    p = p || {};
    S.sec = 'shops';
    Promise.all([API.getShopCategories(), API.getShops(Object.assign({ shop_type: 'shop' }, p)), API.getShops(Object.assign({ shop_type: 'food' }, p)), API.getRecommendedShops({ shop_type: 'shop' })])
      .then(function(res) {
        var cats = res[0], shopData = res[1], foodData = res[2], vip = res[3];
        S.cats.shops = cats;
        var content = vipSlider('VIP Магазины', vip.items, function(item) { return 'APP.openS(' + item.id + ',\'shop\')'; });
        content += srch('shops', p.search, 'Найти магазин...');
        content += '<div class="ch"><button class="ci ' + (!p.shop_type ? 'on' : '') + '" onclick="APP.shopTab(\'\')">Все</button>' +
          '<button class="ci ' + (p.shop_type === 'shop' ? 'on' : '') + '" onclick="APP.shopTab(\'shop\')">🏪 Магазины</button>' +
          '<button class="ci ' + (p.shop_type === 'food' ? 'on' : '') + '" onclick="APP.shopTab(\'food\')">🍔 Доставка</button></div>';
        if (!p.shop_type || p.shop_type === 'shop') {
          content += '<h3 style="margin-top:10px;font-size:15px">🏪 Магазины</h3><div class="ls">';
          for (var i = 0; i < shopData.items.length; i++) {
            content += cardC(shopData.items[i], 'APP.openS(' + shopData.items[i].id + ',\'shop\')');
          }
          content += '</div>';
        }
        if (!p.shop_type || p.shop_type === 'food') {
          content += '<h3 style="margin-top:10px;font-size:15px">🍔 Доставка</h3><div class="ls">';
          for (var i = 0; i < foodData.items.length; i++) {
            content += cardC(foodData.items[i], 'APP.openS(' + foodData.items[i].id + ',\'food\')');
          }
          content += '</div>';
        }
        render(shell('Магазины', false, content));
      })
      .catch(function(e) { console.error(e); render(shell('Магазины', false, empty('Ошибка'))); });
  }

  function shopTab(type) {
    showShops(type ? { shop_type: type } : {});
  }

  // ── FOOD ──
  function showFood(p) {
    p = p || {};
    S.sec = 'food';
    Promise.all([API.getFoodCategories(), API.getShops(Object.assign({ shop_type: 'food' }, p)), API.getRecommendedShops({ shop_type: 'food' })])
      .then(function(res) {
        var cats = res[0], data = res[1], vip = res[2];
        S.cats.food = cats;
        var content = vipSlider('VIP Доставка', vip.items, function(item) { return 'APP.openS(' + item.id + ',\'food\')'; });
        content += srch('food', p.search, 'Найти доставку...');
        content += chips(cats, p.category_id, 'food');
        var items = '';
        for (var i = 0; i < data.items.length; i++) {
          items += cardC(data.items[i], 'APP.openS(' + data.items[i].id + ',\'food\')');
        }
        content += items ? '<div class="ls">' + items + '</div>' : empty();
        render(shell('Доставка еды', false, content));
      })
      .catch(function(e) { console.error(e); render(shell('Доставка', false, empty('Ошибка'))); });
  }

  function openS(id, type) {
    render(skel());
    var bk = type === 'food' ? 'food' : 'shops';
    Promise.all([API.getShop(id), API.getShopReviews(id)])
      .then(function(res) {
        var s = res[0], rv = res[1];
        var isOwner = S.user && S.user.id && s.owner_vk_id === S.user.id;
        var content = '<div class="pf">';
        if (s.photo) {
          content += '<img src="' + esc(s.photo) + '" alt="" style="width:80px;height:80px;border-radius:50%;object-fit:cover;margin:0 auto 10px;display:block">';
        } else {
          content += '<div class="pa">' + esc((s.name || '?')[0]) + '</div>';
        }
        content += '<h2>' + esc(s.name) + '</h2>';
        if (s.verified) content += '<span class="b v">✓ Проверен</span>';
        content += '<div class="ps"><span class="st">' + stars(s.rating) + '</span><span>' + (s.rating || '—') + '</span><span>·</span><span>' + (s.votes_count || 0) + ' оценок</span></div></div>';
        content += '<div class="bl"><h3>Описание</h3><p>' + esc(s.description || '') + '</p></div>';
        if (s.contacts) content += '<div class="bl"><h3>Контакты</h3><p class="ct3">' + esc(s.contacts) + '</p></div>';
        if (isOwner) content += '<div style="margin-top:10px"><button class="btn edit-btn" onclick="APP.editS(' + id + ',\'' + type + '\')">Редактировать</button></div>';
        content += '<div class="bl"><h3>Отзывы (' + rv.length + ')</h3>';
        if (rv.length) { for (var i = 0; i < rv.length; i++) content += revC(rv[i]); }
        else content += '<p class="mt">Пока нет отзывов</p>';
        content += '</div><div class="bb"><button class="btn p" onclick="APP.rf(\'' + type + '\',' + s.id + ')">Оставить отзыв</button></div>';
        render(shell(s.name, bk, content));
      })
      .catch(function(e) { console.error(e); render(shell('Ошибка', bk, empty('Не найдено'))); });
  }

  function editS(id, type) {
    render(skel());
    Promise.all([API.getShop(id), API.getShopCategories()])
      .then(function(res) {
        var s = res[0], cats = res[1];
        var opts = '<option value="">Без категории</option>';
        for (var i = 0; i < cats.length; i++) {
          opts += '<option value="' + cats[i].id + '"' + (s.category_id == cats[i].id ? ' selected' : '') + '>' + esc(cats[i].name) + '</option>';
        }
        var content = '<div class="fm">' +
          '<label>Название</label><input id="es-name" value="' + esc(s.name) + '">' +
          '<label>Описание</label><textarea id="es-desc" rows="3">' + esc(s.description) + '</textarea>' +
          '<label>Контакты</label><input id="es-contacts" value="' + esc(s.contacts) + '">' +
          '<label>Категория</label><select id="es-cat">' + opts + '</select>' +
          '<label>Фото</label><input type="file" id="es-photo" accept="image/*" class="fm-file">' +
          '<div id="es-photo-preview" class="photo-preview">' + (s.photo ? '<img src="' + esc(s.photo) + '" style="width:80px;height:80px;border-radius:10px;object-fit:cover">' : '') + '</div>' +
          '<button class="btn p" onclick="APP.saveS(' + id + ',\'' + type + '\')">Сохранить</button></div>';
        S._pendingPhoto = s.photo || null;
        render(shell('Редактирование', 'performers', content));
        setupPhotoPreview('es-photo', 'es-photo-preview');
      });
  }

  function saveS(id, type) {
    var body = {
      owner_vk_id: S.user.id,
      name: document.getElementById('es-name').value.trim(),
      description: document.getElementById('es-desc').value.trim(),
      contacts: document.getElementById('es-contacts').value.trim(),
      photo: S._pendingPhoto || '',
      category_id: document.getElementById('es-cat').value ? Number(document.getElementById('es-cat').value) : null,
    };
    S._pendingPhoto = null;
    if (!body.name) return toast('Введите название');
    API.updateShop(id, body).then(function() {
      toast('Сохранено!'); openS(id, type);
    }).catch(function() { toast('Ошибка'); });
  }

  // ── JOBS ──
  function showJobs(p) {
    p = p || {};
    S.sec = 'jobs';
    Promise.all([API.getEmployers(p.search ? { search: p.search } : { page: 1 }), API.getRecommendedEmployers()])
      .then(function(res) {
        var data = res[0], vip = res[1];
        var content = vipSlider('VIP Работодатели', vip.items, function(item) { return 'APP.openJob(' + item.id + ')'; });
        content += srch('jobs', p.search, 'Найти вакансию...');
        var items = '';
        for (var i = 0; i < data.items.length; i++) {
          items += jobC(data.items[i]);
        }
        content += items ? '<div class="ls">' + items + '</div>' : empty();
        render(shell('Работа', false, content));
      })
      .catch(function(e) { console.error(e); render(shell('Работа', false, empty('Ошибка'))); });
  }

  function openJob(id) {
    render(skel());
    API.getEmployer(id)
      .then(function(e) {
        var isOwner = S.user && S.user.id && e.user_id === S.user.id;
        var contacts = [e.phone, e.vk_page, e.contacts].filter(Boolean).join('\n');
        var content = '';
        if (e.photo) content += '<div style="text-align:center;margin-top:12px"><img src="' + esc(e.photo) + '" style="width:80px;height:80px;border-radius:50%;object-fit:cover"></div>';
        content += '<div class="bl"><h3>Компания</h3><p>' + esc(e.description || '') + '</p></div>' +
          '<div class="bl"><h3>Вакансия</h3><p>' + esc(e.vacancy_text || '') + '</p></div>' +
          '<div class="bl"><h3>Контакты</h3><p class="ct3">' + esc(contacts) + '</p></div>';
        if (isOwner) content += '<div style="margin-top:10px"><button class="btn edit-btn" onclick="APP.editE(' + id + ')">Редактировать</button></div>';
        render(shell(e.company_name, 'jobs', content));
      })
      .catch(function(e) { console.error(e); render(shell('Ошибка', 'jobs', empty('Не найдено'))); });
  }

  function editE(id) {
    render(skel());
    API.getEmployer(id)
      .then(function(e) {
        var content = '<div class="fm">' +
          '<label>Описание компании</label><textarea id="ee-desc" rows="2">' + esc(e.description) + '</textarea>' +
          '<label>Телефон</label><input id="ee-phone" value="' + esc(e.phone) + '">' +
          '<label>VK</label><input id="ee-vk" value="' + esc(e.vk_page) + '">' +
          '<label>Контакты</label><input id="ee-contacts" value="' + esc(e.contacts) + '">' +
          '<label>Текст вакансии</label><textarea id="ee-vacancy" rows="4">' + esc(e.vacancy_text) + '</textarea>' +
          '<label>Фото</label><input type="file" id="ee-photo" accept="image/*" class="fm-file">' +
          '<div id="ee-photo-preview" class="photo-preview">' + (e.photo ? '<img src="' + esc(e.photo) + '" style="width:80px;height:80px;border-radius:10px;object-fit:cover">' : '') + '</div>' +
          '<button class="btn p" onclick="APP.saveE(' + id + ')">Сохранить</button></div>';
        S._pendingPhoto = e.photo || null;
        render(shell('Редактирование', 'performers', content));
        setupPhotoPreview('ee-photo', 'ee-photo-preview');
      });
  }

  function saveE(id) {
    var body = {
      user_id: S.user.id,
      description: document.getElementById('ee-desc').value.trim(),
      phone: document.getElementById('ee-phone').value.trim(),
      vk_page: document.getElementById('ee-vk').value.trim(),
      contacts: document.getElementById('ee-contacts').value.trim(),
      vacancy_text: document.getElementById('ee-vacancy').value.trim(),
      photo: S._pendingPhoto || '',
    };
    S._pendingPhoto = null;
    API.updateEmployer(id, body).then(function() {
      toast('Сохранено!'); openJob(id);
    }).catch(function() { toast('Ошибка'); });
  }

  // ── MORE ──
  function showMore() {
    S.sec = 'more';
    var content = '<div class="mn">' +
      '<button class="mi" onclick="APP.go(\'ads\')"><span>📢</span><div><b>Реклама</b><p>Размещение объявлений</p></div></button>' +
      '<button class="mi" onclick="APP.go(\'performers\')"><span>🔧</span><div><b>Исполнителям</b><p>Регистрация мастеров, магазинов, доставки</p></div></button>' +
      '<button class="mi" onclick="APP.go(\'admin\')"><span>💬</span><div><b>Написать админу</b><p>Связаться с администрацией</p></div></button>' +
      '</div>';
    render(shell('Ещё', false, content));
  }

  // ── FAQ ──
  function showGuide(p) {
    p = p || {};
    S.sec = 'guide';
    Promise.all([API.getFaqCategories(), API.getFaq(p.search ? { search: p.search } : (p.category_id ? { category_id: p.category_id } : {}))])
      .then(function(res) {
        var cats = res[0], faq = res[1];
        S.cats.guide = cats;
        var items = '';
        for (var i = 0; i < faq.length; i++) {
          items += '<div class="fq"><details><summary>' + esc(faq[i].question) + '</summary><p>' + esc(faq[i].answer) + '</p></details></div>';
        }
        var content = srch('guide', p.search, 'Найти ответ...') + chips(cats, p.category_id, 'guide') + (items || empty());
        content += '<div class="bl" style="margin-top:16px"><h3>Ещё</h3>' +
          '<div class="mn">' +
          (S.user && S.user.id ? '<button class="mi" onclick="APP.showMyItems()"><span>👤</span><div><b>Мой кабинет</b><p>Мои записи и редактирование</p></div></button>' : '') +
          '<button class="mi" onclick="APP.go(\'ads\')"><span>📢</span><div><b>Реклама</b><p>Размещение объявлений</p></div></button>' +
          '<button class="mi" onclick="APP.go(\'performers\')"><span>🔧</span><div><b>Исполнителям</b><p>Регистрация мастеров, магазинов</p></div></button>' +
          '<button class="mi" onclick="APP.go(\'admin\')"><span>💬</span><div><b>Админу</b><p>Связаться с администрацией</p></div></button>' +
          '</div></div>';
        render(shell('Справочник', false, content));
      })
      .catch(function(e) { console.error(e); render(shell('Справочник', false, empty('Ошибка'))); });
  }

  // ── ADS ──
  function showAds() {
    S.sec = 'ads';
    var content = '<div class="info"><b>Реклама в сообществе</b><p>Выберите формат размещения</p></div>' +
      '<div class="at">' +
      '<button class="ab" onclick="APP.submitAd(\'Обычное объявление — 250 ₽\')"><div class="ap">250 ₽</div><div class="at2">Обычное объявление</div><div class="ad">Пост в обсуждениях</div></button>' +
      '<button class="ab" onclick="APP.submitAd(\'Репост из сообщества — 300 ₽\')"><div class="ap">300 ₽</div><div class="at2">Репост из сообщества</div><div class="ad">С переходом трафика</div></button>' +
      '<button class="ab" onclick="APP.submitAd(\'Объявление со ссылкой — 400 ₽\')"><div class="ap">400 ₽</div><div class="at2">Ссылка на TG/сайт</div><div class="ad">Внешние ссылки</div></button>' +
      '<button class="ab" onclick="APP.submitAd(\'Реклама в сторис (24ч) — 400 ₽\')"><div class="ap">400 ₽</div><div class="at2">Сторис на 24 часа</div><div class="ad">Фото/видео + кнопка</div></button>' +
      '<button class="ab" onclick="APP.submitAd(\'Сторис + пост — 550 ₽\')"><div class="ap">550 ₽</div><div class="at2">Сторис + Пост</div><div class="ad">Комбо, выгоднее!</div></button>' +
      '</div>' +
      requisitesBlock() +
      '<p class="mt">После оплаты пришлите скриншот чека. НПД, выставляем счёт.</p>';
    render(shell('Реклама', 'guide', content));
  }

  function submitAd(type) {
    render(shell('Заявка', 'ads',
      '<div class="info"><b>' + esc(type) + '</b><p>Напишите, что хотите разместить — мы отправим на согласование администратору</p></div>' +
      requisitesBlock() +
      '<div class="fm"><label>Текст объявления</label><textarea id="ad-t" rows="5" placeholder="Что разместить?"></textarea>' +
      '<button class="btn p" onclick="APP.sendAd()">Отправить заявку</button></div>'));
    S._adType = type;
  }

  function sendAd() {
    var t = document.getElementById('ad-t').value.trim();
    if (!t) return toast('Напишите текст');
    API.submitMessage({ user_id: S.user ? S.user.id : 0, user_name: S.user ? S.user.name : '', message_text: '[' + S._adType + '] ' + t, message_type: 'ad' })
      .then(function() { toast('Заявка отправлена!'); go('ads'); })
      .catch(function() { toast('Ошибка'); });
  }

  // ── PERFORMERS ──
  function showPerformers() {
    S.sec = 'performers';
    var content = '<div class="info"><b>Для исполнителей</b><p>Раздел для частных мастеров, магазинов и служб доставки. Зарегистрируйтесь, чтобы появиться в каталоге.</p></div>' +
      '<div class="pg">' +
      '<button class="pc" onclick="APP.regF(\'master\')"><div class="pi">✂️</div><b>Мастер</b><p>Маникюр, ремонт, фото</p></button>' +
      '<button class="pc" onclick="APP.regF(\'shop\')"><div class="pi">🏪</div><b>Магазин</b><p>Товары, одежда, услуги</p></button>' +
      '<button class="pc" onclick="APP.regF(\'food\')"><div class="pi">🍕</div><b>Доставка</b><p>Пицца, суши, бургеры</p></button>' +
      '<button class="pc" onclick="APP.empF()"><div class="pi">💼</div><b>Работодатель</b><p>Разместить вакансию</p></button>' +
      '</div>';
    if (S.user && S.user.id) {
      content += '<div class="bl" style="margin-top:12px"><h3>👤 Мой кабинет</h3><p style="font-size:13px;color:var(--sub);margin-bottom:8px">Просматривайте и редактируйте ваши записи</p>' +
        '<button class="btn p" onclick="APP.showMyItems()" style="font-size:14px;padding:10px">Открыть кабинет</button></div>';
    }
    content += '<div class="bb"><button class="btn p" onclick="APP.regF(\'master\')">Зарегистрироваться</button></div>';
    render(shell('Исполнителям', 'guide', content));
  }

  function showMyItems() {
    if (!S.user || !S.user.id) return toast('Войдите через VK');
    render(skel());
    API.getMyItems(S.user.id).then(function(data) {
      var content = '';
      if (data.masters.length) {
        content += '<div class="bl"><h3>Мои мастера</h3>';
        for (var i = 0; i < data.masters.length; i++) {
          var m = data.masters[i];
          content += '<div class="ob-card" style="cursor:default">' +
            '<div class="ob-card-cat">' + esc(m.name) + '</div>' +
            '<div class="ob-card-desc">' + esc((m.description || '').substring(0, 80)) + '</div>' +
            '<div style="display:flex;gap:6px;margin-top:6px">' +
            '<button class="req-copy" onclick="APP.openM(' + m.id + ')">👁 Смотреть</button>' +
            '<button class="req-copy" style="background:var(--orange)" onclick="APP.editM(' + m.id + ')">✏️ Редактировать</button>' +
            '</div></div>';
        }
        content += '</div>';
      }
      if (data.shops.length) {
        content += '<div class="bl"><h3>Мои магазины / доставка</h3>';
        for (var i = 0; i < data.shops.length; i++) {
          var s = data.shops[i];
          content += '<div class="ob-card" style="cursor:default">' +
            '<div class="ob-card-cat">' + esc(s.name) + ' <span class="b" style="background:#8e8e93;color:#fff">' + esc(s.shop_type) + '</span></div>' +
            '<div class="ob-card-desc">' + esc((s.description || '').substring(0, 80)) + '</div>' +
            '<div style="display:flex;gap:6px;margin-top:6px">' +
            '<button class="req-copy" onclick="APP.openS(' + s.id + ',\'' + s.shop_type + '\')">👁 Смотреть</button>' +
            '<button class="req-copy" style="background:var(--orange)" onclick="APP.editS(' + s.id + ',\'' + s.shop_type + '\')">✏️ Редактировать</button>' +
            '</div></div>';
        }
        content += '</div>';
      }
      if (data.employers.length) {
        content += '<div class="bl"><h3>Мои вакансии</h3>';
        for (var i = 0; i < data.employers.length; i++) {
          var e = data.employers[i];
          content += '<div class="ob-card" style="cursor:default">' +
            '<div class="ob-card-cat">' + esc(e.company_name) + '</div>' +
            '<div class="ob-card-desc">' + esc((e.vacancy_text || e.description || '').substring(0, 80)) + '</div>' +
            '<div style="display:flex;gap:6px;margin-top:6px">' +
            '<button class="req-copy" onclick="APP.openJob(' + e.id + ')">👁 Смотреть</button>' +
            '<button class="req-copy" style="background:var(--orange)" onclick="APP.editE(' + e.id + ')">✏️ Редактировать</button>' +
            '</div></div>';
        }
        content += '</div>';
      }
      if (!content) content = empty('У вас пока нет записей. Зарегистрируйтесь как исполнитель.');
      render(shell('Мой кабинет', 'performers', content));
    }).catch(function() { render(shell('Мой кабинет', 'performers', empty('Ошибка'))); });
  }

  function regF(type) {
    var titles = { master: 'Мастер', shop: 'Магазин', food: 'Доставка' };
    var catPromise = type === 'master' ? API.getMasterCategories() : (type === 'food' ? API.getFoodCategories() : API.getShopCategories());
    catPromise.then(function(cats) {
      var opts = '<option value="">Без категории</option>';
      for (var i = 0; i < cats.length; i++) {
        opts += '<option value="' + cats[i].id + '">' + esc(cats[i].name) + '</option>';
      }
      render(shell('Регистрация: ' + titles[type], 'performers',
        '<div class="fm"><label>Название</label><input id="rn" placeholder="' + (type === 'master' ? 'Иван — Мастер маникюра' : 'Название') + '">' +
        '<label>Описание</label><textarea id="rd" rows="3" placeholder="Опишите услуги"></textarea>' +
        '<label>Контакты</label><input id="rc" placeholder="Телефон, @username">' +
        '<label>Категория</label><select id="rca">' + opts + '</select>' +
        '<label>Фото</label><input type="file" id="rphoto" accept="image/*" class="fm-file">' +
        '<div id="rphoto-preview" class="photo-preview"></div>' +
        '<button class="btn p" onclick="APP.sendR(\'' + type + '\')">Отправить</button></div>'));
      setupPhotoPreview('rphoto', 'rphoto-preview');
    });
  }

  function sendR(type) {
    var body = {
      user_id: S.user ? S.user.id : 0,
      user_name: S.user ? S.user.name : '',
      name: document.getElementById('rn').value.trim(),
      description: document.getElementById('rd').value.trim(),
      contacts: document.getElementById('rc').value.trim(),
      category_id: document.getElementById('rca').value ? Number(document.getElementById('rca').value) : null,
      photo: S._pendingPhoto || '',
    };
    S._pendingPhoto = null;
    if (!body.name || !body.contacts) return toast('Заполните обязательные поля');
    var p = type === 'master' ? API.registerMaster(body) : API.registerShop(Object.assign({ shop_type: type }, body));
    p.then(function() { toast('Заявка отправлена!'); go('performers'); })
      .catch(function() { toast('Ошибка'); });
  }

  function empF() {
    render(shell('Вакансия', 'performers',
      '<div class="fm"><label>Компания</label><input id="ec">' +
      '<label>Описание</label><textarea id="ed" rows="2"></textarea>' +
      '<label>Телефон</label><input id="ep">' +
      '<label>VK</label><input id="ev">' +
      '<label>Контакты</label><input id="ecc">' +
      '<label>Текст вакансии</label><textarea id="evc" rows="4"></textarea>' +
      '<label>Фото</label><input type="file" id="ephoto" accept="image/*" class="fm-file">' +
      '<div id="ephoto-preview" class="photo-preview"></div>' +
      '<button class="btn p" onclick="APP.sendEmp()">Отправить</button></div>'));
    setupPhotoPreview('ephoto', 'ephoto-preview');
  }

  function sendEmp() {
    var c = document.getElementById('ec').value.trim();
    var v = document.getElementById('evc').value.trim();
    if (!c || !v) return toast('Заполните компанию и вакансию');
    API.registerEmployer({
      user_id: S.user ? S.user.id : 0, user_name: S.user ? S.user.name : '',
      company_name: c, description: document.getElementById('ed').value.trim(),
      phone: document.getElementById('ep').value.trim(), vk_page: document.getElementById('ev').value.trim(),
      contacts: document.getElementById('ecc').value.trim(), vacancy_text: v,
      photo: S._pendingPhoto || '',
    }).then(function() { S._pendingPhoto = null; toast('Заявка отправлена!'); go('jobs'); }).catch(function() { toast('Ошибка'); });
  }

  // ── ADMIN ──
  function showAdmin() {
    S.sec = 'admin';
    render(shell('Админу', 'guide',
      '<div class="info"><b>Написать админу</b><p>Ваше сообщение будет передано</p></div>' +
      '<div class="fm"><label>Сообщение</label><textarea id="am" rows="5" placeholder="Ваш вопрос..."></textarea>' +
      '<button class="btn p" onclick="APP.sendA()">Отправить</button></div>'));
  }

  function sendA() {
    var t = document.getElementById('am').value.trim();
    if (!t) return toast('Напишите сообщение');
    API.submitMessage({ user_id: S.user ? S.user.id : 0, user_name: S.user ? S.user.name : '', message_text: t, message_type: 'contact' })
      .then(function() { toast('Отправлено!'); go('guide'); })
      .catch(function() { toast('Ошибка'); });
  }

  // ── REVIEWS ──
  function rf(type, id) {
    S.rating = 0;
    var bk = type === 'master' ? 'masters' : (type === 'food' ? 'food' : 'shops');
    var ratingBtns = '';
    for (var n = 1; n <= 5; n++) {
      ratingBtns += '<button class="rb" data-r="' + n + '" onclick="APP.sr(' + n + ')">' + n + '★</button>';
    }
    render(shell('Отзыв', bk,
      '<div class="fm"><label>Оценка</label><div class="rt">' + ratingBtns + '</div>' +
      '<label>Имя</label><input id="rwn" value="' + esc(S.user ? S.user.name : '') + '" placeholder="Как зовут?">' +
      '<label>Отзыв</label><textarea id="rwt" rows="4" placeholder="Расскажите..."></textarea>' +
      '<button class="btn p" onclick="APP.sendRev(\'' + type + '\',' + id + ')">Отправить</button></div>'));
  }

  function sr(n) {
    S.rating = n;
    var btns = document.querySelectorAll('.rb');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle('on', Number(btns[i].getAttribute('data-r')) <= n);
    }
  }

  function sendRev(type, id) {
    var n = document.getElementById('rwn').value.trim();
    var t = document.getElementById('rwt').value.trim();
    if (!S.rating || !n || !t) return toast('Заполните все поля');
    var p;
    if (type === 'master') {
      p = API.createReview({ master_id: id, user_id: S.user ? S.user.id : 0, user_name: n, text: t, rating: S.rating });
    } else {
      p = API.createShopReview({ shop_id: id, user_id: S.user ? S.user.id : 0, user_name: n, text: t, rating: S.rating, target_type: type === 'food' ? 'food' : 'shop' });
    }
    p.then(function() { toast('На модерации!'); type === 'master' ? openM(id) : openS(id, type); })
      .catch(function() { toast('Ошибка'); });
  }

  // ── ORDER BOARD ──
  var ORDER_STATUSES = { new: 'Новая', has_responses: 'Есть отклики', in_progress: 'В работе', completed: 'Выполнена', cancelled: 'Отменена', expired: 'Истекла' };
  var URGENCY_COLORS = { 'Срочно, сегодня': '#ff3b30', 'В ближайшие дни': '#ff9500', 'Не срочно': '#34c759', 'По договорённости': '#007aff' };

  function orderStatusBadge(s) {
    var colors = { new: '#007aff', has_responses: '#ff9500', in_progress: '#5856d6', completed: '#34c759', cancelled: '#ff3b30', expired: '#8e8e93' };
    return '<span style="display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600;color:#fff;background:' + (colors[s] || '#8e8e93') + '">' + esc(ORDER_STATUSES[s] || s) + '</span>';
  }

  function urgencyBadge(u) {
    return '<span style="display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600;color:#fff;background:' + (URGENCY_COLORS[u] || '#8e8e93') + '">' + esc(u) + '</span>';
  }

  function showOrders() {
    S.sec = 'orders';
    var isPerformer = S._isPerformer;
    var content = '<div class="info"><b>Биржа заявок</b><p>Найдите исполнителя или откликнитесь на заявку</p></div>' +
      '<div class="ob-grid">' +
      '<button class="ob-btn" onclick="APP.orderCreateF()"><div class="ob-icon">📝</div><b>Создать заявку</b><p>Найти исполнителя</p></button>' +
      '<button class="ob-btn" onclick="APP.orderList()"><div class="ob-icon">📋</div><b>Заявки</b><p>Активные заявки</p></button>' +
      '<button class="ob-btn" onclick="APP.orderMy()"><div class="ob-icon">📂</div><b>Мои заявки</b><p>Управление заявками</p></button>';
    if (isPerformer) {
      content += '<button class="ob-btn ob-perf" onclick="APP.orderPerfCabinet()"><div class="ob-icon">👤</div><b>Кабинет</b><p>Профиль исполнителя</p></button>' +
        '<button class="ob-btn ob-perf" onclick="APP.orderPerfResponses()"><div class="ob-icon">📨</div><b>Мои отклики</b><p>Отклики и заявки</p></button>';
    }
    content += '</div>';
    if (!isPerformer) {
      content += '<div class="bl" style="margin-top:12px;text-align:center"><button class="btn edit-btn" onclick="APP.orderPerfReg()" style="font-size:14px">Стать исполнителем</button></div>';
    }
    render(shell('Биржа', false, content));
  }

  function orderCreateF() {
    if (!S.user || !S.user.id) return toast('Войдите через VK');
    Promise.all([API.getOrderCategories(), API.getUrgencyOptions()])
      .then(function(res) {
        var cats = res[0], urg = res[1];
        var catOpts = '';
        for (var i = 0; i < cats.length; i++) {
          catOpts += '<option value="' + cats[i].id + '">' + esc(cats[i].name) + '</option>';
        }
        var urgOpts = '';
        for (var i = 0; i < urg.length; i++) {
          urgOpts += '<option value="' + esc(urg[i]) + '">' + esc(urg[i]) + '</option>';
        }
        render(shell('Новая заявка', 'orders',
          '<div class="fm"><label>Категория *</label><select id="ob-cat">' + catOpts + '</select>' +
          '<label>Описание задачи *</label><textarea id="ob-desc" rows="4" placeholder="Опишите, что нужно сделать"></textarea>' +
          '<label>Срочность</label><select id="ob-urg">' + urgOpts + '</select>' +
          '<label>Адрес / район</label><input id="ob-addr" placeholder="ул. Примерная, д. 1">' +
          '<label>Контакт *</label><input id="ob-contact" placeholder="Телефон или @username">' +
          '<label>Желаемое время</label><input id="ob-time" placeholder="Например: сегодня после 18:00">' +
          '<label>Комментарий</label><textarea id="ob-comment" rows="2" placeholder="Дополнительная информация"></textarea>' +
          '<button class="btn p" onclick="APP.orderSend()">Отправить заявку</button></div>'));
      });
  }

  function orderSend() {
    var cat = document.getElementById('ob-cat').value;
    var desc = document.getElementById('ob-desc').value.trim();
    var contact = document.getElementById('ob-contact').value.trim();
    if (!desc || !contact) return toast('Заполните описание и контакт');
    API.createOrder({
      user_vk_id: S.user.id, user_name: S.user.name,
      category_id: Number(cat), description: desc,
      urgency: document.getElementById('ob-urg').value,
      address: document.getElementById('ob-addr').value.trim(),
      contact: contact, photo_url: '',
      desired_time: document.getElementById('ob-time').value.trim(),
      comment: document.getElementById('ob-comment').value.trim(),
    }).then(function(r) {
      if (r.id) { toast('Заявка #' + r.id + ' создана!'); go('orders'); }
    }).catch(function(e) { toast(e.message || 'Ошибка'); });
  }

  function orderList(p) {
    p = p || {};
    S.sec = 'orders';
    API.getOrderCategories().then(function(cats) {
      S._orderCats = cats;
      API.getOrders(p).then(function(data) {
        var catFilter = '<div class="ch"><button class="ci ' + (!p.category_id ? 'on' : '') + '" onclick="APP.orderList()">Все</button>';
        for (var i = 0; i < cats.length; i++) {
          catFilter += '<button class="ci ' + (p.category_id == cats[i].id ? 'on' : '') + '" onclick="APP.orderList({category_id:' + cats[i].id + '})">' + esc(cats[i].name) + '</button>';
        }
        catFilter += '</div>';
        var items = '';
        for (var i = 0; i < data.items.length; i++) {
          var o = data.items[i];
          items += '<div class="ob-card" onclick="APP.orderOpen(' + o.id + ')">' +
            '<div class="ob-card-top">' + orderStatusBadge(o.status) + urgencyBadge(o.urgency) + '</div>' +
            '<div class="ob-card-cat">' + esc(o.category) + '</div>' +
            '<div class="ob-card-desc">' + esc(o.description) + '</div>' +
            '<div class="ob-card-bottom"><span>📍 ' + esc(o.address || 'не указан') + '</span><span>💬 ' + o.responses_count + '</span></div>' +
            '<div class="ob-card-date">' + esc(o.created_at) + '</div></div>';
        }
        render(shell('Заявки', 'orders', catFilter + (items ? '<div class="ls">' + items + '</div>' : empty('Нет активных заявок'))));
      });
    });
  }

  function orderOpen(id) {
    render(skel());
    API.getOrder(id).then(function(o) {
      var isOwner = S.user && S.user.id === o.user_vk_id;
      var isPerformer = S._isPerformer && S._performerProfile;
      var hasResponded = false;
      if (isPerformer) {
        for (var i = 0; i < (o.responses || []).length; i++) {
          if (o.responses[i].performer_id === S._performerProfile.id) { hasResponded = true; break; }
        }
      }
      var content = '<div class="ob-detail">' +
        '<div class="ob-detail-top">' + orderStatusBadge(o.status) + urgencyBadge(o.urgency) + '</div>' +
        '<h2 style="margin-top:8px">' + esc(o.category) + '</h2>' +
        '<div class="bl"><h3>Описание</h3><p>' + esc(o.description) + '</p></div>' +
        '<div class="bl"><h3>Детали</h3><p>📍 ' + esc(o.address || 'не указан') + '</p><p>🕐 ' + esc(o.desired_time || 'по договорённости') + '</p><p>📞 ' + esc(o.contact) + '</p></div>';
      if (o.comment) content += '<div class="bl"><h3>Комментарий</h3><p>' + esc(o.comment) + '</p></div>';
      content += '<div class="bl" style="font-size:12px;color:var(--sub)">Заявка #' + o.id + ' от ' + esc(o.created_at) + (o.expires_at ? ' · Истекает: ' + esc(o.expires_at) : '') + '</div>';
      if (isPerformer && !isOwner && !hasResponded && (o.status === 'new' || o.status === 'has_responses')) {
        content += '<div class="fm" style="margin-top:10px"><label>Комментарий к отклику</label><textarea id="ob-resp-msg" rows="2" placeholder="Готов выполнить..."></textarea>' +
          '<button class="btn p" onclick="APP.orderRespond(' + o.id + ')">Откликнуться</button></div>';
      }
      if (isOwner && o.status === 'has_responses' && o.responses && o.responses.length) {
        content += '<div class="bl"><h3>Отклики (' + o.responses.length + ')</h3>';
        for (var i = 0; i < o.responses.length; i++) {
          var rp = o.responses[i];
          var starsHtml = rp.rating > 0 ? '<span class="st">' + stars(rp.rating) + '</span> ' + rp.rating + ' (' + rp.reviews_count + ')' : '';
          content += '<div class="ob-resp">' +
            '<div class="ob-resp-head"><b>' + esc(rp.performer_name) + '</b>' + starsHtml + '</div>' +
            (rp.message ? '<p>' + esc(rp.message) + '</p>' : '') +
            '<div style="font-size:12px;color:var(--sub)">📞 ' + esc(rp.contact) + '</div>' +
            '<button class="btn p" style="margin-top:6px;font-size:14px;padding:8px" onclick="APP.orderSelect(' + o.id + ',' + rp.id + ')">Выбрать исполнителя</button></div>';
        }
        content += '</div>';
      }
      if (isOwner && (o.status === 'new' || o.status === 'has_responses')) {
        content += '<button class="btn" style="background:var(--red);color:#fff;margin-top:10px;font-size:14px;padding:10px" onclick="APP.orderCancel(' + o.id + ')">Отменить заявку</button>';
      }
      if (isOwner && o.status === 'in_progress') {
        content += '<button class="btn p" style="margin-top:10px;font-size:14px;padding:10px" onclick="APP.orderComplete(' + o.id + ')">Завершить заявку</button>';
      }
      if (isOwner && o.status === 'completed' && S._performerProfile) {
        content += '<div class="fm" style="margin-top:10px"><label>Оценка</label><div class="rt">';
        for (var n = 1; n <= 5; n++) content += '<button class="rb" data-r="' + n + '" onclick="APP.sr(' + n + ')">' + n + '★</button>';
        content += '</div><label>Отзыв</label><textarea id="ob-rev-text" rows="3"></textarea>' +
          '<button class="btn p" style="font-size:14px;padding:10px" onclick="APP.orderReview(' + o.id + ',' + o.selected_performer_id + ')">Оставить отзыв</button></div>';
      }
      content += '</div>';
      render(shell('Заявка #' + o.id, 'orders', content));
    }).catch(function() { render(shell('Ошибка', 'orders', empty('Заявка не найдена'))); });
  }

  function orderRespond(orderId) {
    var msg = document.getElementById('ob-resp-msg') ? document.getElementById('ob-resp-msg').value.trim() : '';
    API.respondToOrder(orderId, { performer_id: S._performerProfile.id, message: msg })
      .then(function() { toast('Отклик отправлен!'); orderOpen(orderId); })
      .catch(function(e) { toast(e.message || 'Ошибка'); });
  }

  function orderSelect(orderId, responseId) {
    API.selectPerformer(orderId, responseId)
      .then(function() { toast('Исполнитель выбран!'); orderOpen(orderId); })
      .catch(function() { toast('Ошибка'); });
  }

  function orderComplete(orderId) {
    API.completeOrder(orderId, S.user.id)
      .then(function() { toast('Заявка завершена!'); orderOpen(orderId); })
      .catch(function() { toast('Ошибка'); });
  }

  function orderCancel(orderId) {
    API.cancelOrder(orderId, S.user.id)
      .then(function() { toast('Заявка отменена'); go('orders'); })
      .catch(function() { toast('Ошибка'); });
  }

  function orderReview(orderId, performerId) {
    if (!S.rating) return toast('Поставьте оценку');
    var text = document.getElementById('ob-rev-text') ? document.getElementById('ob-rev-text').value.trim() : '';
    API.reviewOrder(orderId, { customer_vk_id: S.user.id, performer_id: performerId, rating: S.rating, text: text })
      .then(function() { toast('Отзыв отправлен!'); orderOpen(orderId); })
      .catch(function() { toast('Ошибка'); });
  }

  function orderMy() {
    if (!S.user || !S.user.id) return toast('Войдите через VK');
    render(skel());
    API.getMyOrders(S.user.id).then(function(orders) {
      var items = '';
      for (var i = 0; i < orders.length; i++) {
        var o = orders[i];
        items += '<div class="ob-card" onclick="APP.orderOpen(' + o.id + ')">' +
          '<div class="ob-card-top">' + orderStatusBadge(o.status) + urgencyBadge(o.urgency) + '</div>' +
          '<div class="ob-card-cat">' + esc(o.category) + '</div>' +
          '<div class="ob-card-desc">' + esc(o.description) + '</div>' +
          '<div class="ob-card-bottom"><span>💬 ' + o.responses_count + ' откликов</span></div></div>';
      }
      render(shell('Мои заявки', 'orders', items || empty('У вас пока нет заявок')));
    }).catch(function() { render(shell('Мои заявки', 'orders', empty('Ошибка'))); });
  }

  // ── PERFORMER ──
  function orderPerfReg() {
    if (!S.user || !S.user.id) return toast('Войдите через VK');
    render(shell('Регистрация исполнителя', 'orders',
      '<div class="fm"><label>Ваше имя</label><input id="op-name" value="' + esc(S.user ? S.user.name : '') + '">' +
      '<label>Контакт</label><input id="op-contact" placeholder="Телефон или @username">' +
      '<label>О себе</label><textarea id="op-desc" rows="3" placeholder="Опишите ваши навыки"></textarea>' +
      '<button class="btn p" onclick="APP.orderPerfRegSend()">Зарегистрироваться</button></div>'));
  }

  function orderPerfRegSend() {
    var name = document.getElementById('op-name').value.trim();
    if (!name) return toast('Введите имя');
    API.registerPerformer({
      vk_id: S.user.id, name: name,
      contact: document.getElementById('op-contact').value.trim(),
      description: document.getElementById('op-desc').value.trim(),
    }).then(function() {
      S._isPerformer = true;
      toast('Вы зарегистрированы!');
      orderPerfCabinet();
    }).catch(function() { toast('Ошибка'); });
  }

  function orderPerfCabinet() {
    if (!S.user || !S.user.id) return toast('Войдите через VK');
    render(skel());
    Promise.all([API.getPerformerProfile(S.user.id), API.getOrderCategories()])
      .then(function(res) {
        var p = res[0], allCats = res[1];
        S._performerProfile = p;
        var myCatIds = {};
        for (var i = 0; i < p.categories.length; i++) myCatIds[p.categories[i].id] = true;
        var catsHtml = '';
        for (var i = 0; i < allCats.length; i++) {
          var checked = myCatIds[allCats[i].id] ? ' checked' : '';
          catsHtml += '<label class="ob-cat-item"><input type="checkbox" value="' + allCats[i].id + '"' + checked + '> ' + esc(allCats[i].name) + '</label>';
        }
        var content = '<div class="ob-perf-header">' +
          '<div class="pa" style="background:linear-gradient(135deg,var(--orange),#ff3b30)">' + esc((p.name || '?')[0]) + '</div>' +
          '<h2>' + esc(p.name) + '</h2>' +
          '<div class="ps"><span class="st">' + stars(p.rating) + '</span> ' + p.rating + ' · ' + p.reviews_count + ' отзывов</div>' +
          '<div style="margin-top:6px">' + (p.accepts_requests ? '<span class="b v">✓ Принимает заявки</span>' : '<span class="b" style="background:#ff3b30;color:#fff">Не принимает</span>') + '</div></div>';
        content += '<div class="bl"><h3>Категории заявок</h3><div class="ob-cats-list">' + catsHtml + '</div>' +
          '<button class="btn p" style="margin-top:8px;font-size:14px;padding:10px" onclick="APP.orderPerfSaveCats()">Сохранить категории</button></div>';
        content += '<button class="btn edit-btn" style="margin-top:8px;font-size:14px;padding:10px" onclick="APP.orderPerfToggle()">' +
          (p.accepts_requests ? 'Отключить получение заявок' : 'Включить получение заявок') + '</button>';
        content += '<div class="bl" style="margin-top:8px"><button class="btn" style="background:var(--sub);color:#fff;font-size:14px;padding:10px" onclick="APP.orderPerfEdit()">Редактировать профиль</button></div>';
        render(shell('Кабинет исполнителя', 'orders', content));
      }).catch(function() { render(shell('Кабинет', 'orders', empty('Зарегистрируйтесь как исполнитель'))); });
  }

  function orderPerfSaveCats() {
    var checks = document.querySelectorAll('.ob-cats-list input[type=checkbox]');
    var ids = [];
    for (var i = 0; i < checks.length; i++) {
      if (checks[i].checked) ids.push(Number(checks[i].value));
    }
    if (!ids.length) return toast('Выберите хотя бы одну категорию');
    API.setPerformerCategories({ vk_id: S.user.id, category_ids: ids })
      .then(function() { toast('Категории сохранены!'); orderPerfCabinet(); })
      .catch(function() { toast('Ошибка'); });
  }

  function orderPerfToggle() {
    API.togglePerformer(S.user.id)
      .then(function(r) { toast(r.accepts_requests ? 'Приём заявок включён' : 'Приём заявок отключён'); orderPerfCabinet(); })
      .catch(function() { toast('Ошибка'); });
  }

  function orderPerfEdit() {
    API.getPerformerProfile(S.user.id).then(function(p) {
      render(shell('Редактирование', 'orders',
        '<div class="fm"><label>Имя</label><input id="ope-name" value="' + esc(p.name) + '">' +
        '<label>Контакт</label><input id="ope-contact" value="' + esc(p.contact) + '">' +
        '<label>О себе</label><textarea id="ope-desc" rows="3">' + esc(p.description) + '</textarea>' +
        '<button class="btn p" onclick="APP.orderPerfEditSave()">Сохранить</button></div>'));
    });
  }

  function orderPerfEditSave() {
    API.updatePerformer({
      vk_id: S.user.id,
      name: document.getElementById('ope-name').value.trim(),
      contact: document.getElementById('ope-contact').value.trim(),
      description: document.getElementById('ope-desc').value.trim(),
    }).then(function() { toast('Сохранено!'); orderPerfCabinet(); }).catch(function() { toast('Ошибка'); });
  }

  function orderPerfResponses() {
    if (!S.user || !S.user.id) return toast('Войдите через VK');
    render(skel());
    API.getPerformerOrders(S.user.id).then(function(orders) {
      var items = '';
      for (var i = 0; i < orders.length; i++) {
        var o = orders[i];
        var respBadge = o.my_response ? '<span class="b v" style="margin-left:4px">✓ Откликнулся</span>' : '';
        items += '<div class="ob-card" onclick="APP.orderOpen(' + o.id + ')">' +
          '<div class="ob-card-top">' + orderStatusBadge(o.status) + urgencyBadge(o.urgency) + respBadge + '</div>' +
          '<div class="ob-card-cat">' + esc(o.category) + '</div>' +
          '<div class="ob-card-desc">' + esc(o.description) + '</div>' +
          '<div class="ob-card-bottom"><span>👤 ' + esc(o.user_name) + '</span><span>📍 ' + esc(o.address || '') + '</span></div></div>';
      }
      render(shell('Мои отклики', 'orders', items || empty('Нет заявок по вашим категориям')));
    }).catch(function() { render(shell('Мои отклики', 'orders', empty('Ошибка'))); });
  }

  function initPerformerState() {
    if (!S.user || !S.user.id) { S._isPerformer = false; return Promise.resolve(); }
    return API.getPerformerProfile(S.user.id)
      .then(function(p) { S._isPerformer = true; S._performerProfile = p; })
      .catch(function() { S._isPerformer = false; S._performerProfile = null; });
  }

  // ── SEARCH / FILTER ──
  function searchBtn(sec) {
    var input = document.getElementById('si-input');
    if (!input) return;
    var q = input.value.trim();
    var p = q.length >= 2 ? { search: q } : {};
    var fns = { masters: showMasters, shops: showShops, food: showFood, jobs: showJobs, guide: showGuide };
    if (fns[sec]) fns[sec](p);
  }

  function srchF(sec, q) {
  }

  function flt(sec, cat) {
    var fns = { masters: showMasters, shops: showShops, food: showFood, guide: showGuide };
    if (fns[sec]) fns[sec](cat ? { category_id: cat } : {});
  }

  // ── ROUTE ──
  function route() {
    var h = (location.hash || '#masters').replace('#', '');
    var p = h.split('/').filter(Boolean);
    if (p[0] === 'master' && p[1]) return openM(Number(p[1]));
    if (p[0] === 'shop' && p[1]) return openS(Number(p[1]), 'shop');
    if (p[0] === 'food' && p[1]) return openS(Number(p[1]), 'food');
    if (p[0] === 'job' && p[1]) return openJob(Number(p[1]));
    if (p[0] === 'order' && p[1]) return orderOpen(Number(p[1]));
    var map = { masters: showMasters, shops: showShops, food: showFood, jobs: showJobs, guide: showGuide, ads: showAds, admin: showAdmin, performers: showPerformers, more: showMore, orders: showOrders };
    if (map[p[0]]) map[p[0]]();
    else showMasters();
  }

  window.APP = {
    go: go, flt: flt, srchF: srchF, searchBtn: searchBtn,
    openM: openM, openS: openS, openJob: openJob,
    rf: rf, sr: sr, sendRev: sendRev,
    regF: regF, sendR: sendR, empF: empF, sendEmp: sendEmp,
    submitAd: submitAd, sendAd: sendAd,
    sendA: sendA,
    copyNum: copyNum,
    editM: editM, saveM: saveM, editS: editS, saveS: saveS, editE: editE, saveE: saveE,
    showMyItems: showMyItems,
    orderCreateF: orderCreateF, orderSend: orderSend, orderList: orderList, orderOpen: orderOpen,
    orderRespond: orderRespond, orderSelect: orderSelect, orderComplete: orderComplete,
    orderCancel: orderCancel, orderReview: orderReview, orderMy: orderMy,
    orderPerfReg: orderPerfReg, orderPerfRegSend: orderPerfRegSend,
    orderPerfCabinet: orderPerfCabinet, orderPerfSaveCats: orderPerfSaveCats,
    orderPerfToggle: orderPerfToggle, orderPerfEdit: orderPerfEdit, orderPerfEditSave: orderPerfEditSave,
    orderPerfResponses: orderPerfResponses,
    shopTab: shopTab,
  };

  initVK().then(function() {
    initPerformerState().then(function() {
      route();
      window.addEventListener('hashchange', route);
    });
  });
})();
