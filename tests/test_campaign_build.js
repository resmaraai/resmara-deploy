#!/usr/bin/env node
'use strict';
/*
 * static/campaign-build.js (Engine 4 on the review screen):
 *  - the Gallery view shows each post with its day, time, caption and 👍 / 👎, and "Needs a look";
 *  - times are shown in the agent's own time (the server stores UTC);
 *  - a caption edit is saved on the server first; a Fair Housing refusal stops the save.
 * Run: node tests/test_campaign_build.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

let checks = 0, failures = 0;
function ok(name, cond, extra) {
  checks++;
  if (cond) console.log('  PASS  ' + name);
  else { failures++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}

const calls = [];
let refuse = false;
const review = { items: [
  { postId: 11, day: 1, kind: 'Photo post', title: 'Just listed', caption: 'Morning light.\n\n#ReddingHomes', image: '/uploads/post-01-a.png' },
  { postId: 12, day: 2, kind: 'Photo post', title: 'The coffee corner', caption: 'Coffee here.', image: '/uploads/post-02-b.png' },
  { kind: 'Meta ad', day: 1, title: 'Ad' }] };
const ctx = {
  console, Promise, JSON, String, Number, Object, Date, isNaN,
  state: { calView: 'calendar' }, persist() {}, toast() {}, details() {}, ReviewStudio: { active: 0 },
  esc: s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])),
  mediaPath: s => s, niceDate: d => d, time12: t => t, reviewSlot: () => ({ date: '2026-12-01', time: '18:00' }),
  activeReview: () => review, reviewCampaignBoostId: () => 7,
  reviewCalendar: () => '<details><summary>Campaign calendar</summary><div class="review-month-scroll">GRID</div><p class="fine">notes</p></details>',
  editCampaignItem() {}, saveReviewItem: async () => { calls.push('base-save'); },
  modal: { querySelector() { return null; }, querySelectorAll() { return []; }, classList: { add() {}, remove() {} } },
  document: { getElementById() { return null; } },
  RM: {
    isLoggedIn: () => true,
    posts: async () => [
      { id: 11, rating: 1, needs_look: false, design_style: 'full_photo', caption_ig: 'Morning light. Comment TOUR', publish_at: '2026-12-02T02:00:00', image_url: '/uploads/post-01-a.png' },
      { id: 12, rating: null, needs_look: true, design_style: 'framed', publish_at: '2026-12-03T02:00:00', image_url: '/uploads/post-02-b.png' }],
    request: async (p, o) => {
      calls.push((o && o.method || 'GET') + ' ' + p + ' ' + (o && o.body || ''));
      if (refuse) { const e = new Error('no'); e.detail = { error: 'fair_housing', message: 'This can’t be saved: Fair Housing.' }; throw e; }
      return { caption: JSON.parse(o.body).caption };
    },
  },
};
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'static', 'campaign-build.js'), 'utf8'), ctx);

(async () => {
  await ctx.RM.posts(7);
  let html = ctx.reviewCalendar(review, {});
  ok('Calendar | Gallery toggle, the calendar grid kept', html.includes('cal-views') && html.includes('GRID'));
  ok('Ads run 6 AM to 11 PM under the ad', html.includes('Ads run 6 AM to 11 PM.'));
  ok('times shown in the agent’s own time, not UTC', review.items[0].time && review.items[0].time !== '02:00', review.items[0].time);
  ok('designed posts are marked so their words aren’t printed twice', review.items[0].designed === true);
  ctx.state.calView = 'gallery';
  html = ctx.reviewCalendar(review, {});
  ok('Gallery: a card per post, not the ad', (html.match(/class="pg-card"/g) || []).length === 2 && !html.includes('GRID'));
  ok('Gallery: 👍 / 👎 on every card, with the current one marked', (html.match(/class="thumb( on)?"/g) || []).length === 4 && html.includes('thumb on'));
  ok('Gallery: Needs a look on the flagged post', html.includes('Needs a look'));
  ok('Gallery: the caption without its hashtags', html.includes('Morning light.') && !html.includes('#ReddingHomes'));

  const form = { elements: { caption: { value: 'Perfect for your growing family.' }, title: { value: 'Just listed' } }, querySelector: () => ({ textContent: '' }) };
  const err = { textContent: '' };
  form.querySelector = () => err;
  refuse = true;
  await ctx.saveReviewItem(0, form);
  ok('a Fair Housing refusal stops the save and says why', !calls.includes('base-save') && /Fair Housing/.test(err.textContent), err.textContent);
  refuse = false;
  form.elements.caption.value = 'Coffee by the big window.';
  await ctx.saveReviewItem(0, form);
  ok('an edit is saved on the server, then locally', calls.some(c => c.startsWith('PATCH /api/boosts/7/posts/11')) && calls.includes('base-save'));

  console.log(`\n${checks} checks, ${failures} failed.`);
  if (failures) process.exit(1);
  console.log('ALL CAMPAIGN BUILD CHECKS PASSED');
})().catch(e => { console.error(e); process.exit(1); });
