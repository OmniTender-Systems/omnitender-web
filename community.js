// community.js — OmniTender Community (internal staff discussion board)
// Self-contained IIFE, mirroring workboard.js: owns its own API base, esc,
// and helpers rather than depending on dashboard.js internals.
//
// Backend contract (OmniVerse, validated):
//   GET  /api/community/posts                          -> { items, categories }
//   POST /api/community/posts                           -> 201 { item }  (title, body, category)
//   POST /api/community/posts/:id                        -> { item }     (title/body/category if author; pinned/deleted per role)
//   POST /api/community/posts/:id/comments                -> 201 { item } (body)
//   POST /api/community/posts/:id/comments/:commentId     -> { item }     (deleted: true/false)
// CSRF/auth via Authorization: Bearer from sessionStorage 'omni_dash_token'.
(function () {
  'use strict';

  var API = window.location.hostname === 'omnitender-omniverse.fly.dev' || window.location.port === '3000'
    ? ''
    : (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname === '[::1]'
      ? 'http://' + window.location.hostname + ':3000'
      : 'https://omnitender-omniverse.fly.dev');

  var CATEGORY_LABELS = { general: 'General', question: 'Question', announcement: '📣 Announcement' };

  var _currentUserRole = sessionStorage.getItem('omni_dash_role') || 'Employee';
  var _currentUser = sessionStorage.getItem('omni_dash_username') || '';
  var _cache = [];        // posts, each with a nested .comments array
  var _categories = ['general', 'question', 'announcement'];
  var _expanded = {};     // postId -> true while its thread is open

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/\//g, '&#47;');
  }

  function toast(msg, isErr) {
    var t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast' + (isErr ? ' err' : '');
    t.style.display = 'block';
    setTimeout(function () { t.style.display = 'none'; }, 3500);
  }

  function authHeaders() {
    return { 'Authorization': 'Bearer ' + (sessionStorage.getItem('omni_dash_token') || '') };
  }

  async function api(path, opts) {
    var o = opts || {};
    var init = { method: o.method || 'GET', headers: authHeaders() };
    if (init.method !== 'GET') {
      init.headers['Content-Type'] = 'application/json';
      init.headers['X-OV-Console'] = '1';
      init.body = JSON.stringify(o.body || {});
    }
    var r = await fetch(API + path, init);
    var ct = r.headers.get('content-type') || '';
    var data = ct.includes('json') ? await r.json() : await r.text();
    if (!r.ok) throw new Error((data && data.error) || ('HTTP ' + r.status));
    return data;
  }

  function isModerator() {
    return _currentUserRole === 'Admin' || _currentUserRole === 'Owner';
  }

  function canManage(record) {
    return isModerator() || (record && record.author === _currentUser);
  }

  function when(iso) {
    try { return new Date(iso).toLocaleString(); } catch (e) { return iso || ''; }
  }

  function commentHtml(postId, comment) {
    if (comment.deleted) {
      return '<div class="cm-comment cm-comment-deleted" data-id="' + comment.id + '">' +
        '<div class="cm-comment-body">[deleted]</div></div>';
    }
    var actions = canManage(comment)
      ? '<button type="button" class="wb-btn wb-btn-mini wb-btn-del" data-cm-del-comment="' + comment.id + '" data-post="' + postId + '">Remove</button>'
      : '';
    return '<div class="cm-comment" data-id="' + comment.id + '">' +
      '<div class="cm-comment-meta">' + esc(comment.author) + (comment.authorRole ? ' <span class="cm-role">· ' + esc(comment.authorRole) + '</span>' : '') +
      ' <span class="cm-time">· ' + esc(when(comment.createdAt)) + '</span></div>' +
      '<div class="cm-comment-body">' + esc(comment.body) + '</div>' +
      (actions ? '<div class="wb-card-actions">' + actions + '</div>' : '') +
      '</div>';
  }

  function postHtml(post) {
    var open = !!_expanded[post.id];
    var isDeleted = !!post.deleted;
    var chip = '<span class="cm-chip cm-chip-' + esc(post.category) + '">' + esc(CATEGORY_LABELS[post.category] || post.category) + '</span>';
    var pinned = post.pinned ? '<span class="cm-pin">📌 Pinned</span>' : '';

    var actions = [];
    if (!isDeleted && canManage(post)) {
      actions.push('<button type="button" class="wb-btn wb-btn-mini" data-cm-edit="' + post.id + '">Edit</button>');
      actions.push('<button type="button" class="wb-btn wb-btn-mini wb-btn-del" data-cm-del="' + post.id + '">Remove</button>');
    }
    if (!isDeleted && isModerator()) {
      actions.push('<button type="button" class="wb-btn wb-btn-mini" data-cm-pin="' + post.id + '">' + (post.pinned ? 'Unpin' : 'Pin') + '</button>');
    }

    var visibleComments = post.comments || [];
    var commentsHtml = open
      ? '<div class="cm-comments">' +
          (visibleComments.length ? visibleComments.map(function (c) { return commentHtml(post.id, c); }).join('') : '<div class="wb-empty">No replies yet — be the first.</div>') +
          (isDeleted ? '' :
            '<div class="cm-reply-row">' +
            '<textarea class="cm-reply-input" id="cm-reply-' + post.id + '" rows="2" placeholder="Write a reply…"></textarea>' +
            '<button type="button" class="wb-btn wb-btn-primary wb-btn-mini" data-cm-reply="' + post.id + '">Reply</button>' +
            '</div>') +
        '</div>'
      : '';

    return '<div class="wb-card cm-post' + (post.pinned ? ' cm-post-pinned' : '') + '" data-id="' + post.id + '">' +
      '<div class="cm-post-head">' + chip + pinned + '</div>' +
      '<div class="wb-card-title">' + esc(post.title) + '</div>' +
      '<div class="cm-post-meta">' + esc(post.author) + (post.authorRole ? ' <span class="cm-role">· ' + esc(post.authorRole) + '</span>' : '') +
        ' <span class="cm-time">· ' + esc(when(post.createdAt)) + '</span></div>' +
      (isDeleted ? '<div class="cm-post-body cm-deleted">[deleted]</div>' : '<div class="cm-post-body">' + esc(post.body) + '</div>') +
      '<div class="cm-post-actions">' +
      '<button type="button" class="wb-btn wb-btn-mini" data-cm-toggle="' + post.id + '">' +
        (open ? 'Hide' : 'View') + ' discussion (' + visibleComments.length + ')</button>' +
      actions.join('') +
      '</div>' +
      commentsHtml +
      '</div>';
  }

  function renderFeed() {
    var root = document.getElementById('community-root');
    if (!root) return;

    var html = '<div class="wb-toolbar">' +
      '<button type="button" class="wb-btn wb-btn-primary" id="cm-new-post">+ New Post</button>' +
      '<span class="wb-toolbar-note" id="cm-summary"></span>' +
      '</div>' +
      '<div class="cm-feed">' +
      (_cache.length ? _cache.map(postHtml).join('') : '<div class="wb-empty">No posts yet — start the first discussion.</div>') +
      '</div>';

    root.innerHTML = html;
    var live = _cache.filter(function (p) { return !p.deleted; }).length;
    document.getElementById('cm-summary').textContent = live + ' post' + (live === 1 ? '' : 's');
    bindFeedEvents();
  }

  function bindFeedEvents() {
    var root = document.getElementById('community-root');
    if (!root) return;
    var newBtn = document.getElementById('cm-new-post');
    if (newBtn) newBtn.addEventListener('click', function () { openPostModal(null); });

    root.querySelectorAll('[data-cm-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-cm-toggle');
        _expanded[id] = !_expanded[id];
        renderFeed();
      });
    });
    root.querySelectorAll('[data-cm-edit]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var post = _cache.find(function (p) { return p.id === btn.getAttribute('data-cm-edit'); });
        if (post) openPostModal(post);
      });
    });
    root.querySelectorAll('[data-cm-del]').forEach(function (btn) {
      btn.addEventListener('click', function (e) { e.stopPropagation(); deletePost(btn.getAttribute('data-cm-del')); });
    });
    root.querySelectorAll('[data-cm-pin]').forEach(function (btn) {
      btn.addEventListener('click', function (e) { e.stopPropagation(); togglePin(btn.getAttribute('data-cm-pin')); });
    });
    root.querySelectorAll('[data-cm-reply]').forEach(function (btn) {
      btn.addEventListener('click', function (e) { e.stopPropagation(); submitReply(btn.getAttribute('data-cm-reply')); });
    });
    root.querySelectorAll('[data-cm-del-comment]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        deleteComment(btn.getAttribute('data-post'), btn.getAttribute('data-cm-del-comment'));
      });
    });
  }

  function categoryOptionsHtml(selected) {
    return _categories
      .filter(function (c) { return c !== 'announcement' || isModerator(); })
      .map(function (c) {
        return '<option value="' + esc(c) + '"' + (c === selected ? ' selected' : '') + '>' + esc(CATEGORY_LABELS[c] || c) + '</option>';
      }).join('');
  }

  function openPostModal(post) {
    var root = document.getElementById('community-root');
    if (!root) return;
    var isEdit = !!post;
    var p = post || {};
    var html = '<div class="wb-modal-backdrop" id="cm-modal">' +
      '<div class="wb-modal">' +
      '<div class="wb-modal-head">' + (isEdit ? 'Edit Post' : 'New Post') +
      '<button type="button" class="wb-modal-x" id="cm-modal-close">&times;</button></div>' +
      '<div class="wb-modal-body">' +
      '<label class="wb-field"><span>Title *</span><input id="cm-form-title" value="' + esc(p.title || '') + '" placeholder="What do you want to ask or share?"></label>' +
      '<label class="wb-field"><span>Details *</span><textarea id="cm-form-body" rows="5">' + esc(p.body || '') + '</textarea></label>' +
      '<label class="wb-field"><span>Category</span><select id="cm-form-category">' + categoryOptionsHtml(p.category || 'general') + '</select></label>' +
      '</div>' +
      '<div class="wb-modal-foot">' +
      '<button type="button" class="wb-btn wb-btn-primary" id="cm-form-save">' + (isEdit ? 'Save Changes' : 'Post') + '</button>' +
      '<button type="button" class="wb-btn" id="cm-modal-cancel">Cancel</button>' +
      '<span class="wb-form-status" id="cm-form-status"></span>' +
      '</div>' +
      '</div></div>';
    root.insertAdjacentHTML('afterbegin', html);
    bindModalEvents(post ? post.id : null);
  }

  function closeModal() {
    var m = document.getElementById('cm-modal');
    if (m) m.remove();
  }

  function bindModalEvents(postId) {
    var close = document.getElementById('cm-modal-close');
    var cancel = document.getElementById('cm-modal-cancel');
    var backdrop = document.getElementById('cm-modal');
    var save = document.getElementById('cm-form-save');
    var statusEl = document.getElementById('cm-form-status');
    if (close) close.addEventListener('click', closeModal);
    if (cancel) cancel.addEventListener('click', closeModal);
    if (backdrop) backdrop.addEventListener('click', function (e) { if (e.target === backdrop) closeModal(); });
    if (save) save.addEventListener('click', async function () {
      save.disabled = true;
      save.textContent = 'Saving…';
      statusEl.textContent = '';
      var body = {
        title: (document.getElementById('cm-form-title').value || '').trim(),
        body: (document.getElementById('cm-form-body').value || '').trim(),
        category: (document.getElementById('cm-form-category') || { value: 'general' }).value
      };
      try {
        if (postId) { await api('/api/community/posts/' + postId, { method: 'POST', body: body }); toast('Post updated.'); }
        else { await api('/api/community/posts', { method: 'POST', body: body }); toast('Posted.'); }
        closeModal();
        await load();
      } catch (err) {
        statusEl.textContent = err.message;
        toast(err.message, true);
      } finally {
        save.disabled = false;
        save.textContent = postId ? 'Save Changes' : 'Post';
      }
    });
  }

  async function deletePost(id) {
    if (!window.confirm('Remove this post? This cannot be undone.')) return;
    try {
      await api('/api/community/posts/' + id, { method: 'POST', body: { deleted: true } });
      toast('Post removed.');
      await load();
    } catch (err) { toast(err.message, true); }
  }

  async function togglePin(id) {
    var post = _cache.find(function (p) { return p.id === id; });
    if (!post) return;
    try {
      await api('/api/community/posts/' + id, { method: 'POST', body: { pinned: !post.pinned } });
      toast(post.pinned ? 'Unpinned.' : 'Pinned.');
      await load();
    } catch (err) { toast(err.message, true); }
  }

  async function submitReply(postId) {
    var input = document.getElementById('cm-reply-' + postId);
    if (!input) return;
    var body = (input.value || '').trim();
    if (!body) { toast('Write a reply first.', true); return; }
    try {
      await api('/api/community/posts/' + postId + '/comments', { method: 'POST', body: { body: body } });
      _expanded[postId] = true;
      await load();
    } catch (err) { toast(err.message, true); }
  }

  async function deleteComment(postId, commentId) {
    if (!window.confirm('Remove this reply? This cannot be undone.')) return;
    try {
      await api('/api/community/posts/' + postId + '/comments/' + commentId, { method: 'POST', body: { deleted: true } });
      _expanded[postId] = true;
      toast('Reply removed.');
      await load();
    } catch (err) { toast(err.message, true); }
  }

  async function load() {
    var root = document.getElementById('community-root');
    if (!root) return;
    try {
      var data = await api('/api/community/posts');
      _cache = data.items || [];
      _categories = data.categories || _categories;
      renderFeed();
    } catch (err) {
      root.innerHTML = '<div class="card"><h2>🗣️ Community</h2><div class="empty">Could not load Community: ' + esc(err.message) + '</div></div>';
    }
  }

  var OmniTenderCommunity = {
    init: function () {
      _currentUserRole = sessionStorage.getItem('omni_dash_role') || 'Employee';
      _currentUser = sessionStorage.getItem('omni_dash_username') || '';
      load();
    }
  };

  window.OmniTenderCommunity = OmniTenderCommunity;
})();
