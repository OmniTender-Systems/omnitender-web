// community-forum.js — OmniTender public Community forum (customers & vendors)
// Talks directly to Supabase (see supabaseClient.js) — this static site has no
// server of its own for this feature; every access rule lives in Postgres Row
// Level Security + triggers (see supabase/community_schema.sql), not here.
// New posts are held as 'pending' until a moderator (a row in forum_admins)
// approves them; comments are visible immediately on an approved post.
(function () {
  'use strict';

  var CATEGORY_LABELS = { general: 'General', question: 'Question', announcement: '📣 Announcement' };

  var _session = null;
  var _isAdmin = false;
  var _posts = [];
  var _expanded = {};

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/\//g, '&#47;');
  }

  function when(iso) {
    try { return new Date(iso).toLocaleString(); } catch (e) { return iso || ''; }
  }

  function statusMsg(id, msg, isErr) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg || '';
    el.className = 'forum-status' + (isErr ? ' err' : '');
  }

  function sb() {
    return window.supabaseClient || null;
  }

  // ---- auth ----

  function renderAuthPanel() {
    var el = document.getElementById('forum-auth');
    if (!el) return;
    if (!sb()) {
      el.innerHTML = '<p class="fine">Community sign-in is not configured on this deployment.</p>';
      return;
    }
    if (!_session) {
      el.innerHTML =
        '<form id="forum-login-form" class="forum-inline-form">' +
        '<label for="forum-email" class="fine">Sign in with your email to post or reply — no password, just a one-time link.</label>' +
        '<div class="forum-inline-row">' +
        '<input type="email" id="forum-email" placeholder="you@example.com" required>' +
        '<button type="submit" class="btn-hero secondary">Email me a sign-in link</button>' +
        '</div></form>' +
        '<p class="forum-status" id="forum-auth-status"></p>';
      var form = document.getElementById('forum-login-form');
      if (form) form.addEventListener('submit', handleMagicLink);
      return;
    }

    var name = (_session.user.user_metadata || {}).display_name || '';
    el.innerHTML =
      '<div class="forum-account-row">' +
      '<span>Signed in as <strong>' + esc(_session.user.email) + '</strong>' + (_isAdmin ? ' <span class="pf-pin">· Moderator</span>' : '') + '</span>' +
      '<button type="button" class="btn-hero secondary" id="forum-signout">Sign out</button>' +
      '</div>' +
      (name ? '' :
        '<form id="forum-name-form" class="forum-inline-form">' +
        '<label for="forum-name" class="fine">Choose a display name for your posts (shown publicly instead of your email).</label>' +
        '<div class="forum-inline-row">' +
        '<input type="text" id="forum-name" maxlength="80" placeholder="e.g. Jordan at Acme Merchant" required>' +
        '<button type="submit" class="btn-hero primary">Save</button>' +
        '</div></form>' +
        '<p class="forum-status" id="forum-name-status"></p>');

    var signout = document.getElementById('forum-signout');
    if (signout) signout.addEventListener('click', function () { sb().auth.signOut(); });
    var nameForm = document.getElementById('forum-name-form');
    if (nameForm) nameForm.addEventListener('submit', handleSetDisplayName);
  }

  async function handleMagicLink(e) {
    e.preventDefault();
    var email = (document.getElementById('forum-email').value || '').trim();
    if (!email) return;
    statusMsg('forum-auth-status', 'Sending…', false);
    try {
      var { error } = await sb().auth.signInWithOtp({ email: email, options: { emailRedirectTo: window.location.href } });
      if (error) throw error;
      statusMsg('forum-auth-status', 'Check your email for a sign-in link.', false);
    } catch (err) {
      statusMsg('forum-auth-status', err.message || 'Could not send the link. Try again.', true);
    }
  }

  async function handleSetDisplayName(e) {
    e.preventDefault();
    var name = (document.getElementById('forum-name').value || '').trim();
    if (name.length < 1) return;
    statusMsg('forum-name-status', 'Saving…', false);
    try {
      var { error } = await sb().auth.updateUser({ data: { display_name: name } });
      if (error) throw error;
      await refreshSession();
      renderAuthPanel();
      renderComposer();
    } catch (err) {
      statusMsg('forum-name-status', err.message || 'Could not save. Try again.', true);
    }
  }

  async function refreshSession() {
    if (!sb()) return;
    var { data } = await sb().auth.getSession();
    _session = data && data.session ? data.session : null;
    _isAdmin = false;
    if (_session) {
      try {
        var { data: adminRow } = await sb().from('forum_admins').select('user_id').eq('user_id', _session.user.id).maybeSingle();
        _isAdmin = !!adminRow;
      } catch (e) { _isAdmin = false; }
    }
  }

  function displayName() {
    return _session ? ((_session.user.user_metadata || {}).display_name || '') : '';
  }

  // ---- composer ----

  function categoryOptionsHtml() {
    return Object.keys(CATEGORY_LABELS)
      .filter(function (c) { return c !== 'announcement' || _isAdmin; })
      .map(function (c) { return '<option value="' + esc(c) + '">' + esc(CATEGORY_LABELS[c]) + '</option>'; })
      .join('');
  }

  function renderComposer() {
    var el = document.getElementById('forum-composer');
    if (!el) return;
    if (!_session || !displayName()) {
      el.innerHTML = '';
      el.style.display = 'none';
      return;
    }
    el.style.display = 'block';
    el.innerHTML =
      '<div class="card">' +
      '<h3 style="margin-top:0;">Start a discussion</h3>' +
      '<form id="forum-post-form" novalidate>' +
      '<label for="forum-post-title">Title</label>' +
      '<input type="text" id="forum-post-title" required maxlength="160" placeholder="What do you want to ask or share?">' +
      '<label for="forum-post-body">Details</label>' +
      '<textarea id="forum-post-body" required maxlength="4000" rows="4" style="width:100%;padding:12px;border-radius:8px;border:1px solid var(--border);background:var(--surface-2);color:inherit;font:inherit;"></textarea>' +
      '<label for="forum-post-category">Category</label>' +
      '<select id="forum-post-category" style="width:100%;">' + categoryOptionsHtml() + '</select>' +
      '<p class="fine">New posts are reviewed by a moderator before they appear publicly — usually within a day.</p>' +
      '<button type="submit" class="btn-hero primary">Post for review</button>' +
      '<p class="forum-status" id="forum-post-status"></p>' +
      '</form></div>';
    var form = document.getElementById('forum-post-form');
    if (form) form.addEventListener('submit', handleNewPost);
  }

  async function handleNewPost(e) {
    e.preventDefault();
    var title = (document.getElementById('forum-post-title').value || '').trim();
    var body = (document.getElementById('forum-post-body').value || '').trim();
    var category = (document.getElementById('forum-post-category') || { value: 'general' }).value;
    if (title.length < 3 || body.length < 3) {
      statusMsg('forum-post-status', 'Title and details are required.', true);
      return;
    }
    statusMsg('forum-post-status', 'Posting…', false);
    try {
      var { error } = await sb().from('forum_posts').insert({
        title: title, body: body, category: category,
        user_id: _session.user.id, display_name: displayName(),
      });
      if (error) throw error;
      document.getElementById('forum-post-form').reset();
      statusMsg('forum-post-status', 'Posted — awaiting moderator review.', false);
      await loadFeed();
    } catch (err) {
      statusMsg('forum-post-status', err.message || 'Could not post. Try again.', true);
    }
  }

  // ---- feed ----

  function postBadge(post) {
    if (post.deleted) return '<span class="pf-pin" style="color:var(--danger);">Removed</span>';
    if (post.status === 'pending') return '<span class="pf-pin">Pending review</span>';
    if (post.status === 'rejected') return '<span class="pf-pin" style="color:var(--danger);">Not approved</span>';
    return '';
  }

  function commentHtml(postId, comment) {
    if (comment.deleted) {
      return '<div class="pf-comment pf-comment-deleted"><div class="pf-comment-body">[deleted]</div></div>';
    }
    var canRemove = _session && (_isAdmin || comment.user_id === _session.user.id);
    return '<div class="pf-comment" data-id="' + comment.id + '">' +
      '<div class="pf-comment-meta">' + esc(comment.display_name) + ' <span class="pf-time">· ' + esc(when(comment.created_at)) + '</span></div>' +
      '<div class="pf-comment-body">' + esc(comment.body) + '</div>' +
      (canRemove ? '<button type="button" class="btn-hero secondary forum-mini-btn" data-forum-del-comment="' + comment.id + '">Remove</button>' : '') +
      '</div>';
  }

  function postHtml(post) {
    var open = !!_expanded[post.id];
    var mine = _session && post.user_id === _session.user.id;
    var chip = '<span class="pf-chip pf-chip-' + esc(post.category) + '">' + esc(CATEGORY_LABELS[post.category] || post.category) + '</span>';
    var badge = postBadge(post);
    var comments = (post.forum_comments || []).filter(function (c) { return !!c; })
      .sort(function (a, b) { return String(a.created_at).localeCompare(String(b.created_at)); });

    var actions = [];
    if (!post.deleted && (mine || _isAdmin)) {
      actions.push('<button type="button" class="btn-hero secondary forum-mini-btn" data-forum-del-post="' + post.id + '">Remove</button>');
    }
    if (!post.deleted && _isAdmin && post.status !== 'approved') {
      actions.push('<button type="button" class="btn-hero primary forum-mini-btn" data-forum-approve="' + post.id + '">Approve</button>');
      actions.push('<button type="button" class="btn-hero secondary forum-mini-btn" data-forum-reject="' + post.id + '">Reject</button>');
    }
    if (!post.deleted && _isAdmin && post.status === 'approved') {
      actions.push('<button type="button" class="btn-hero secondary forum-mini-btn" data-forum-pin="' + post.id + '">' + (post.pinned ? 'Unpin' : 'Pin') + '</button>');
    }

    var commentsHtml = '';
    if (open) {
      commentsHtml = '<div class="pf-comments">' +
        (comments.length ? comments.map(function (c) { return commentHtml(post.id, c); }).join('') : '<div class="pf-empty">No replies yet.</div>') +
        (post.status === 'approved' && !post.deleted && _session
          ? '<div class="pf-reply-row"><textarea class="pf-reply-input" id="forum-reply-' + post.id + '" rows="2" placeholder="Write a reply…"></textarea>' +
            '<button type="button" class="btn-hero primary forum-mini-btn" data-forum-reply="' + post.id + '">Reply</button></div>'
          : (post.status === 'approved' && !post.deleted ? '<p class="fine">Sign in above to reply.</p>' : '')) +
        '</div>';
    }

    return '<div class="card forum-post' + (post.pinned ? ' forum-post-pinned' : '') + '" data-id="' + post.id + '">' +
      '<div class="pf-post-head">' + chip + (post.pinned ? '<span class="pf-pin">📌 Pinned</span>' : '') + badge + '</div>' +
      '<h3 style="margin:0 0 6px;">' + esc(post.title) + '</h3>' +
      '<div class="pf-post-meta">' + esc(post.display_name) + ' <span class="pf-time">· ' + esc(when(post.created_at)) + '</span></div>' +
      '<div class="pf-post-body">' + esc(post.body) + '</div>' +
      '<div class="pf-post-actions">' +
      (post.status === 'approved' && !post.deleted
        ? '<button type="button" class="btn-hero secondary forum-mini-btn" data-forum-toggle="' + post.id + '">' + (open ? 'Hide' : 'View') + ' discussion (' + comments.filter(function (c) { return !c.deleted; }).length + ')</button>'
        : '') +
      actions.join('') +
      '</div>' + commentsHtml + '</div>';
  }

  function renderFeed() {
    var el = document.getElementById('forum-feed');
    if (!el) return;
    var visible = _posts;
    el.innerHTML = visible.length
      ? visible.map(postHtml).join('')
      : '<p class="fine" style="text-align:center;">No posts yet — be the first to start a discussion.</p>';
    bindFeedEvents();
  }

  function bindFeedEvents() {
    var el = document.getElementById('forum-feed');
    if (!el) return;
    el.querySelectorAll('[data-forum-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-forum-toggle');
        _expanded[id] = !_expanded[id];
        renderFeed();
      });
    });
    el.querySelectorAll('[data-forum-del-post]').forEach(function (btn) {
      btn.addEventListener('click', function () { removePost(btn.getAttribute('data-forum-del-post')); });
    });
    el.querySelectorAll('[data-forum-approve]').forEach(function (btn) {
      btn.addEventListener('click', function () { moderatePost(btn.getAttribute('data-forum-approve'), 'approved'); });
    });
    el.querySelectorAll('[data-forum-reject]').forEach(function (btn) {
      btn.addEventListener('click', function () { moderatePost(btn.getAttribute('data-forum-reject'), 'rejected'); });
    });
    el.querySelectorAll('[data-forum-pin]').forEach(function (btn) {
      btn.addEventListener('click', function () { togglePin(btn.getAttribute('data-forum-pin')); });
    });
    el.querySelectorAll('[data-forum-reply]').forEach(function (btn) {
      btn.addEventListener('click', function () { submitReply(btn.getAttribute('data-forum-reply')); });
    });
    el.querySelectorAll('[data-forum-del-comment]').forEach(function (btn) {
      btn.addEventListener('click', function () { removeComment(btn.getAttribute('data-forum-del-comment')); });
    });
  }

  async function removePost(id) {
    if (!window.confirm('Remove this post? This cannot be undone.')) return;
    try {
      var { error } = await sb().from('forum_posts').update({ deleted: true }).eq('id', id);
      if (error) throw error;
      await loadFeed();
    } catch (err) { window.alert(err.message || 'Could not remove.'); }
  }

  async function moderatePost(id, status) {
    try {
      var { error } = await sb().from('forum_posts').update({ status: status }).eq('id', id);
      if (error) throw error;
      await loadFeed();
    } catch (err) { window.alert(err.message || 'Could not update.'); }
  }

  async function togglePin(id) {
    var post = _posts.find(function (p) { return p.id === id; });
    if (!post) return;
    try {
      var { error } = await sb().from('forum_posts').update({ pinned: !post.pinned }).eq('id', id);
      if (error) throw error;
      await loadFeed();
    } catch (err) { window.alert(err.message || 'Could not update.'); }
  }

  async function submitReply(postId) {
    var input = document.getElementById('forum-reply-' + postId);
    if (!input) return;
    var body = (input.value || '').trim();
    if (!body) return;
    try {
      var { error } = await sb().from('forum_comments').insert({
        post_id: postId, body: body, user_id: _session.user.id, display_name: displayName(),
      });
      if (error) throw error;
      _expanded[postId] = true;
      await loadFeed();
    } catch (err) { window.alert(err.message || 'Could not reply.'); }
  }

  async function removeComment(id) {
    if (!window.confirm('Remove this reply? This cannot be undone.')) return;
    try {
      var { error } = await sb().from('forum_comments').update({ deleted: true }).eq('id', id);
      if (error) throw error;
      await loadFeed();
    } catch (err) { window.alert(err.message || 'Could not remove.'); }
  }

  async function loadFeed() {
    var el = document.getElementById('forum-feed');
    if (!el || !sb()) return;
    try {
      var { data, error } = await sb()
        .from('forum_posts')
        .select('*, forum_comments(*)')
        .order('pinned', { ascending: false })
        .order('created_at', { ascending: false });
      if (error) throw error;
      _posts = data || [];
      renderFeed();
    } catch (err) {
      el.innerHTML = '<p class="fine" style="text-align:center;">Could not load the Community feed: ' + esc(err.message) + '</p>';
    }
  }

  async function init() {
    if (!sb()) {
      var el = document.getElementById('forum-auth');
      if (el) el.innerHTML = '<p class="fine">Community sign-in is not configured on this deployment.</p>';
      var feed = document.getElementById('forum-feed');
      if (feed) feed.innerHTML = '';
      return;
    }
    await refreshSession();
    renderAuthPanel();
    renderComposer();
    await loadFeed();

    sb().auth.onAuthStateChange(async function () {
      await refreshSession();
      renderAuthPanel();
      renderComposer();
      await loadFeed();
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
