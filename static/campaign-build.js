/* Engine 4 on the review screen (campaign build).
 *
 *  - Calendar and Gallery: the 14 posts as bigger cards with the design, day and time, the title,
 *    the caption and 👍 / 👎 ("Like this style?"). One tap, no reason asked.
 *  - Edits are saved on the server (so what goes out is what was approved), with Fair Housing
 *    checked on every edit: a non-compliant edit can't be saved.
 *  - Swapping a photo: pick from this home's photos first (or upload your own); the post is redrawn
 *    on the new photo with its words, style and agent details.
 *  - "Needs a look" on posts the checks couldn't clear, and "Ads run 6 AM to 11 PM" under the ad.
 * Loaded after review.js and signup.js.
 */
(function () {
  const live = () => !!(window.RM && RM.isLoggedIn && RM.isLoggedIn());
  const boostId = () => (typeof reviewCampaignBoostId === 'function' ? reviewCampaignBoostId() : null);
  const call = (path, method, body) => RM.request(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const localTime = iso => { if (!iso) return undefined; const d = new Date(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z'); return isNaN(d) ? undefined : String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); };

  // The server's Engine 4 fields ride along on every post the review screen reads.
  const basePosts = RM && RM.posts;
  if (basePosts) {
    RM.posts = function (id) {
      return basePosts(id).then(rows => {
        if (Array.isArray(rows)) RMBuild.serverPosts[String(id)] = rows;
        return rows;
      });
    };
  }
  const B = (window.RMBuild = { serverPosts: {} });
  function enrich(r) {
    const rows = B.serverPosts[String(boostId())] || [];
    const byId = Object.fromEntries(rows.map(p => [String(p.id), p]));
    (r.items || []).forEach(it => {
      const p = byId[String(it.postId)]; if (!p) return;
      it.rating = p.rating; it.needsLook = !!p.needs_look; it.captionIg = p.caption_ig || ''; it.style = p.design_style || '';
      // A designed post already carries its words: the editor must not print them over it again.
      if (p.design_style || /\/post-\d/.test(p.image_url || '')) it.designed = true;
      // Times are stored in UTC on the server; show them in the agent's own time.
      const t = localTime(p.publish_at); if (t && !it.timeEdited) it.time = t;
    });
  }

  // ------------------------------------------------------------------ Calendar | Gallery
  const baseCalendar = window.reviewCalendar;
  window.reviewCalendar = function (r, c) {
    enrich(r);
    let html = baseCalendar(r, c);
    const i1 = html.indexOf('<div class="review-month-scroll">');
    const i2 = i1 < 0 ? -1 : html.indexOf('<p class="fine">', i1);
    if (i1 < 0 || i2 < 0) return html;
    const gallery = state.calView === 'gallery';
    const toggle = `<div class="cal-views" role="tablist"><button type="button" role="tab" class="${gallery ? '' : 'on'}" aria-selected="${!gallery}" onclick="state.calView='calendar';persist();details(ReviewStudio.active)">Calendar</button><button type="button" role="tab" class="${gallery ? 'on' : ''}" aria-selected="${gallery}" onclick="state.calView='gallery';persist();details(ReviewStudio.active)">Gallery</button></div>`;
    const ads = (r.items || []).some(x => x.kind === 'Meta ad') ? '<p class="cal-ad-hours">Ads run 6 AM to 11 PM.</p>' : '';
    const body = gallery ? galleryView(r) : html.slice(i1, i2);
    return html.slice(0, i1) + toggle + body + ads + html.slice(i2);
  };
  function thumbs(it, i) {
    if (it.postId == null) return '';
    return `<span class="thumbs" role="group" aria-label="Like this style?"><button type="button" class="thumb${it.rating === 1 ? ' on' : ''}" aria-pressed="${it.rating === 1}" title="I like this style" onclick="event.stopPropagation();ratePost(${i},1)">👍</button><button type="button" class="thumb${it.rating === -1 ? ' on' : ''}" aria-pressed="${it.rating === -1}" title="Not for me" onclick="event.stopPropagation();ratePost(${i},-1)">👎</button></span>`;
  }
  function galleryView(r) {
    const cards = (r.items || []).map((it, i) => ({ it, i })).filter(x => x.it.kind !== 'Meta ad').sort((a, b) => a.it.day - b.it.day);
    return `<div class="post-gallery">${cards.map(({ it, i }) => {
      const slot = typeof reviewSlot === 'function' ? reviewSlot(r, it) : {};
      const when = 'Day ' + it.day + (slot.date ? ' · ' + niceDate(slot.date) : '') + (it.time || slot.time ? ' · ' + time12(it.time || slot.time) : '');
      return `<article class="pg-card" onclick="editCampaignItem(${i})">${it.image ? `<img src="${esc(mediaPath(it.image))}" alt="${esc(it.room || it.title || '')}" loading="lazy">` : '<span class="pg-noimg">No design yet</span>'}
        ${it.needsLook ? '<span class="pg-look">Needs a look</span>' : ''}
        <div class="pg-body"><small>${esc(when)}</small><b>${esc(it.title || '')}</b><p>${esc(String(it.caption || '').replace(/\n\n#.*$/s, '').slice(0, 150))}${String(it.caption || '').length > 150 ? '…' : ''}</p>
        <div class="pg-foot"><span>Like this style?</span>${thumbs(it, i)}</div></div></article>`;
    }).join('')}</div>`;
  }
  window.ratePost = async function (i, value) {
    const r = activeReview(), it = r && r.items[i]; if (!it) return;
    const next = it.rating === value ? 0 : value;
    it.rating = next || null; persist();
    if (typeof details === 'function') details(ReviewStudio.active);
    if (live() && boostId() != null && it.postId != null) {
      try { await call(`/api/boosts/${boostId()}/posts/${it.postId}/rating`, 'POST', { value: next }); }
      catch (e) { toast('That didn’t save. Try again.'); }
    }
  };

  // ------------------------------------------------------------------ the post editor
  const baseEdit = window.editCampaignItem;
  window.editCampaignItem = function (i) {
    const out = baseEdit(i);
    const r = activeReview(), it = r && r.items[i];
    if (!it || it.kind === 'Meta ad') return out;
    const host = modal.querySelector('.ei-media') || modal.querySelector('form') || modal;
    // One way to swap a photo on a live post: pick from the home's photos (Upload your own is in there).
    if (it.postId != null && live()) {
      const old = modal.querySelector('input[name="photo"]');
      const wrap = old && (old.closest('label') || old.parentElement);
      if (wrap) { wrap.style.display = 'none'; const help = wrap.nextElementSibling; if (help && help.classList.contains('fine')) help.style.display = 'none'; }
    }
    const locked = r.approved || r.calendarApproved;
    host.insertAdjacentHTML('beforeend', `<div class="ei-e4">
      ${it.needsLook ? '<p class="pg-look-note"><b>Needs a look.</b> Resmara’s checks couldn’t clear this design, so it uses Resmara’s own layout. Glance at it before you approve.</p>' : ''}
      ${it.postId != null ? `<div class="pg-foot"><span>Like this style?</span>${thumbs(it, i)}</div>` : ''}
      ${!locked && it.postId != null && live() ? `<button type="button" class="campaign-primary navy ei-swap" onclick="pickHomePhoto(${i})">Pick from this home’s photos</button>` : ''}
      ${it.captionIg ? '<p class="fine">On Instagram the caption has no link (Instagram doesn’t make them clickable). It ends with an invitation to comment instead.</p>' : ''}</div>`);
    return out;
  };
  // Edits go to the server first; Fair Housing is checked there and a refusal stops the save.
  const baseSave = window.saveReviewItem;
  window.saveReviewItem = async function (i, form) {
    const r = activeReview(), it = r && r.items[i];
    const error = form.querySelector('[role="alert"]');
    if (it && it.kind !== 'Meta ad' && it.postId != null && live() && boostId() != null && form.elements.caption) {
      const changed = {};
      if (form.elements.caption.value !== (it.caption || '')) changed.caption = form.elements.caption.value;
      if (form.elements.title && form.elements.title.value !== (it.title || '')) changed.title = form.elements.title.value;
      if (Object.keys(changed).length) {
        try {
          const saved = await call(`/api/boosts/${boostId()}/posts/${it.postId}`, 'PATCH', changed);
          if (saved && saved.caption != null) form.elements.caption.value = saved.caption;
        } catch (e) {
          const d = (e && e.detail) || {};
          if (error) error.textContent = d.message || (e && e.message) || 'That didn’t save.';
          return;
        }
      }
    }
    return baseSave(i, form);
  };

  // ------------------------------------------------------------------ swap a photo
  window.pickHomePhoto = async function (i) {
    const r = activeReview(), it = r && r.items[i], id = boostId();
    if (!it || id == null) return;
    let photos = [];
    try { const g = (await RM.gallery(id)) || {}; photos = (g.photos || []).filter(a => (a.kind || 'photo') === 'photo'); } catch (e) {}
    show(`<span class="eyebrow">DAY ${it.day} · SWAP THE PHOTO</span><h2>Pick a photo of this home.</h2><p>Resmara redraws this post on the photo you pick, with the same words, style and your details.</p>
      <div class="swap-grid">${photos.map(a => `<button type="button" onclick="swapHomePhoto(${i},${Number(a.id)})"><img src="${esc(mediaPath(a.url))}" alt="${esc(a.room || 'Listing photo')}" loading="lazy"><small>${esc(a.room || '')}</small></button>`).join('') || '<p class="fine">No photos on this campaign yet.</p>'}</div>
      <p class="fine" id="swap-status" role="status"></p>
      <div class="modal-actions"><button type="button" class="campaign-primary navy" onclick="editCampaignItem(${i})">Back</button><label class="campaign-primary swap-upload">Upload your own<input type="file" accept="image/*" style="display:none" onchange="uploadAndSwap(${i},this)"></label></div>`);
    modal.classList.add('wide-modal');
  };
  window.swapHomePhoto = async function (i, assetId) {
    const r = activeReview(), it = r && r.items[i], s = document.getElementById('swap-status');
    if (s) s.textContent = 'Redrawing this post on the new photo…';
    modal.querySelectorAll('.swap-grid button').forEach(b => { b.disabled = true; });
    try {
      const res = await call(`/api/boosts/${boostId()}/posts/${it.postId}/photo`, 'POST', { asset_id: assetId });
      it.image = res.image_url; it.needsLook = !!res.needs_look; it.reviewed = false; persist();
      modal.classList.remove('wide-modal'); editCampaignItem(i);
      toast(res.needs_look ? 'Swapped. It uses Resmara’s own layout, so give it a look.' : 'Swapped and redrawn.');
    } catch (e) {
      if (s) s.textContent = (e && e.message) || 'That photo couldn’t be used. Try another.';
      modal.querySelectorAll('.swap-grid button').forEach(b => { b.disabled = false; });
    }
  };
  // Upload your own: saved as a JPEG to this home's photos, then the post is redrawn on it.
  window.uploadAndSwap = async function (i, input) {
    const file = input.files && input.files[0]; if (!file) return;
    const s = document.getElementById('swap-status'); if (s) s.textContent = 'Uploading…';
    try {
      const jpeg = await compressToJpeg(file);
      const blob = await (await fetch(jpeg)).blob();
      const up = await RM.uploadPhoto(new File([blob], 'photo.jpg', { type: 'image/jpeg' }), boostId(), 'photo');
      const assetId = up && (up.asset_id != null ? up.asset_id : up.id);
      if (assetId == null) throw new Error('The upload didn’t come back with a photo id.');
      await swapHomePhoto(i, assetId);
    } catch (e) { if (s) s.textContent = (e && e.message) || 'The upload didn’t work.'; }
  };
})();
