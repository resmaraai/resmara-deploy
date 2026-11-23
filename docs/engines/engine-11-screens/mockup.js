// Review copy only: Engine 1, Part C mockup (PR #18). Not part of PR #17.
//   #audit  Continue with Facebook -> live checklist -> "Here's what we found".
(function () {
  const css = `
  .af-pick{display:grid;gap:8px;margin:14px 0}
  .af-pick label{display:flex;gap:10px;align-items:flex-start;border:1px solid #d8effd;background:#fff;border-radius:12px;padding:10px 12px;cursor:pointer;color:#12354d}
  .af-pick small{display:block;color:#12354d;opacity:.8}
  .af-found{list-style:none;margin:14px 0;padding:0;display:grid;gap:8px}
  .af-found li{display:flex;gap:12px;align-items:center;background:#e2f0f8;border-radius:12px;padding:10px 12px;color:#12354d}
  .af-av{flex:0 0 44px;height:44px;border-radius:50%;background:#12354d;color:#fff;display:grid;place-items:center;font-weight:600;font-size:15px}
  .af-av.ig{background:#d94c0d}.af-av.none{background:#fff;color:#12354d;border:1px dashed #12354d}
  .af-txt{flex:1;min-width:0}.af-txt small{display:block;color:#12354d;opacity:.85}
  .af-txt em{font-style:normal;font-size:12px;letter-spacing:.06em;text-transform:uppercase;display:block;margin-bottom:1px}
  .af-st{flex:0 0 auto;font-weight:600;font-size:13px;padding:4px 10px;border-radius:999px}
  .af-st.ok{background:#12354d;color:#fff}.af-st.bad{background:#d94c0d;color:#fff}
  .af-mean{margin:4px 0 0;font-size:13px;color:#12354d}
  .af-pages{list-style:none;margin:14px 0;padding:0;display:grid;gap:8px}
  .af-pages button{width:100%;display:flex;gap:12px;align-items:center;text-align:left;background:#fff;border:1px solid #d8effd;border-radius:12px;padding:10px 12px;color:#12354d;cursor:pointer}
  .af-pages button:hover{background:#eef8ff}
  .af-tag{margin-left:auto;font-size:12px;background:#e2f0f8;color:#12354d;border-radius:999px;padding:3px 9px}
  .af-note{font-size:13px;color:#12354d;margin-top:10px}
  .fl-card{background:#e2f0f8;border-radius:14px;padding:14px 16px;margin-top:12px;color:#12354d}
  .fl-card h3{margin:0 0 8px;font-size:17px;color:#12354d;display:flex;align-items:center;gap:8px}
  .fl-tick{width:22px;height:22px;border-radius:50%;background:#12354d;color:#fff;display:inline-grid;place-items:center;font-size:12px}
  .fl-tick.todo{background:#d94c0d}
  .fl-kit{display:flex;gap:14px;align-items:center;background:#fff;border-radius:12px;padding:12px}
  .fl-logo{flex:0 0 52px;height:52px;border-radius:50%;background:#2F4F3E;color:#fff;display:grid;place-items:center;font:600 18px 'Playfair Display',serif}
  .fl-sw{display:flex;gap:5px;margin-top:6px}.fl-sw i{width:22px;height:22px;border-radius:6px;border:1px solid #d8effd}
  .fl-name{font:600 19px 'Playfair Display',serif;color:#2F4F3E}
  .fl-voice{font-size:13px;margin:8px 0 0;color:#12354d}
  .fl-row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:7px 0;border-top:1px solid #d8effd;font-size:14px}
  .fl-row:first-of-type{border-top:0}
  .fl-row .af-st{font-size:12px;padding:3px 9px}
  .fl-sub{font-size:13px;margin:6px 0 0}
  .fl-btns{display:flex;justify-content:flex-end;gap:8px;margin-top:10px;flex-wrap:wrap}
  .fl-btns button{padding:9px 16px;font-size:14px}
  .vc-sec textarea{width:100%;min-height:150px;font-size:15px;line-height:1.5}
  .vc-note{font-size:13px;color:#12354d;margin-top:6px}
  .mb-field.miss input{border:2px solid #d94c0d!important;background:#fff6f1}
  .mb-field.miss span{color:#d94c0d}
  #modal.af-locked > .close{display:none}
  .af-dot{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;background:#d94c0d;color:#fff;font-size:12px;font-weight:700;margin-left:auto;flex:0 0 auto}
  .side-nav button{display:flex;align-items:center}
  .af-attn{display:flex;align-items:center;gap:10px;background:#e2f0f8;color:#12354d;border-radius:12px;padding:10px 14px;margin:0 0 18px;font-size:15px}
  .af-attn .af-dot{margin-left:0}
  .af-attn span:nth-child(2){flex:1}.af-attn button{padding:8px 16px;font-size:14px}
  .af-bot{width:40px;height:40px;flex:0 0 40px}
  .gd-head{display:flex;gap:12px;align-items:center;margin-bottom:6px}
  .gd-head .robot-avatar{width:54px;height:54px;flex:0 0 54px}
  .gd-steps{list-style:none;padding:0;margin:14px 0;display:grid;gap:8px}
  .gd-steps li{display:flex;gap:12px;align-items:flex-start;background:#e2f0f8;border-radius:12px;padding:10px 12px;color:#12354d}
  .gd-steps li span{flex:0 0 26px;height:26px;border-radius:50%;background:#d94c0d;color:#fff;display:grid;place-items:center;font-weight:700;font-size:13px}
  .gd-steps a{color:#12354d;text-decoration:underline}
  .gd-win{text-align:center}.gd-win .robot-avatar{width:84px;height:84px;margin:0 auto 6px;display:block}
  .gd-ok{width:56px;height:56px;border-radius:50%;background:#12354d;color:#fff;display:grid;place-items:center;font-size:28px;margin:6px auto}
  .gd-count{font-size:13px;color:#12354d}
  .af-note-box{display:flex;align-items:center;gap:14px;background:#e2f0f8;color:#12354d;border-radius:14px;padding:14px 18px;margin:0 0 18px}
  .af-note-box .af-dot{margin-left:0}.af-note-box div{flex:1}.af-note-box p{margin:2px 0 0;font-size:14px}
  .ns{background:#fff;border:1px solid #d8effd;border-radius:16px;padding:18px 20px;margin:0 0 22px;color:#12354d}
  .ns h2{margin:0 0 4px;font-size:22px}
  .ns > p{margin:0 0 10px}
  .mb-field.miss em{color:#d94c0d!important}.mb-field.miss em:before,.mb-field.miss em:after{content:none!important}
  .su-or{display:flex;align-items:center;gap:10px;margin:16px 0 6px;color:#12354d;font-size:13px}
  .su-or:before,.su-or:after{content:"";flex:1;height:1px;background:#d8effd}
  .su-fb,.su-g{width:100%;display:flex;align-items:center;justify-content:center;gap:10px;border-radius:999px;padding:13px 18px;font-weight:600;font-size:16px;cursor:pointer;border:0}
  .su-fb{background:#1877f2;color:#fff;margin-top:14px}
  .su-g{background:#fff;color:#12354d;border:1px solid #12354d;margin-top:10px}
  .su-ico{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-family:Arial,sans-serif;font-size:15px}
  .su-fb .su-ico{background:#fff;color:#1877f2}.su-g .su-ico{background:#12354d;color:#fff;font-size:13px}
  .su-why{background:#e2f0f8;border-radius:12px;padding:10px 14px;color:#12354d;font-size:14px;margin-top:12px}
  .fbw .fb-mock-body{text-align:left}
  .fbw .fb-head{display:flex;gap:10px;align-items:center;justify-content:center;margin-bottom:10px}
  .fbw .fb-logo{width:30px;height:30px;border-radius:50%;background:#1877f2;color:#fff;display:grid;place-items:center;font:800 20px Arial,sans-serif}
  .fbw .fb-x{color:#606770;font-size:18px}
  .fbw .fb-av{width:64px;height:64px;border-radius:50%;background:#12354d;color:#fff;display:grid;place-items:center;font-weight:700;font-size:22px;margin:4px auto 10px}
  .fbw .fb-center{text-align:center}
  .fbw .fb-sec{margin:14px 0 0}
  .fbw .fb-sec b{display:block;font-size:14px;color:#1c1e21;margin-bottom:6px}
  .fbw .fb-item{display:flex;align-items:center;gap:10px;border:1px solid #dde1e6;border-radius:8px;padding:8px 10px;margin-top:6px;font-size:14px;color:#1c1e21}
  .fbw .fb-item input{width:18px;height:18px;margin:0;accent-color:#1877f2}
  .fbw .fb-sq{width:28px;height:28px;border-radius:6px;background:#e4e6eb;display:grid;place-items:center;font-size:11px;font-weight:700;color:#1c1e21}
  .fbw .fb-none{font-size:13px;color:#606770;padding:6px 0}
  .fbw .fb-perm{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid #eef0f2;font-size:14px;color:#1c1e21}
  .fbw .fb-tog{width:38px;height:22px;border-radius:999px;background:#1877f2;position:relative;flex:0 0 auto}
  .fbw .fb-tog:after{content:"";position:absolute;right:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#fff}
  .fbw .fb-fine{font-size:12px;color:#606770;margin-top:10px}
  .fbw .fb-done{width:54px;height:54px;border-radius:50%;background:#e7f3ff;color:#1877f2;display:grid;place-items:center;font-size:28px;margin:6px auto 10px}
  .af-todo{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:10px}
  .af-todo li{display:flex;gap:14px;align-items:flex-start;background:#e2f0f8;border-radius:14px;padding:14px 16px;color:#12354d}
  .af-todo li.done{background:#fff;border:1px solid #d8effd}
  .af-num{flex:0 0 32px;height:32px;border-radius:50%;background:#d94c0d;color:#fff;display:grid;place-items:center;font-weight:700}
  .af-todo li.done .af-num{background:#12354d}
  .acc-one{background:#e2f0f8;border-radius:14px;padding:6px 16px;gap:0!important}
  .acc-one li,.acc-one li.done{background:none!important;border:0!important;border-radius:0!important;padding:10px 0!important;border-top:1px solid #d8effd!important}
  .acc-one li:first-child{border-top:0!important}
  .acc-one .af-num{width:26px;height:26px;flex:0 0 26px;font-size:13px}
  .acc-one .af-txt p{margin:2px 0 0}
  .acc-help{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
  .acc-help>div{background:#e2f0f8;border-radius:14px;padding:14px 16px;color:#12354d}
  .acc-help p{margin:8px 0 0;font-size:14px;color:#12354d}
  .af-todo .af-txt p{margin:4px 0 0;font-size:14px}
  .af-todo .af-act{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
  .af-todo .af-act button{padding:8px 14px;font-size:14px}
  .af-meta{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:16px;color:#12354d;font-size:14px}
  .ob-skip,.ob-skip *{color:#12354d}
  .af-st.info{background:#e2f0f8;color:#12354d;font-weight:500}
  .tour-fix{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 2px}
  .tour-fix button{padding:9px 16px;font-size:14px}
  .campaign-primary.navy{background:#12354d!important;color:#fff!important}
  .af-save{display:flex;gap:12px;align-items:flex-start;background:#e2f0f8;border-radius:12px;padding:12px 14px;margin:14px 0 4px;color:#12354d;cursor:pointer}
  .af-save input{width:20px;height:20px;margin:2px 0 0;accent-color:#d94c0d;flex:0 0 auto}
  .sp-list{list-style:none;margin:14px 0 4px;padding:0;display:grid;gap:8px}
  .sp{display:flex;gap:12px;align-items:flex-start;border:1px solid #d8effd;background:#fff;border-radius:14px;padding:12px 14px;color:#12354d}
  .sp.open{background:#e2f0f8;border-color:#e2f0f8}
  .sp.done{background:#fff}
  .sp-num{flex:0 0 30px;height:30px;border-radius:50%;background:#d94c0d;color:#fff;display:grid;place-items:center;font-weight:700}
  .sp.done .sp-num{background:#12354d}
  .sp:not(.open):not(.done) .sp-num{background:#fff;color:#12354d;border:2px solid #12354d}
  .sp-txt{flex:1;min-width:0}.sp-txt small{display:block;font-size:13px;color:#12354d;margin-top:2px}.sp-txt p{margin:6px 0 0;font-size:14px}
  .sp .gd-steps li{background:#fff}
  .sp-note{background:#fff;border-radius:10px;padding:8px 12px}
  .sp-act{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
  .sp-left{display:flex;gap:8px;flex-wrap:wrap}
  .sp-tut{text-decoration:none;display:inline-flex;align-items:center}
  .sp-checking{display:flex;align-items:center;gap:8px;font-weight:600;color:#12354d}.sp-checking .robot-avatar{width:30px;height:30px}
  .sg-video{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;aspect-ratio:16/9;background:#12354d;color:#fff;border-radius:14px;margin:10px 0 12px;text-align:center;padding:14px}
  .sg-video b{color:#fff;font-size:15px}.sg-video small{color:#fff;opacity:.85;font-size:12px;letter-spacing:0;text-transform:none}
  .sg-play{width:54px;height:54px;border-radius:50%;background:#d94c0d;position:relative;margin-bottom:6px}
  .sg-play:after{content:"";position:absolute;left:21px;top:16px;border-style:solid;border-width:11px 0 11px 17px;border-color:transparent transparent transparent #fff}
  .sg-card.sg-focus{outline:3px solid #d94c0d;outline-offset:4px}
  .af-locked-card{position:relative}
  .af-locked-card img{filter:blur(4px)}
  .af-lock-tag{position:absolute;top:12px;left:12px;z-index:2;background:#12354d;color:#fff;font-weight:600;font-size:13px;border-radius:999px;padding:6px 12px}
  .sx{border:1px solid #d8effd;border-radius:14px;padding:14px;margin:12px 0 4px;background:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
  .sx-wallets{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .sx-wallet{background:#000;color:#fff;border-radius:8px;text-align:center;padding:10px;font-weight:600;font-size:14px}
  .sx-or{display:flex;align-items:center;gap:10px;color:#6b7c93;font-size:13px;margin:12px 0 6px}.sx-or:before,.sx-or:after{content:"";flex:1;height:1px;background:#e3e8ee}
  .sx-label{font-size:13px;color:#30313d;margin:8px 0 4px}
  .sx-box{border:1px solid #e3e8ee;border-radius:8px;overflow:hidden;box-shadow:0 1px 1px rgba(0,0,0,.03)}
  .sx-f{padding:10px 12px;color:#8792a2;font-size:15px;display:flex;justify-content:space-between;align-items:center}
  .sx-num{border-bottom:1px solid #e3e8ee}.sx-row,.sx-row2{display:grid;grid-template-columns:1fr 1fr}.sx-row .sx-f:first-child,.sx-row2 .sx-f:first-child{border-right:1px solid #e3e8ee}
  .sx-brands{display:flex;gap:4px}.sx-brands i{font-style:normal;font-size:9px;font-weight:700;border:1px solid #e3e8ee;border-radius:3px;padding:1px 3px;color:#30313d}
  .sx-err{border-color:#df1b41}.sx-msg{color:#df1b41;font-size:13px;margin-top:6px}
  .sx-foot{font-size:12px;color:#6b7c93;margin-top:10px;text-align:center}.sx-foot b{color:#635bff}
  .sx-saved{display:flex;align-items:center;gap:12px;background:#e2f0f8;border-radius:12px;padding:12px 14px;margin:12px 0 4px;color:#12354d}
  .sx-saved small{display:block;font-size:13px}.sx-saved span:nth-child(2){flex:1}.sx-saved button{padding:8px 14px;font-size:14px}
  .sx-card{background:#12354d;color:#fff;border-radius:6px;font-size:11px;font-weight:800;padding:6px 8px}
  .af-unlock{align-items:flex-start;padding-top:20px}
  .ls-hint{display:flex;gap:10px;align-items:flex-start;background:#e2f0f8;border-radius:12px;padding:10px 14px;color:#12354d;font-size:14px;margin:10px 0}
  .ls-hint .robot-avatar{width:34px;height:34px;flex:0 0 34px}
  .ls-facts{display:flex;gap:14px;align-items:center;background:#e2f0f8;border-radius:14px;padding:12px;margin:12px 0;color:#12354d}
  .ls-facts img{width:120px;height:84px;object-fit:cover;border-radius:10px;flex:0 0 auto}
  .ls-facts small{display:block;font-size:12px;margin-top:6px;color:#12354d}
  .ls-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}.ls-chips span{background:#fff;border-radius:999px;padding:3px 10px;font-size:13px;font-weight:600}
  .ls-found{list-style:none;padding:0;margin:8px 0;display:grid;gap:6px}
  .ls-found li{display:flex;gap:8px;font-size:14px;color:#12354d}.ls-found li b{flex:0 0 auto}
  .ls-found li:before{content:"✓";color:#fff;background:#12354d;border-radius:50%;width:20px;height:20px;display:inline-grid;place-items:center;font-size:12px;flex:0 0 20px}
  .cv-toggle{display:inline-flex;background:#e2f0f8;border-radius:999px;padding:4px;margin:6px 0 12px}
  .cv-toggle button{border:0;background:none;color:#12354d;font-weight:600;padding:7px 16px;border-radius:999px;cursor:pointer}
  .cv-toggle button.on{background:#12354d;color:#fff}
  .cv-gallery{display:none;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px;margin:4px 0 14px}
  .cv-show-gallery .cv-gallery{display:grid}.cv-show-gallery .review-month-scroll{display:none}
  .cv-card{background:#fff;border:1px solid #d8effd;border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
  .cv-img{position:relative;border:0;padding:0;cursor:pointer;display:block;aspect-ratio:4/5;background:#e2f0f8}
  .cv-img img{width:100%;height:100%;object-fit:cover;display:block}
  .cv-img .post-overlay{position:absolute;left:12px;right:12px;bottom:12px}
  .cv-img .play-btn{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%)}
  .cv-body{padding:12px 14px 14px;color:#12354d;display:flex;flex-direction:column;gap:4px;flex:1}
  .cv-body small{font-size:12px;color:#12354d;opacity:.85}.cv-body b{font-size:15px}
  .cv-body p{margin:2px 0 6px;font-size:13px;line-height:1.45;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
  .cv-rate{display:flex;align-items:center;gap:6px;margin-top:auto;font-size:13px;color:#12354d}
  .cv-rate span{flex:1}
  .cv-rate button{border:1px solid #d8effd;background:#fff;border-radius:999px;width:38px;height:32px;cursor:pointer;font-size:15px}
  .cv-rate button.on{background:#12354d;border-color:#12354d}
  .cv-rate-modal{background:#e2f0f8;border-radius:12px;padding:8px 12px;margin-bottom:10px}
  .ad-row{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;align-items:end;margin:14px 0}
  .ad-card{margin:0}.ad-card figcaption{font-size:12px;color:#12354d;margin-top:6px;text-align:center}
  .ad-art{position:relative;aspect-ratio:4/5;border-radius:12px;overflow:hidden;background:#12354d}
  .ad-story .ad-art{aspect-ratio:9/16}
  .ad-art img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
  .ad-shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 35%,rgba(0,0,0,.72) 100%)}
  .ad-text{position:absolute;left:12px;right:12px;bottom:10px;display:flex;flex-direction:column;gap:5px}
  .ad-text b{color:#fff;font:700 22px/1.1 'Playfair Display',Georgia,serif}
  .ad-story .ad-text b{font-size:16px}
  .ad-text small{color:#fff;font-size:12px;opacity:.95}
  .ad-sig{color:#fff;font-size:9.5px;letter-spacing:.04em;opacity:.85;margin-top:3px}
.ad-play{position:absolute;top:34%;left:50%;transform:translate(-50%,-50%);z-index:2;width:44px;height:44px;border-radius:50%;background:#d94c0d;color:#fff;display:grid;place-items:center;font-size:16px}
  .ad-text b{font-size:15px}
  .ad-story .ad-art{aspect-ratio:4/5}
  .ad-sig{font-size:8.5px!important}
  .ad-copy{display:grid;grid-template-columns:2fr 1.3fr .8fr 1fr;gap:10px;background:#e2f0f8;border-radius:12px;padding:12px 14px;color:#12354d}
  .ad-copy small{font-size:11px;letter-spacing:.08em;font-weight:700}.ad-copy p{margin:2px 0 0;font-size:14px}
  #content.af-blur-wrap{position:relative;min-height:80vh}
  #content.af-blur-wrap > *:not(.af-unlock){filter:blur(7px);pointer-events:none;user-select:none}
  .af-unlock{position:absolute;inset:0;display:flex;justify-content:center;align-items:flex-start;padding-top:40px;z-index:5}
  .af-unlock-card{background:#fff;color:#12354d;border-radius:20px;box-shadow:0 20px 60px rgba(18,53,77,.25);padding:24px 26px;max-width:560px;width:100%}
  .af-unlock-card h2{margin:6px 0 6px;color:#12354d}
  .af-save small{display:block;font-size:13px;margin-top:2px;color:#12354d}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const PAGE = { name: 'Jamie Carter Realty', init: 'JC' };
  const TEAM = { name: 'Summit Home Team', init: 'SH' };
  const IG = '@jamiecarterrealty';
  // results: [page, instagram, ad]; what each row says.
  const S = {
    personal: { label: 'Personal Facebook and Instagram only', sub: 'Most agents start here: no Page, no business Instagram, no ad account yet' },
    noIg:    { label: 'Personal Facebook only, no Instagram at all', sub: 'Nothing set up for business, and no Instagram account' },
    ready:   { label: 'Everything is set up', sub: 'Page, business Instagram, ad account with a card' },
    noAd:    { label: 'No ad account', sub: 'Most common for new agents' },
    noCard:  { label: 'Ad account, no card on it', sub: 'Meta can’t bill the ad budget' },
    igPers:  { label: 'Instagram is a personal account', sub: 'Or not linked to the Page' },
    noPage:  { label: 'No Facebook business Page', sub: 'Personal profile only' },
    several: { label: 'Manages two Pages', sub: 'Their own Page and a team Page' },
    taken:   { label: 'Page already on another Resmara account', sub: 'A teammate connected it first' },
    noLic:   { label: 'Everything set up, but no license number found', sub: 'Brand kit has a gap' }
  };
  let sc = 'personal', chosen = PAGE;
  const PERS = (k = sc) => k === 'personal' || k === 'noIg';

  modal.addEventListener('cancel', e => { if (modal.classList.contains('af-locked')) e.preventDefault(); });
  window.afPick = function () {
    modal.classList.remove('af-locked'); afActive = false; brandMissing = false; fixed.page = fixed.ig = fixed.ad = fixed.lic = false; tourResume = null; doneCount = 0; workspaceTourCleanup?.();
    show(`<span class="eyebrow">SIGN-UP TOUR MOCKUP</span><h2>A new client signs up.</h2><p>Pick how their Facebook looks, then click through sign-up, the finish pop-up, the tour and the first campaign’s payment.</p>
    <form onsubmit="event.preventDefault();afSignup(this.sc.value)"><div class="ob-scenarios">${Object.entries(S).map(([k, v]) => `<label><input type="radio" name="sc" value="${k}" ${k === sc ? 'checked' : ''}><span><b>${v.label}</b><small>${v.sub}</small></span></label>`).join('')}</div>
    <div class="modal-actions"><span></span><button class="campaign-primary">Start as a new client</button></div></form>`);
  };

  // 1. Resmara's Create your account pop-up: Facebook first.
  // One door for everyone: the top-right Client Login and Let's get started open the same pop-up.
  window.afSignup = function (k) {
    if (k) sc = k;
    show(`<span class="eyebrow">WELCOME TO RESMARA</span><h2>Log in with Facebook.</h2>
    <p>New or returning, it’s the same button. <b>Have an account?</b> You’re signed straight in. <b>New to Resmara?</b> We set up your account and connect your Page, Instagram and ad account in one go.</p>
    <button type="button" class="su-fb" onclick="afFb(1)"><span class="su-ico">f</span>Continue with Facebook</button>
    <div class="su-why"><b>No Facebook account?</b> You’ll need one to use Resmara, because it runs your marketing on Facebook and Instagram. It’s free: <a href="https://www.facebook.com/r.php" target="_blank" rel="noopener" style="color:#12354d;text-decoration:underline">create one on Facebook</a>, then come back here. A personal account is fine; we’ll help you set up the business side.</div>
    <p class="fine">Nothing is ever posted without your approval.</p>
    <p class="fine ob-skip">Preview (${esc(S[sc].label)}): <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try a different Meta setup</a></p>`);
  };
  // In this mockup, the site's Client Login button opens the same pop-up.
  const baseAccess = window.clientAccess;
  window.clientAccess = function (mode) { if (state.clientSignedIn) return dashboard('campaigns'); afSignup(); };

  // 2. Facebook's own window (the real one is Facebook's, opened as a pop-up).
  function fbWin(body) {
    show(`<div class="fb-mock fbw"><div class="fb-mock-bar">facebook.com · Log in with Facebook <em>PREVIEW</em></div><div class="fb-mock-body">
    <div class="fb-head"><span class="fb-logo">f</span><span class="fb-x">⇄</span><span class="robot-avatar" style="width:34px;height:34px;margin:0" aria-hidden="true"></span></div>${body}</div></div>
    <p class="fine" style="text-align:center;margin-top:10px">This is Facebook’s own window. Resmara can’t change how it looks.</p>`);
  }
  window.afGo = function () { afStart(sc); };
  window.afFb = function (step) {
    const pages = (sc === 'noPage' || PERS()) ? [] : sc === 'several' ? [[PAGE, true], [TEAM, true]] : [[PAGE, true]];
    const igs = (sc === 'noPage' || sc === 'igPers' || PERS()) ? [] : [IG];
    const ads = (sc === 'noAd' || PERS()) ? [] : ['Jamie Carter Realty'];
    const item = (sq, name, on) => `<label class="fb-item"><input type="checkbox" ${on ? 'checked' : ''}><span class="fb-sq">${sq}</span>${name}</label>`;
    const none = t => `<div class="fb-none">${t}</div>`;
    if (step === 1) return fbWin(`<div class="fb-center"><div class="fb-av">JC</div><h3>Continue as Jamie?</h3>
      <p>Resmara will receive your name, profile picture and email address.</p></div>
      <div class="fb-mock-actions" style="flex-direction:column;align-items:stretch"><button type="button" class="fb-continue" onclick="afFb(2)">Continue as Jamie</button><button type="button" class="fb-cancel" onclick="afSignup()">Cancel</button></div>
      <p class="fb-fine" style="text-align:center">Resmara’s Privacy Policy and Terms</p>`);
    if (step === 2) return fbWin(`<h3 style="text-align:center">Choose what Resmara can access</h3><p style="text-align:center">Pick the Page, Instagram account and ad account for your listings.</p>
      <div class="fb-sec"><b>Pages</b>${pages.length ? pages.map(([p, on]) => item(p.init, p.name, on)).join('') : none('You don’t manage any Pages.')}</div>
      <div class="fb-sec"><b>Instagram accounts</b>${igs.length ? igs.map(i => item('IG', i, true)).join('') : none('No Instagram business accounts are linked to your Pages.')}</div>
      <div class="fb-sec"><b>Ad accounts</b>${ads.length ? ads.map(a => item('Ad', a, true)).join('') : none('You don’t have any ad accounts.')}</div>
      <div class="fb-mock-actions"><button type="button" class="fb-cancel" onclick="afFb(1)">Back</button><button type="button" class="fb-continue" onclick="afFb(3)">Continue</button></div>`);
    if (step === 3) return fbWin(`<h3 style="text-align:center">Review what Resmara can do</h3>
      <div class="fb-sec">${['Create and manage posts on your Page', 'Publish posts to your Instagram account', 'Create and manage ads in your ad account', 'Read how your posts and ads perform', 'Receive messages and comments from your Page'].map(t => `<div class="fb-perm">${t}<span class="fb-tog"></span></div>`).join('')}</div>
      <p class="fb-fine">You can change or remove Resmara’s access at any time in your Facebook settings.</p>
      <div class="fb-mock-actions"><button type="button" class="fb-cancel" onclick="afFb(2)">Back</button><button type="button" class="fb-continue" onclick="afFb(4)">Save</button></div>`);
    return fbWin(`<div class="fb-center"><div class="fb-done">✓</div><h3>You’ve now linked Resmara to Facebook</h3><p>Resmara can now access what you chose.</p></div>
      <div class="fb-mock-actions"><button type="button" class="fb-continue" onclick="afGo()">Got it</button></div>`);
  };

  window.afStart = function (k) {
    sc = k; chosen = PAGE;
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>Welcome, Jamie. Your account is ready.</h2><p>Now Resmara is checking your Facebook and building your brand kit. This takes a couple of minutes.</p><div id="ob-box"></div>`);
    modal.classList.add('af-locked');
    const labels = [
      ['Signing you in with Facebook', 'Signed in as Jamie Carter', ''],
      ['Finding your Facebook Page', (k === 'noPage' || PERS(k)) ? 'No business Page found' : k === 'several' ? 'Found 2 Pages' : 'Found ' + PAGE.name, (k === 'noPage' || PERS(k)) ? 'No business Page yet' : ''],
      ['Checking your Instagram', 'Found ' + IG, k === 'noIg' ? 'No Instagram account found' : PERS(k) ? 'Your Instagram is a personal account' : k === 'noPage' ? 'No Page to check Instagram on' : 'Instagram isn’t a business account'],
      ['Checking your ad account', 'Found Jamie Carter Realty ad account', (k === 'noAd' || PERS(k)) ? 'No ad account yet' : 'Ad account has no card on it'],
      ['Looking at your posts', PERS(k) ? 'Studied your website and public profiles' : 'Read your last 30 posts', ''],
      ['Researching you and your brokerage', 'Found your license, brokerage and website', ''],
      ['Building your brand kit', 'Your brand kit is built', '']
    ];
    const res = [true, !(k === 'noPage' || PERS(k)), !(k === 'igPers' || k === 'noPage' || PERS(k)), !(k === 'noAd' || k === 'noCard' || PERS(k)), true, true, true];
    obWalk(document.querySelector('#ob-box'), labels, res, '', () => k === 'several' ? afPages() : k === 'taken' ? afResult() : afFinish());
  };

  function afPages() {
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>Which Page is your business?</h2><p>You manage two Facebook Pages. Pick the one Resmara should post to. You can change it later in Accounts.</p>
    <ul class="af-pages">
      <li><button onclick="afChoose(0)"><span class="af-av">${PAGE.init}</span><span><b>${PAGE.name}</b><small style="display:block">Real estate agent</small></span><span class="af-tag">Has Instagram</span></button></li>
      <li><button onclick="afChoose(1)"><span class="af-av">${TEAM.init}</span><span><b>${TEAM.name}</b><small style="display:block">Real estate team</small></span></button></li>
    </ul>`);
  }
  window.afChoose = function (i) { chosen = i ? TEAM : PAGE; afFinish(); };

  function row(av, avCls, kind, name, detail, ok, mean) {
    return `<li><span class="af-av ${avCls}">${av}</span><span class="af-txt"><em>${kind}</em><b>${name}</b>${detail ? `<small>${detail}</small>` : ''}${mean ? `<p class="af-mean">${mean}</p>` : ''}</span><span class="af-st ${ok ? 'ok' : 'bad'}">${ok ? '✓ Ready' : 'Needs a fix'}</span></li>`;
  }


  // The onboarding finish line: brand kit + Facebook + card + first campaign, on one screen.
  const PALETTE = [['Primary', '#2F4F3E'], ['Accent', '#C46A3C'], ['Text', '#2B2B2B'], ['Tint', '#EEF2EC'], ['Page', '#FFFFFF']];
  const VOICE = 'Jamie is warm, upbeat and very local. She sells mostly in Redding and Shasta Lake, with a lot of first-time buyers and young families moving up. Her posts read like a friendly neighbour: short, encouraging, a bit of humour, and she often says “Let’s get you home.” She celebrates clients at closing and shares local spots. Keep it personal and upbeat; avoid hype words and anything that sounds like a big-brokerage ad.';
  function frow(label, name, ok, mean) {
    return `<div class="fl-row"><span><b>${label}:</b> ${name}${mean ? `<br><small>${mean}</small>` : ''}</span><span class="af-st ${ok ? 'ok' : 'bad'}">${ok ? '✓ Ready' : 'Needs a fix'}</span></div>`;
  }
  const fixed = { page: false, ig: false, ad: false, lic: false };
  function afState() {
    const P = PERS();
    const pageOk = fixed.page || !(sc === 'noPage' || P);
    const igOk = pageOk && (fixed.ig || (!(sc === 'igPers' || sc === 'noPage' || P) && chosen === PAGE));
    const adOk = fixed.ad || !(sc === 'noAd' || sc === 'noCard' || P);
    return { pageOk, igOk, adOk, fbOk: pageOk && igOk && adOk, licOk: fixed.lic || sc !== 'noLic' };
  }
  // Sign-up tour engine, step 1: the finish pop-up. Information only: their brand and Facebook status.
  function pill(ok, txt) { return `<span class="af-st ${ok ? 'ok' : 'info'}">${ok ? '✓ ' + txt : txt}</span>`; }
  function afFinish() {
    const st = afState(), P = PERS();
    const rows = [
      ['Facebook Page', st.pageOk ? chosen.name : 'No business Page yet', st.pageOk, st.pageOk ? 'Connected' : 'Not set up yet'],
      ['Instagram', st.igOk ? IG : sc === 'noIg' ? 'No Instagram yet' : P ? 'Personal account' : !st.pageOk ? 'Needs a Page first' : chosen === TEAM ? 'None on this Page' : 'Personal account', st.igOk, st.igOk ? 'Connected' : 'Not set up yet'],
      ['Ad account', (sc === 'noAd' || P) && !fixed.ad ? 'No ad account yet' : 'Jamie Carter Realty', st.adOk, st.adOk ? 'Ready' : sc === 'noCard' ? 'No card on it' : 'Not set up yet']
    ].map(r => `<div class="fl-row"><span><b>${r[0]}:</b> ${r[1]}</span>${pill(r[2], r[3])}</div>`).join('');
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">SETUP COMPLETE</span><h2>You’re all set up, Jamie.</h2>
    <p>Here’s your brand and your Facebook. Let me show you around. It takes about a minute.</p>
    <div class="fl-card"><h3>Your brand</h3>
      <div class="fl-kit"><span class="fl-logo">JC</span><div><div class="fl-name">Jamie Carter Realty</div><small>Playfair Display · Jost · ${st.licOk ? 'DRE #02123456' : 'License number not found yet'}</small><div class="fl-sw">${PALETTE.map(p => `<i style="background:${p[1]}"></i>`).join('')}</div></div></div>
      <p class="fl-voice"><b>Voice of the client:</b> ${VOICE.split('. ').slice(0, 2).join('. ')}.</p></div>
    <div class="fl-card"><h3>Your Facebook</h3>${rows}</div>
    <div class="modal-actions"><span></span><button class="campaign-primary" onclick="afDone()">Show me around</button></div>
    <p class="fine ob-skip">Preview (${esc(S[sc].label)}): <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try another setup</a></p>`);
    modal.classList.add('af-locked');
  }
  // After setup: a clean dashboard, the Resmara tour, and notices that live on the menu items.
  let afActive = false, brandMissing = false;
  const baseDashboard = window.dashboard;
  function issues() {
    const st = afState();
    return { brand: !st.licOk || (brandMissing && !fixed.lic), card: false, fb: !st.fbOk, st };
  }
  function fbReason(st) {
    return !st.pageOk ? 'there’s no Facebook business Page connected yet'
      : !st.igOk ? 'your Instagram isn’t a business account, so posts go to Facebook only'
      : 'your ad account ' + (sc === 'noAd' ? 'is missing' : 'has no card on it') + ', so your listing ad can’t run yet';
  }
  window.dashboard = function (v) {
    if (afActive && v === 'brand') prepBrand();
    baseDashboard(v);
    if (!afActive) return;
    history.replaceState(null, '', location.pathname + (location.hash || '#tour'));
    paintMenu();
    if (v === 'brand') paintBrand();
    else if (v === 'accounts') paintAccounts();
    else if (v === 'credits') paintBilling();
    else if (!v || v === 'campaigns') { paintAttention(); paintLocked(); }
  };
  function paintMenu() {
    const is = issues();
    const flag = { brand: is.brand, credits: is.card, accounts: is.fb };
    document.querySelectorAll('.side-nav button').forEach(btn => {
      const key = (btn.getAttribute('onclick') || '').match(/dashboard\('(\w+)'\)/);
      if (key && flag[key[1]] && !btn.querySelector('.af-dot')) btn.insertAdjacentHTML('beforeend', '<span class="af-dot">!</span>');
    });
  }
  function paintAttention() {
    const q = afQueue();
    if (!q.length) return;
    const c = document.querySelector('#content'); if (!c || c.querySelector('.af-attn')) return;
    const setup = PERS() && ['page', 'ig', 'ad'].some(k => q.includes(k));
    const msg = setup ? `<b>Let’s get you set up for business.</b> ${q.filter(k => k !== 'lic').length} quick steps so I can post and run ads for you. About 10 minutes.`
      : `<b>${q.length === 1 ? 'One thing needs' : 'A few things need'} your attention.</b> Want me to walk you through ${q.length === 1 ? 'it' : 'them'}?`;
    c.insertAdjacentHTML('afterbegin', `<div class="af-attn"><span class="robot-avatar af-bot" aria-hidden="true"></span><span>${msg}</span>${setup ? `<button class="campaign-primary" style="background:#12354d;color:#fff" onclick="obBook(true)">Do it with our team</button>` : ''}<button class="campaign-primary" onclick="afGuide(afQueue()[0])">${setup ? 'Let’s do it' : 'Let’s fix it'}</button></div>`);
  }
  function paintBilling() {
    return; // the card is asked for at the first campaign, not during onboarding
    if (state.cardOnFile) return;
    const c = document.querySelector('#content'); if (!c) return;
    c.insertAdjacentHTML('afterbegin', `<div class="af-note-box"><span class="af-dot">!</span><div><b>You don’t have a card on file.</b><p>You need one to build a campaign. You pay per listing, only when you launch.</p></div><button class="campaign-primary" onclick="afGuide('card')">Add a card</button></div>`);
  }

  // Resmara walks them through each thing that needs attention, one at a time.
  window.afQueue = function () { const st = afState(); return [!st.pageOk && 'page', !st.igOk && 'ig', !st.adOk && 'ad', !st.licOk && 'lic'].filter(Boolean); };
  const BOOK = `<button type="button" class="campaign-primary" style="background:#12354d;color:#fff" onclick="afTourBook()">Do it with our team</button>`;
  function guideFor(key) {
    const st = afState();
    if (key === 'page') return { title: 'Let’s set up your Facebook business Page.', why: 'Resmara posts to a business Page, not your personal profile. Until you have one, you download each post and share it yourself.',
      steps: ['Open <a href="https://www.facebook.com/pages/create" target="_blank" rel="noopener">Facebook’s Create a Page</a>.', 'Name it for your real estate business and pick the Real Estate Agent category.', 'Add your profile photo and a cover photo, then publish it.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'ig') return { title: 'Let’s switch your Instagram to a business account.', why: 'Meta only lets Resmara post to business Instagram accounts. It’s free, takes about a minute, and you keep all your posts and followers.',
      steps: ['Open <a href="https://www.facebook.com/settings/?tab=linked_instagram" target="_blank" rel="noopener">Facebook’s linked accounts</a>, acting as your business Page.', 'Click <b>Connect account</b> next to Instagram and sign in.', 'When Facebook asks, choose <b>Business</b>.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'ad' && sc !== 'noCard') return { title: 'Let’s set up your ad account.', why: 'Your posts already go out. An ad account lets Resmara run your listing ad too, and Meta bills the ad budget to it directly.',
      steps: ['Open <a href="https://adsmanager.facebook.com" target="_blank" rel="noopener">Meta Ads Manager</a>.', 'Follow Meta’s steps to create an ad account in your name or your business name.', 'In <b>Payment settings</b>, add a card so Meta can bill your ad budget.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'ad') return { title: 'Let’s add a card to your ad account.', why: 'Your ad account is set up, but Meta needs a payment method before it can run your listing ad.',
      steps: ['Open <a href="https://business.facebook.com/billing_hub" target="_blank" rel="noopener">Meta’s Billing &amp; payments</a>.', 'Choose your ad account and click <b>Add payment method</b>.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'lic') return { title: 'Let’s add your license number.', why: 'It has to go on every post, and we couldn’t find it on your pages or in the state lookup.', field: true };
    return { title: 'Let’s add your card.', why: 'You pay per listing, only when you launch a campaign. Stripe keeps your card; Resmara never sees the number.', card: true };
  }
  function guideShell(inner) {
    const q = afQueue(), total = q.length + doneCount;
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">${PERS() ? 'GETTING YOU SET UP' : 'LET’S FIX IT TOGETHER'}</span><div class="gd-count">${doneCount + 1} of ${total}</div></div></div>${inner}`);
    modal.classList.add('af-locked');
  }
  let doneCount = 0;
  window.afGuide = function (key) {
    if (!key) return;
    if (key === 'page' || key === 'ig' || key === 'ad') return afSetup(key);
    const g = guideFor(key);
    guideShell(`<h2>${g.title}</h2><p>${g.why}</p><label class="field">License number<input id="gd-lic" placeholder="e.g. DRE #02123456"></label>
      <div class="modal-actions">${BOOK}<div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="afLater()">Later</button><button class="campaign-primary" onclick="afWin('lic')">Save it</button></div></div>`);
  };

  // The setup plan: everything they need for business on one pop-up, ticked off in place.
  const PLAN = [
    ['page', 'Facebook business Page', 'About 5 minutes'],
    ['ig', 'Instagram business account, linked to your Page', 'About 2 minutes'],
    ['ad', 'Ad account with a card', 'About 3 minutes. Your posts go out without it; it runs your listing ad']
  ];
  function igGuide() {
    return sc === 'noIg' ? { title: 'Create your Instagram business account.', why: 'Resmara posts your listing to Instagram too. It’s free and takes a couple of minutes.',
      steps: ['Download Instagram and tap <b>Create new account</b>. Use your business name.', 'Go to <b>Settings</b>, then <b>Account type and tools</b>, and switch to a <b>Business</b> account.', 'Open <a href="https://www.facebook.com/settings/?tab=linked_instagram" target="_blank" rel="noopener">Facebook’s linked accounts</a> as your business Page and connect it.', 'Come back here and press <b>Check again</b>.'] } : guideFor('ig');
  }
  window.afSetup = function (open, note) {
    const st = afState(), ok = { page: st.pageOk, ig: st.igOk, ad: st.adOk };
    open = open && !ok[open] ? open : PLAN.map(p => p[0]).find(k => !ok[k]);
    if (!open) return afSetupDone();
    const n = PLAN.filter(p => !ok[p[0]]).length;
    const items = PLAN.map(([k, t, time], i) => {
      if (ok[k]) return `<li class="sp done"><span class="sp-num">✓</span><div class="sp-txt"><b>${t}</b><small>${fixed[k] ? 'Done just now' : 'Already set up'}</small></div></li>`;
      if (k !== open) return `<li class="sp"><span class="sp-num">${i + 1}</span><div class="sp-txt"><b>${t}</b><small>${k === 'ig' && !ok.page ? 'After your Page' : time}</small></div></li>`;
      const g = k === 'ig' ? igGuide() : guideFor(k);
      return `<li class="sp open"><span class="sp-num">${i + 1}</span><div class="sp-txt"><b>${t}</b><p>${g.why}</p>
        ${note ? `<p class="sp-note"><b>Not quite yet.</b> Meta still shows the same thing. Sometimes it takes a few minutes to update.</p>` : ''}
        <ol class="gd-steps">${g.steps.map((x, j) => `<li><span>${j + 1}</span><div>${x}</div></li>`).join('')}</ol>
        <div class="sp-act"><span class="sp-left"><button type="button" class="campaign-primary navy" onclick="afTourBook()">Do it with our team</button><button type="button" class="campaign-primary navy" onclick="window.open(location.pathname + '#setup-guides-${k === 'ad' ? 'ads' : k === 'ig' ? 'instagram' : 'page'}', '_blank', 'noopener')">See the tutorial</button></span><button class="campaign-primary" onclick="afSetupCheck('${k}')">${note ? 'Try again' : 'Check again'}</button></div>
        <p class="fine ob-skip" style="text-align:left">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afSetupCheck('${k}',true);return false">see what happens if it’s not done yet</a></p></div></li>`;
    }).join('');
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">GETTING YOU SET UP FOR BUSINESS</span><div class="gd-count">${n === 1 ? 'One thing left' : n + ' things left'} · about ${n === 3 ? 10 : n === 2 ? 7 : 5} minutes</div></div></div>
      <h2>Let’s get you set up for business.</h2><p>To post and run ads for you, Resmara needs these three things. I’ll walk you through each one, or our team can do it with you.</p>
      <ul class="sp-list">${items}</ul>
      <div class="modal-actions"><span></span><button type="button" class="nc-cancel" onclick="afLater()">Later</button></div>`);
    modal.classList.add('af-locked');
  };
  window.afSetupCheck = function (key, fail) {
    const li = document.querySelector('.sp.open .sp-act');
    if (li) li.innerHTML = '<span class="sp-checking"><span class="robot-avatar" aria-hidden="true"></span>Checking with Meta…</span>';
    setTimeout(() => { if (!fail) fixed[key] = true; afSetup(fail ? key : null, !!fail); }, 1200);
  };
  function afSetupDone() {
    const lic = afQueue().includes('lic');
    show(`<div class="gd-win"><span class="robot-avatar" aria-hidden="true"></span><div class="gd-ok">✓</div><h2>You’re set up for business, Jamie.</h2>
      <p>I can post to your Page and Instagram and run your listing ads now.${lic ? ' One last thing: your license number.' : ''}</p></div>
      <ul class="sp-list">${PLAN.map(([k, t]) => `<li class="sp done"><span class="sp-num">✓</span><div class="sp-txt"><b>${t}</b></div></li>`).join('')}</ul>
      <div class="modal-actions"><span></span>${lic ? `<button class="campaign-primary" onclick="afGuide('lic')">Add my license number</button>` : tourResume != null ? `<button class="campaign-primary" onclick="afLater()">Continue the tour</button>` : `<button class="campaign-primary" onclick="afLater(true)">Start a campaign</button>`}</div>`);
    modal.classList.add('af-locked');
  }
  window.afWin = function (key) {
    fixed[key] = true;
    const next = afQueue()[0];
    show(`<div class="gd-win"><span class="robot-avatar" aria-hidden="true"></span><div class="gd-ok">✓</div><h2>Saved. It’s on every post now.</h2><p>${next ? 'Next, let’s get you set up for business.' : 'That’s everything. You’re ready to build your first campaign.'}</p></div>
      <div class="modal-actions"><span></span>${next ? `<button class="campaign-primary" onclick="afGuide('${next}')">Let’s go</button>` : tourResume != null ? `<button class="campaign-primary" onclick="afLater()">Continue the tour</button>` : `<button class="campaign-primary" onclick="afLater(true)">Start a campaign</button>`}</div>`);
    modal.classList.add('af-locked');
  };
  window.afLater = function (start) {
    modal.classList.remove('af-locked'); modal.close(); doneCount = 0;
    if (tourResume != null) { const i = tourResume; tourResume = null; return workspaceTour(i); }
    const v = (document.querySelector('.side-nav button.active') || {}).getAttribute ? (document.querySelector('.side-nav button.active').getAttribute('onclick') || '').match(/dashboard\('(\w+)'\)/) : null;
    dashboard(start ? 'campaigns' : (v ? v[1] : 'campaigns'));
    if (start) toast('Preview: this opens a new campaign.');
  };

  // Sign-up tour engine, step 2: the tour. Anything that needs fixing first, then where
  // everything is, ending on "Let's start your first campaign".
  let tourResume = null;
  window.afDone = function () {
    modal.classList.remove('af-locked'); modal.close();
    afActive = true; state.metaIssues = []; state.cardOnFile = false; state.firstRun = true; state.tourDone = false; state.clientSignedIn = true; state.connected = true;
    const is = issues(), P = PERS();
    const fix = (key, label) => `<div class="tour-fix"><button type="button" class="campaign-primary" onclick="afTourFix('${key}')">${label}</button><button type="button" class="campaign-primary navy" onclick="afTourBook()">Do it with our team</button></div>`;
    const steps = [];
    if (is.fb) steps.push({ page: 'accounts', sel: '.meta-card', title: P ? 'First, let’s get you set up for business.' : 'First, let’s sort out your Facebook.',
      text: sc === 'noIg' ? 'You’re starting with a personal Facebook and no Instagram yet. To post and run ads for you, I need a business Page and a business Instagram. About 10 minutes, and I’ll walk you through it.' : P ? 'Like most agents, you’re starting with a personal Facebook and Instagram. To post and run ads for you, I need a business Page and a business Instagram. About 10 minutes, and I’ll walk you through it.' : 'Before your first campaign: ' + fbReason(is.st) + '. It’s quick, and I’ll walk you through it.',
      extra: fix(afQueue().find(k => k !== 'lic'), 'Walk me through it') });
    if (is.brand) steps.push({ page: 'brand', sel: '.mb-head', title: 'One thing is missing from your brand.',
      text: 'We couldn’t find your license number. It has to go on every post. Add it now, or when you start your first campaign.', extra: fix('lic', 'Add it now') });
    const nFix = steps.length;
    if (nFix) steps.push({ page: 'campaigns', sel: '.add-campaign', title: 'Now, a quick look around.', text: 'This is the Campaign button. Click it any time to start a new campaign. All you need is your listing link.' });
    else steps.push({ page: 'campaigns', sel: '.add-campaign', title: 'This is the Campaign button.', text: 'Click it any time to start a new campaign. All you need is your listing link.' });
    steps.push({ page: 'campaigns', sel: '.camp-tabs', title: 'Your campaigns live here.', text: 'Active campaigns are running now. When one finishes it moves to Completed, where you can run it again in one click.' });
    if (!is.brand) steps.push({ page: 'brand', sel: '.mb-head', title: 'This is the brand we built for you.', text: 'Resmara made it from your Facebook, Instagram and website. Every post and ad follows it. You can change it any time.' });
    steps.push({ page: 'credits', sel: '#billing-cards', box: true, title: 'This is Billing.', text: 'Your receipts and your card live here. You don’t need a card yet: you’ll add one when you pay for your first campaign.' });
    if (!is.fb) steps.push({ page: 'accounts', sel: '.meta-card', title: 'Your accounts.', text: 'Your Facebook Page, Instagram and ad account live here. If anything ever needs attention, this is where you’ll find it.' });
    steps.push({ page: 'support', sel: '.grid2 .panel', title: 'Need a hand?', text: 'Send us a request any time. A real person reads every one and replies right here.' });
    steps.push({ page: 'campaigns', sel: '.add-campaign', final: true, title: 'Let’s start your first campaign.', text: 'All you need is your listing link.', extra: '<div class="tour-fix"><button type="button" class="campaign-primary" onclick="afStartCampaign()">Let’s start your first campaign</button></div>' });
    TOUR.splice(0, TOUR.length, ...steps);
    tourResume = nFix;
    workspaceTour(0);
  };
  // "Walk me through it" from the tour: the walkthrough, then back to the tour where it left off.
  window.afTourFix = function (key) { workspaceTourCleanup?.(); afGuide(key); };
  // "Do it with our team" from the tour: book the setup session, then carry on with the tour.
  window.afTourBook = function () {
    workspaceTourCleanup?.(); obBook(true);
    const b = modal.querySelector('.modal-actions .nc-cancel');
    if (b) { b.textContent = tourResume != null ? 'Continue the tour' : 'Back'; b.className = 'campaign-primary'; b.setAttribute('onclick', "modal.classList.remove('wide-modal');afLater()"); }
  };

  // First campaign: listing link and photo permission, build everything, then pay to unlock it.
  window.afStartCampaign = function () { workspaceTourCleanup?.(); tourDone(); newCampaign(); };

  // ===== Engine 3 · Listing link (mockup) =====
  const LS = {
    ready:  { label: 'Ready', sub: 'Address, 32 photos and a video, from the link and other sites' },
    zillow: { label: 'Zillow link with its photos blocked', sub: 'Photos found on the photographer’s page instead' },
    few:    { label: 'Too few photos', sub: 'Only 9 usable photos from every source' },
    none:   { label: 'No home found', sub: 'The link doesn’t point to a home' },
    signin: { label: 'MLS sign-in link', sub: 'Needs a log-in to open' },
    dead:   { label: 'Dead link', sub: 'The page is gone' },
    sold:   { label: 'Pending or sold', sub: 'A source shows it’s under contract' }
  };
  let ls = 'ready';
  window.afListingPick = function () {
    show(`<span class="eyebrow">ENGINE 3 MOCKUP · LISTING LINK</span><h2>Pick what the link turns up.</h2><p>Then paste any link and press Build my campaign.</p>
    <form onsubmit="event.preventDefault();afNewCampaign(this.ls.value)"><div class="ob-scenarios">${Object.entries(LS).map(([k, v]) => `<label><input type="radio" name="ls" value="${k}" ${k === ls ? 'checked' : ''}><span><b>${v.label}</b><small>${v.sub}</small></span></label>`).join('')}</div>
    <div class="modal-actions"><span></span><button class="campaign-primary">Open + Campaign</button></div></form>`);
  };
  window.afNewCampaign = function (k) {
    if (k) ls = k;
    show(`<span class="eyebrow">NEW CAMPAIGN</span><h2>Which home is it?</h2>
    <p>Paste any link to the home. Resmara finds the address, then researches it everywhere it can: the listing sites, the photographer’s page and public records.</p>
    <label class="field">Link to the home<input id="ls-url" type="url" placeholder="https://..." value="${ls === 'zillow' ? 'https://www.zillow.com/homedetails/905-Laurel-Bend-Austin-TX/' : 'https://jamiecarter.aryeo.com/sites/905-laurel-bend'}"></label>
    <div class="ls-hint"><span class="robot-avatar" aria-hidden="true"></span><span><b>Got a link from your photographer?</b> One with all your photos and video works best (Aryeo, Fotello, Dropbox, Drive). An MLS share link, Zillow, Realtor.com, Redfin or your brokerage’s page works too.</span></div>
    <label class="nc-rights"><input type="checkbox" checked><span>I have permission to use these photos and listing details to market this property on social media and in ads.</span></label>
    <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary" onclick="afListingCheck()">Build my campaign</button></div>
    <p class="fine ob-skip">Preview (${esc(LS[ls].label)}): <a href="#" style="color:#12354d;text-decoration:underline" onclick="afListingPick();return false">try another result</a> · <a href="#" style="color:#12354d;text-decoration:underline" onclick="afManual();return false">enter it manually</a></p>`);
  };
  window.afListingCheck = function () {
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">CHECKING YOUR HOME</span><h2>Researching your home.</h2><p>This takes about a minute.</p><div id="ob-box"></div>`);
    const bad = ['none', 'signin', 'dead'].includes(ls);
    const rows = [
      ['Opening your link', ls === 'signin' ? 'This link needs an MLS sign-in' : ls === 'dead' ? 'There’s no page at this link' : 'Link opened', ls === 'signin' ? 'This link needs an MLS sign-in' : 'There’s no page at this link'],
      ['Finding the home’s address', '905 Laurel Bend, Austin, TX 78738', 'Couldn’t find a home at this link'],
      ['Searching Zillow, Realtor.com, Redfin and other sites', ls === 'sold' ? 'Zillow shows it as pending' : 'Found it on Zillow, Realtor.com and Redfin', 'Zillow shows it as pending'],
      ['Gathering the photos', ls === 'few' ? 'Only 9 usable photos' : ls === 'zillow' ? 'Zillow blocks its photos. Found 36 on the photographer’s page' : 'Found 32 photos', 'Only 9 usable photos'],
      ['Looking for a video', 'Found a listing video', ''],
      ['Building the home’s file', 'The home’s file is ready', '']
    ];
    const res = { ready: [1,1,1,1,1,1], zillow: [1,1,1,1,1,1], few: [1,1,1,0,1,1], sold: [1,1,0], none: [1,0], signin: [0], dead: [0] }[ls].map(Boolean);
    const stopAt = res.length;
    obWalk(document.querySelector('#ob-box'), rows.slice(0, stopAt), res.slice(0, stopAt), '', () => afListingResult());
  };
  function afListingResult() {
    const facts = `<div class="ls-facts"><img src="sample/card-3.jpg" alt=""><div><b>905 Laurel Bend, Austin, TX</b><div class="ls-chips"><span>4 bd</span><span>3 ba</span><span>2,980 sq ft</span><span>$1,150,000</span><span>Built 2019</span></div>
      <small>Sources: your link · Zillow · Realtor.com · Redfin · Travis County records</small></div></div>`;
    if (ls === 'ready' || ls === 'zillow') return afBuild('905 Laurel Bend', facts + `<ul class="ls-found"><li><b>${ls === 'zillow' ? '36 photos' : '32 photos'}</b>${ls === 'zillow' ? 'from your photographer’s page (Zillow blocks its photos)' : 'from your link'}</li><li><b>A listing video</b>it’ll lead your ad and one of your posts</li></ul>`);
    if (ls === 'few') return show(`<span class="eyebrow">ALMOST THERE</span><h2>We found 9 photos. Add 5 more.</h2>${facts}<p>A 14-day campaign needs at least 14 usable photos, and we couldn’t find more anywhere online.</p>
      <label class="nc-drop"><input type="file" accept="image/*" multiple><b>＋</b><span>Drop your photos here or click to choose</span><small>Add 5 more (minimum 14)</small></label>
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Later</button><button class="campaign-primary" onclick="afBuild('905 Laurel Bend')">Build it</button></div><p class="fine ob-skip">Preview: Build it unlocks once there are 14.</p>`);
    if (ls === 'sold') return show(`<span class="eyebrow">CAN’T ADVERTISE THIS ONE</span><h2>This home shows as pending.</h2><p>Zillow shows 905 Laurel Bend as pending, so it can’t be advertised. If that’s wrong, try your own listing link.</p>
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Close</button><button class="campaign-primary" onclick="afNewCampaign()">Try another link</button></div>`);
    const msg = ls === 'signin' ? ['This link needs an MLS sign-in.', 'Use your MLS’s public share link, or any other link to the home: your photographer’s page, Zillow or your brokerage’s site.']
      : ls === 'dead' ? ['There’s no page at this link.', 'It may have been taken down or typed wrong. Try another link to the home.']
      : ['We couldn’t find a home at this link.', 'Try another link to the home, or enter the address and upload your photos.'];
    show(`<span class="eyebrow">LET’S TRY ANOTHER WAY</span><h2>${msg[0]}</h2><p>${msg[1]}</p>
      <div class="modal-actions"><button type="button" class="campaign-primary navy" onclick="afManual()">Enter it manually</button><button class="campaign-primary" onclick="afNewCampaign()">Try another link</button></div>`);
  }
  window.afManual = function () {
    show(`<span class="eyebrow">NEW CAMPAIGN</span><h2>Enter the home.</h2><p>Resmara researches the address online, the same as for a link.</p>
      <label class="field">Street address<input value="905 Laurel Bend"></label><div class="nc-row3"><label class="field">City<input value="Austin"></label><label class="field">State<input value="TX"></label><label class="field">ZIP<input value="78738"></label></div>
      <label class="nc-drop"><input type="file" accept="image/*" multiple><b>＋</b><span>Drop your photos here or click to choose</span><small>Minimum 14, up to 60</small></label>
      <label class="nc-rights"><input type="checkbox" checked><span>I have permission to use these photos and listing details to market this property on social media and in ads.</span></label>
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="afNewCampaign()">Back</button><button class="campaign-primary" onclick="ls='ready';afListingCheck()">Build my campaign</button></div>`);
  };
  const baseNcBuild = window.ncBuild;
  window.ncBuild = function (form) {
    if (!afActive) return baseNcBuild(form);
    if (!form.rights.checked) return;
    const addr = (typeof ncTypedAddress === 'function' && ncTypedAddress(form)) || '905 Laurel Bend, Austin, TX';
    afBuild(addr.split(',')[0]);
  };
  let afAddr = '905 Laurel Bend';
  window.afBuild = function (addr, found) {
    afAddr = addr || afAddr;
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">${found ? 'GREEN LIGHT · BUILDING YOUR CAMPAIGN' : 'BUILDING YOUR CAMPAIGN'}</span><h2>Building ${esc(afAddr)}.</h2><p>${found ? 'We have everything we need. Anything wrong in the details, you fix in review.' : 'I’m reading your listing and building your whole campaign. A few minutes.'}</p>${found || ''}<div id="ob-box"></div>`);
    modal.classList.add('af-locked');
    obWalk(document.querySelector('#ob-box'), [
      ['Reading your listing', 'Read the listing and researched the home', ''],
      ['Picking your best 14 photos', 'Picked your best 14 photos', ''],
      ['Writing your 14 days of posts', 'Wrote 14 days of posts in your voice', ''],
      ['Designing your posts', 'Designed your posts in your brand', ''],
      ['Building your ad and listing page', 'Built your ad and listing page', '']
    ], [true, true, true, true, true], '', () => afUnlock());
  };
  // The built campaign stays locked until it's paid for: blurred, with one card on top.
  const lockedIdx = () => state.campaigns.findIndex(x => x.locked);
  let gateDeclined = false;
  window.afUnlock = function (declined) {
    modal.classList.remove('af-locked'); if (modal.open) modal.close();
    if (!state.campaigns.some(x => x.address === afAddr)) {
      const id = 'preview-' + afAddr.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      const c = { address: afAddr, area: 'Austin, TX · $1,150,000', image: 'sample/card-3.jpg', reviewId: id, scopeFirst: true, creditUsed: 1, paid: true, day: 0, locked: !state.cardOnFile };
      try { const scope = initialCampaignScope(c); scope.start = goLiveDate(scope.start); state.reviews = state.reviews || {}; state.reviews['review-' + id] = { v: 5, approved: false, scopeConfirmed: false, calendarApproved: false, items: sampleReviewItems(c), scope }; } catch (e) {}
      state.campaigns.unshift(c);
      if (!c.locked) { dashboard('campaigns'); details(0); toast('Built and paid: $49 charged to your saved Visa ending 4242.'); return; }
    }
    gateDeclined = !!declined;
    const i = lockedIdx(); if (i < 0) return;
    dashboard('campaigns'); details(i);
  };
  const baseDetails = window.details;
  window.details = function (i) {
    baseDetails(i);
    const c = [...state.campaigns, ...examples][i];
    if (c && c.locked) paintGate(c);
    try { paintGallery(); } catch (e) {}
  };
  // Stripe's own card form, embedded in the card (Stripe Embedded Checkout). Fields shown here are
  // a picture of it: nothing typed in this preview goes anywhere.
  const stripeForm = (err) => `<div class="sx">
    <div class="sx-wallets"><span class="sx-wallet">Apple Pay</span><span class="sx-wallet">Google Pay</span></div>
    <div class="sx-or">Or pay with card</div>
    <div class="sx-label">Card information</div>
    <div class="sx-box${err ? ' sx-err' : ''}"><div class="sx-f sx-num">1234 1234 1234 1234<span class="sx-brands"><i>VISA</i><i>MC</i><i>AMEX</i></span></div><div class="sx-row"><div class="sx-f">MM / YY</div><div class="sx-f">CVC</div></div></div>
    ${err ? '<div class="sx-msg">Your card was declined. Please check your card and try again, or use another card.</div>' : ''}
    <div class="sx-label">Name on card</div><div class="sx-box"><div class="sx-f">Jamie Carter</div></div>
    <div class="sx-label">Country and ZIP</div><div class="sx-box sx-row2"><div class="sx-f">United States</div><div class="sx-f">ZIP</div></div>
    <div class="sx-foot">Secure payment by <b>stripe</b> · Resmara never sees your card number</div></div>`;
  // Campaign calendar: a Gallery view, and 👍 / 👎 on every post (Adam, 22 Nov).
  let calView = 'calendar';
  function paintGallery() {
    const cal = document.querySelector('.review-calendar'); const r = activeReview && activeReview();
    if (!cal || !r || !r.items || cal.querySelector('.cv-toggle')) return;
    const scroll = cal.querySelector('.review-month-scroll'); if (!scroll) return;
    scroll.insertAdjacentHTML('beforebegin', `<div class="cv-toggle" role="tablist"><button class="${calView === 'calendar' ? 'on' : ''}" onclick="afCalView('calendar')">Calendar</button><button class="${calView === 'gallery' ? 'on' : ''}" onclick="afCalView('gallery')">Gallery</button></div>`);
    const posts = r.items.map((it, i) => ({ it, i })).filter(x => x.it.kind !== 'Meta ad').sort((a, b) => a.it.day - b.it.day);
    const card = ({ it, i }) => {
      let when = 'Day ' + it.day; try { const sl = reviewSlot(r, it); when += ' · ' + reviewDateLabel(sl.date, sl.time, r.scope.zone); } catch (e) {}
      return `<article class="cv-card"><button class="cv-img" onclick="editCampaignItem(${i})"><img src="${esc(mediaPath(it.image))}" alt="">${it.overlay ? `<em class="post-overlay">${esc(it.overlay)}</em>` : ''}${it.kind === 'Video post' ? '<span class="play-btn" aria-hidden="true">▶</span>' : ''}</button>
        <div class="cv-body"><small>${esc(when)}</small><b>${esc(it.title)}</b><p>${esc(it.caption || '')}</p>
        <div class="cv-rate"><span>Like this style?</span><button class="${it.rating === 1 ? 'on' : ''}" aria-label="Thumbs up" onclick="afRate(${i},1)">👍</button><button class="${it.rating === -1 ? 'on' : ''}" aria-label="Thumbs down" onclick="afRate(${i},-1)">👎</button></div></div></article>`;
    };
    scroll.insertAdjacentHTML('afterend', `<div class="cv-gallery">${posts.map(card).join('')}</div>`);
    cal.classList.toggle('cv-show-gallery', calView === 'gallery');
  }
  window.afCalView = function (v) { calView = v; const c = document.querySelector('.review-calendar'); if (!c) return; c.classList.toggle('cv-show-gallery', v === 'gallery'); c.querySelectorAll('.cv-toggle button').forEach(b => b.classList.toggle('on', b.textContent.toLowerCase() === v)); };
  window.afRate = function (i, v) {
    const r = activeReview(); const it = r.items[i]; it.rating = it.rating === v ? 0 : v; persist && persist();
    document.querySelectorAll(`[onclick^="afRate(${i},"]`).forEach(b => b.classList.toggle('on', b.getAttribute('onclick') === `afRate(${i},${it.rating})`));
    if (it.rating) toast(it.rating > 0 ? 'Noted: more like this.' : 'Noted: less like this. Your next campaign will lean away from it.');
  };
  const baseEdit = window.editCampaignItem;
  window.editCampaignItem = function (i) {
    baseEdit(i);
    const it = activeReview().items[i]; const side = document.querySelector('#modal .ei-side'); if (!side || it.kind === 'Meta ad') return;
    side.insertAdjacentHTML('afterbegin', `<div class="cv-rate cv-rate-modal"><span>Like this style?</span><button class="${it.rating === 1 ? 'on' : ''}" aria-label="Thumbs up" onclick="afRate(${i},1)">👍</button><button class="${it.rating === -1 ? 'on' : ''}" aria-label="Thumbs down" onclick="afRate(${i},-1)">👎</button></div>`);
  };
  // Engine 4: the ad, built differently from the posts: a true-to-the-house hook, minimal text.
  window.afAd = function () {
    const hooks = [
      ['sample/card-3.jpg', 'Have you seen a pool like this?', 'Infinity edge · Hill Country view'],
      ['sample/card-1.jpg', 'This entry sets the tone.', '4 bd · 3 ba · Austin'],
      ['sample/card-4.jpg', 'Wait till you see the back porch.', 'Sunset views · Outdoor living']
    ];
    const card = ([img, hook, sub], i) => `<figure class="ad-card"><div class="ad-art"><img src="${img}" alt=""><div class="ad-shade"></div><div class="ad-text"><b>${hook}</b><small>${sub}</small><span class="ad-sig">Jamie Carter · DRE #02123456 · (530) 555-0142</span></div></div><figcaption>Hook ${i + 1}${i === 0 ? ' · leading' : ''}</figcaption></figure>`;
    show(`<span class="eyebrow">YOUR AD · DAYS 1–14</span><h2>Built to stop the scroll.</h2>
      <p>Resmara found what makes this home stand out and wrote three hooks around it, all true to the house. Your listing video runs alongside them. Meta shows them all and puts your budget behind the ones people click.</p>
      <div class="ad-row">${hooks.map(card).join('')}<figure class="ad-card"><div class="ad-art"><img src="sample/card-2.jpg" alt=""><div class="ad-shade"></div><span class="play-btn ad-play" aria-hidden="true">▶</span><div class="ad-text"><b>Have you seen a pool like this?</b><small>Listing video · 0:45</small><span class="ad-sig">Jamie Carter · DRE #02123456</span></div></div><figcaption>Video ad</figcaption></figure><figure class="ad-card ad-story"><div class="ad-art"><img src="sample/card-3.jpg" alt=""><div class="ad-shade"></div><div class="ad-text"><b>Have you seen a pool like this?</b><small>Tap to see the home</small><span class="ad-sig">Jamie Carter · DRE #02123456</span></div></div><figcaption>Also made tall for Stories and Reels</figcaption></figure></div>
      <div class="ad-copy"><div><small>PRIMARY TEXT</small><p>Infinity pool, Hill Country views and room for everyone. Come see 905 Laurel Bend.</p></div><div><small>HEADLINE</small><p>See the pool. Then the rest.</p></div><div><small>BUTTON</small><p>Learn more</p></div><div><small>CLICKS GO TO</small><p>Your listing page</p></div></div>
      <p class="fine">Runs on Facebook, Instagram, Marketplace, Stories and Reels. Housing ad rules applied. Budget: $50 for all 14 days, billed by Meta to your ad account.</p>
      <div class="modal-actions"><span></span><button class="campaign-primary" onclick="modal.close()">Done</button></div>`);
    modal.classList.add('wide-modal');
  };
  function paintGate(c) {
    const box = document.querySelector('#content'); if (!box) return;
    box.classList.add('af-blur-wrap');
    const price = billingMoney(BILLING_PRICE_CENTS), declined = gateDeclined; gateDeclined = false;
    const saved = state.cardOnFile && !declined;
    box.querySelector('.af-unlock')?.remove();
    box.insertAdjacentHTML('beforeend', `<div class="af-unlock" role="dialog" aria-label="Unlock your campaign"><div class="af-unlock-card">
      <div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">${declined ? 'PAYMENT' : 'YOUR CAMPAIGN IS READY'}</span></div></div>
      <h2>${declined ? 'Your payment didn’t go through.' : esc(c.address) + ' is built.'}</h2>
      <p>${declined ? 'Please check your card and try again. Nothing was charged, and your campaign is saved right here.' : `Your 14 days of posts, your ad and your listing page are all here. Pay <b>${price}</b> to unlock it, then review and launch.`}</p>
      ${saved ? `<div class="sx-saved"><span class="sx-card">VISA</span><span><b>Visa ending 4242</b><small>Your saved card</small></span><button type="button" class="campaign-primary navy" onclick="state.cardOnFile=false;afUnlock()">Use another card</button></div>` : stripeForm(declined)}
      ${saved ? '' : `<label class="af-save"><input type="checkbox" checked><span><b>Save this card for future campaigns</b><small>Skip this step next time: your next campaign unlocks as soon as it’s built.</small></span></label>`}
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="dashboard('campaigns')">Later</button><button class="campaign-primary" onclick="afPaid()">${declined ? 'Try again' : 'Unlock my campaign for ' + price}</button></div>
      <p class="fine ob-skip">Preview: ${declined ? '' : '<a href="#" style="color:#12354d;text-decoration:underline" onclick="afUnlock(true);return false">see a declined card</a> · '}<a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">start over</a></p></div></div>`);
    window.scrollTo(0, 0);
  }
  // Guardrail: one locked campaign at a time.
  const baseNew = window.newCampaign;
  window.newCampaign = function () {
    const c = afActive && state.campaigns.find(x => x.locked);
    if (!c) return afActive ? afNewCampaign() : baseNew();
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">ONE AT A TIME</span></div></div><h2>Unlock ${esc(c.address)} first.</h2>
      <p>Your campaign for ${esc(c.address)} is built and waiting. Unlock it to start another, or replace it with a new listing.</p>
      <div class="modal-actions"><button type="button" class="campaign-primary navy" onclick="modal.close();state.campaigns=state.campaigns.filter(x=>!x.locked);baseNewCampaign()">Replace it</button><button class="campaign-primary" onclick="afUnlock()">Unlock ${esc(c.address)}</button></div>`);
  };
  window.baseNewCampaign = baseNew;
  // On My campaigns, a locked campaign says so, and opening it shows the same pay gate.
  function paintLocked() {
    const c = state.campaigns.find(x => x.locked); if (!c) return;
    document.querySelectorAll('#content article.card').forEach(card => {
      if (!card.textContent.includes(c.address) || card.querySelector('.af-lock-tag')) return;
      card.classList.add('af-locked-card');
      card.insertAdjacentHTML('afterbegin', `<span class="af-lock-tag">Built · pay to unlock</span>`);
      const btn = [...card.querySelectorAll('button')].pop(); if (btn) btn.textContent = 'Unlock my campaign';
      card.querySelectorAll('span,small,em,p,div').forEach(el => {
        if (el.children.length) return;
        const t = el.textContent.trim();
        if (t === 'Staged') el.textContent = 'Locked';
        else if (t === 'Awaiting campaign generation') el.textContent = 'Built · waiting for payment';
        else if (t === 'Draft') el.textContent = 'Not live';
      });
    });
  }
  window.afFirstCampaign = window.afUnlock;
  window.afPaid = function () {
    state.cardOnFile = true; state.campaigns.forEach(x => { x.locked = false; });
    document.querySelector('.af-unlock')?.remove();
    document.querySelector('#content')?.classList.remove('af-blur-wrap');
    toast('Paid. Your campaign is unlocked. Review it, then launch.');
  };
  window.afDeclined = function () { afUnlock(true); };
  window.afFinish = afFinish;

  // My Brand with the Voice of the client section (and the phone and broker license fields).
  window.afBrand = function (missing) {
    modal.classList.remove('af-locked'); modal.close();
    afActive = true; if (missing) brandMissing = true;
    dashboard('brand');
  };
  function prepBrand() {
    const missing = issues().brand;
    Object.assign(SAMPLE_BRAND, { agent: 'Jamie Carter', brokerage: 'Shasta Summit Realty', license: missing ? '' : 'DRE #02123456', website: 'https://jamiecarterrealty.com',
      market: 'Redding and Shasta Lake', brandLink: 'https://instagram.com/jamiecarterrealty', palette: PALETTE, fonts: ['Playfair Display', 'Jost'], voice: VOICE,
      use: ['Let’s get you home', 'Welcome home', 'Your Redding agent'], avoid: ['Stunning', 'Must-see', 'Hurry!'], theme: 'Match my brand',
      legal: ['Jamie Carter · REALTOR® · ' + (missing ? 'License number needed' : 'DRE #02123456'), 'Shasta Summit Realty · DRE #01987654', 'Equal Housing Opportunity'],
      sources: [['Facebook', 'Jamie Carter Realty'], ['Instagram', '@jamiecarterrealty'], ['Website', 'jamiecarterrealty.com'], ['State license lookup', 'DRE'], ['Brokerage', 'Shasta Summit Realty']], researched: 'Today, 9:16 AM' });
    state.name = 'Jamie Carter';
  }
  function paintBrand() {
    const missing = issues().brand;
    const form = document.querySelector('form.mb'); if (!form) return;
    form.querySelectorAll('.mb-mono').forEach(x => { x.textContent = 'JC'; });
    const hd = document.querySelector('.mb-id div'); if (hd) hd.innerHTML = '<b>Jamie Carter Realty</b><small>Jamie Carter · Shasta Summit Realty · Redding and Shasta Lake</small>';
    const grid = form.querySelector('.mb-grid');
    const fld = (name, label, value, src) => `<label class="mb-field"><span>${label}<em>${src}</em></span><input name="${name}" value="${esc(value)}"></label>`;
    grid.insertAdjacentHTML('beforeend', fld('phone', 'Phone', '(530) 555-0142', 'Facebook Page') + fld('brokerLicense', 'Broker license number', 'DRE #01987654', 'State license lookup'));
    form.querySelector('[name=agent]').closest('.mb-field').querySelector('em').textContent = 'Facebook Page';
    form.querySelector('[name=license]').closest('.mb-field').querySelector('em').textContent = missing ? 'Not found' : 'State license lookup';
    // Swap the small Voice box for the full Voice of the client section.
    const voiceSec = [...form.querySelectorAll('.mb-sec')].find(x => x.querySelector('h4') && x.querySelector('h4').textContent === 'VOICE');
    const pair = voiceSec.parentNode; voiceSec.remove();
    pair.insertAdjacentHTML('afterend', `<section class="mb-sec vc-sec"><h4>VOICE OF THE CLIENT</h4><textarea name="voice" rows="6">${esc(VOICE)}</textarea>
      <p class="vc-note">Resmara wrote this from your Facebook, Instagram and website. It’s how every post, caption, ad and listing page will sound. Rewrite anything that isn’t you, then save.</p>
      <div class="mb-chips">${SAMPLE_BRAND.use.map(w => `<span class="ok">“${esc(w)}”</span>`).join('')}${SAMPLE_BRAND.avoid.map(w => `<span class="no">${esc(w)}</span>`).join('')}</div></section>`);
    pair.style.gridTemplateColumns = '1fr';
    // No Modern / Classic / Rustic / Match my brand (Adam, 22 Nov): the look is learned from their 👍 / 👎.
    const looks = form.querySelector('.mb-looks');
    if (looks) { const sec = looks.closest('.mb-sec'), two = sec.parentNode; sec.remove(); if (two.classList.contains('mb-two')) two.style.gridTemplateColumns = '1fr'; }
    if (missing) document.querySelector('#content').insertAdjacentHTML('afterbegin', `<div class="af-attn"><span class="robot-avatar af-bot" aria-hidden="true"></span><span><b>Your license number is missing.</b> It has to go on every post.</span><button class="campaign-primary" onclick="afGuide('lic')">Add it with me</button></div>`);
    if (missing) { const f = form.querySelector('[name=license]').closest('.mb-field'); f.classList.add('miss');  }
    const c = document.querySelector('#content');
    c.insertAdjacentHTML('beforeend', `<p class="fine ob-skip" style="margin-top:14px;text-align:center">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afMissing();return false">see the “license missing” check when they start a campaign</a> · <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">start over</a></p>`);
  }

  // The Campaign build engine's check on + Campaign (logged on Engine 4).
  window.afMissing = function () {
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">BEFORE WE BUILD</span></div></div><h2>Your license number is missing.</h2>
    <p>It has to go on every post. Add it here and Resmara saves it to your brand, so you’re never asked again.</p><label class="field">License number<input placeholder="e.g. DRE #02123456"></label>
    <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary" onclick="modal.close();toast('Saved to My Brand. Building your campaign (preview).')">Save and continue</button></div>`);
  };


  function afResult() {
    const pageOk = sc !== 'noPage';
    const igOk = !(sc === 'igPers' || sc === 'noPage') && chosen === PAGE;
    const adOk = !(sc === 'noAd' || sc === 'noCard');
    if (sc === 'taken') {
      show(`<span class="eyebrow">LOG IN</span><h2>This Page is already on Resmara.</h2>
      <ul class="af-found">${row(PAGE.init, '', 'Facebook Page', PAGE.name, 'Connected to another Resmara account', false, '')}</ul>
      <p>If that account is yours, log in with the Facebook you used for it. If not, contact us and we’ll sort it out.</p>
      <div class="modal-actions"><button type="button" class="campaign-primary navy" onclick="toast('Preview: this opens Support.')">Contact us</button><button class="campaign-primary" onclick="afPick()">Log in with a different Facebook</button></div>${again()}`);
      return;
    }
    const rows = [
      pageOk ? row(chosen.init, '', 'Facebook Page', chosen.name, 'Published · you can post to it', true, '')
             : row('?', 'none', 'Facebook Page', 'No business Page found', 'Only your personal profile', false, 'Resmara still builds everything. You download each post and share it yourself until a Page is connected.'),
      pageOk ? (igOk ? row('IG', 'ig', 'Instagram', IG, 'Business account, linked to your Page', true, '')
                     : row('IG', 'none', 'Instagram', chosen === TEAM ? 'No Instagram on this Page' : IG, chosen === TEAM ? 'Nothing linked to ' + TEAM.name : 'Personal account, so Resmara can’t post to it', false, 'Your posts go to Facebook only until it’s a business account.'))
             : row('IG', 'none', 'Instagram', 'Not checked', 'Needs a Facebook Page first', false, ''),
      sc === 'noAd' ? row('Ad', 'none', 'Ad account', 'No ad account', '', false, 'Your posts still go out. Your listing ad is off until you have one.')
                    : row('Ad', adOk ? '' : 'none', 'Ad account', 'Jamie Carter Realty', adOk ? 'Active · card on file' : 'Active · no card on it', adOk, adOk ? '' : 'No ad until it has a payment method. Your posts still go out.')
    ];
    const allOk = pageOk && igOk && adOk;
    const head = allOk ? 'You’re all set.' : pageOk ? 'You’re ready to go.' : 'Resmara can build everything, but can’t post for you yet.';
    const lead = allOk ? 'Resmara can post to your Page and Instagram and run your listing ads.'
      : pageOk ? ([igOk, adOk].filter(x => !x).length > 1 ? 'A couple of things will make it better.' : 'One thing will make it better.') + ' Fix it now or any time from Accounts.'
      : 'Connect a Facebook business Page and the rest goes out on schedule.';
    const btns = allOk ? `<span></span><button class="campaign-primary" onclick="modal.close()">Build my brand</button>`
      : pageOk ? `<button type="button" class="nc-cancel" onclick="obBook(true)">Book a call</button><div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="${igOk ? "setupGuides('ads');modal.close()" : 'obIgSwitch()'}">Fix it now</button><button class="campaign-primary" onclick="modal.close()">Build my brand</button></div>`
      : `<button type="button" class="nc-cancel" onclick="obBook(true)">Book a call</button><div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="modal.close()">Continue anyway</button><button class="campaign-primary" onclick="setupGuides('page');modal.close()">Fix it now</button></div>`;
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>${head}</h2><p>${lead}</p><h3 style="margin:14px 0 0;color:#12354d">Here’s what we found</h3><ul class="af-found">${rows.join('')}</ul>
    ${pageOk ? '<p class="af-note">We also picked up your website and phone from your Page, so your brand kit starts filled in.</p>' : ''}
    <div class="modal-actions">${btns}</div>${again()}`);
  }
  function again() { return `<p class="fine ob-skip">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try another setup</a> · <a href="#" style="color:#12354d;text-decoration:underline" onclick="afAccounts();return false">see their setup to-do list in Accounts</a></p>`; }

  // The setup to-do list: what the audit found missing, in order, each ticked off by the next
  // check that passes. Lives in Accounts; drives the notice, the emails, Ask Resmara and the Team room.
  window.afAccounts = function () {
    modal.classList.remove('af-locked'); modal.close();
    afActive = true; dashboard('accounts');
  };
  function paintAccounts() {
    const { pageOk, igOk, adOk } = afState();
    const items = [
      { ok: true, t: 'Sign in with Facebook', d: 'Signed in as Jamie Carter.', when: 'Done today, 9:14 AM' },
      pageOk ? { ok: true, t: 'Connect your Facebook Page', d: chosen.name + '. Resmara posts here.', when: 'Done today, 9:14 AM' }
             : { ok: false, t: 'Create a Facebook business Page', d: 'Resmara posts to a business Page, not your personal profile. Until then you download each post and share it yourself.', key: 'page' },
      igOk ? { ok: true, t: 'Connect your Instagram', d: IG + ', a business account linked to your Page.', when: 'Done today, 9:14 AM' }
           : { ok: false, t: sc === 'noIg' ? 'Create an Instagram business account' : 'Switch your Instagram to a business account', d: pageOk ? 'Your posts go to Facebook only until it’s switched. It takes about a minute.' : 'Do this after your Page is set up.', key: 'ig' },
      adOk ? { ok: true, t: 'Ad account ready', d: 'Jamie Carter Realty, with a card on file.', when: 'Done today, 9:14 AM' }
           : { ok: false, t: sc !== 'noCard' ? 'Set up your ad account' : 'Add a card to your ad account', d: 'Your posts still go out. Your listing ad is off until this is done.', key: 'ad' }
    ];
    const left = items.filter(i => !i.ok);
    // One box: what's set up and what isn't, then one way through it (Adam, 22 Nov).
    const list = items.map(i => `<li class="${i.ok ? 'done' : ''}"><span class="af-num">${i.ok ? '✓' : '!'}</span><span class="af-txt"><b>${i.t}</b><p>${i.d}</p>${i.ok ? `<small>${i.when}</small>` : ''}</span></li>`).join('');
    document.querySelector('#content').innerHTML = `<div class="welcome"><h1>Your social connections.</h1></div>
    <div class="panel meta-card"><span class="eyebrow">YOUR SETUP</span><h3>${left.length ? (left.length === 1 ? 'One thing left to set up' : left.length + ' things left to set up') : 'Everything is set up'}</h3>
    <p>${left.length ? 'Here’s what’s ready and what isn’t. Each one ticks off on its own as soon as Meta shows it’s done.' : 'Resmara can post to your Page and Instagram and run your listing ads.'}</p>
    <ul class="af-todo acc-one">${list}</ul>
    ${left.length ? `<div class="acc-help">
      <div><button class="campaign-primary" onclick="afSetup()">Walk me through it</button><p>I’ll take you through ${left.length === 1 ? 'it' : 'all ' + left.length} step by step, on one screen. About ${left.length > 2 ? 10 : left.length * 4} minutes.</p></div>
      <div><button class="campaign-primary" style="background:#12354d;color:#fff" onclick="afTourBook()">Do it with our team</button><p>Book a free 30-minute screen share and one of our team sets it up with you.</p></div></div>` : ''}
    <div class="af-meta"><span>Last checked today at 9:14 AM</span><span class="btn-pair" style="margin:0"><button class="alt" onclick="toast('Checked just now. Nothing has changed.')">Check again</button><button class="alt" onclick="afPick()">Reconnect</button>${sc === 'several' ? '<button class="alt" onclick="afPick()">Change Page</button>' : ''}</span></div></div>
    <p class="fine ob-skip" style="margin-top:14px">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try another setup</a></p>`;
  }

  const hash = window.__previewHash || location.hash;
  // Tutorials: the existing Setup page, opened at one guide, each guide with a short screen recording.
  const baseGuides = window.setupGuides;
  window.setupGuides = function (open) {
    baseGuides(open);
    document.querySelectorAll('.sg-card').forEach(card => {
      if (card.querySelector('.sg-video')) return;
      const h = card.querySelector('h3'); if (!h) return;
      h.insertAdjacentHTML('afterend', `<div class="sg-video" role="img" aria-label="Video: ${esc(h.textContent)}"><span class="sg-play"></span><b>Watch how: ${esc(h.textContent)}</b><small>A 1-minute explainer video: mock-up screens, step by step (AI-made, coming soon)</small></div>`);
    });
    const el = open && document.getElementById('sg-' + open); if (el) el.classList.add('sg-focus');
  };
  if (hash.indexOf('#setup-guides-') === 0) setTimeout(() => setupGuides(hash.slice(14)), 50);
  if (hash === '#listing') setTimeout(() => { history.replaceState(null, '', location.pathname + '#listing'); afActive = true; state.clientSignedIn = true; state.cardOnFile = false; dashboard('campaigns'); afListingPick(); }, 50);
  if (hash === '#ad') setTimeout(() => { history.replaceState(null, '', location.pathname + '#ad'); afAd(); }, 50);
  if (hash === '#tour') setTimeout(() => { history.replaceState(null, '', location.pathname + '#tour'); afPick(); }, 50);
  if (hash === '#audit') setTimeout(() => { history.replaceState(null, '', location.pathname + '#audit'); afPick(); }, 50);
  if (hash === '#signup') setTimeout(() => { history.replaceState(null, '', location.pathname + '#signup'); afSignup('personal'); }, 50);
})();

// Review copy only: Engine 5 mockup (the listing website). Redraws the page Resmara builds for
// every campaign, and adds "Your website" (Preview, Copy link, Share) to the campaign page.
(function () {
  const css = `
  .w5{--w5-pad:clamp(18px,4vw,56px);background:var(--ls-page);color:var(--ls-text);font-family:var(--ls-body);font-size:16px;line-height:1.6;position:relative}
  .w5 *{box-sizing:border-box}
  .w5 img{padding:0!important;margin:0;max-width:100%}
  .w5 h1,.w5 h2,.w5 h3{font-family:var(--ls-head)!important;font-weight:var(--ls-hw,500)!important;text-transform:var(--ls-hcase,none)!important;font-stretch:var(--ls-hstretch,100%)!important;letter-spacing:var(--ls-hls,0)!important;line-height:var(--ls-hlh,1.12)!important;margin:0!important}
  .w5.w5-dash .w5-eyebrow:before{content:'';display:inline-block;width:26px;height:2px;background:currentColor;vertical-align:middle;margin-right:10px}
  .w5 .w5-ch-num{color:var(--ls-second,var(--ls-accent))!important}
  .w5.w5-bold .w5-ch-num{opacity:1!important;font-weight:900;font-stretch:125%}
  .w5.w5-bold .w5-hero h1{font-size:clamp(34px,5.4vw,70px)!important}
  .w5.w5-bold .w5-chip{background:var(--ls-second,var(--ls-accent))}
  .w5.w5-bold .w5-btn{text-transform:uppercase;letter-spacing:.04em;font-weight:800;font-size:14px}
  .w5 a{color:inherit;text-decoration:none}
  .w5-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:999px;padding:13px 24px;font:600 15px var(--ls-body);cursor:pointer;white-space:nowrap}
  .w5-btn.solid{background:var(--ls-accent);color:#fff}
  .w5-btn.dark{background:var(--ls-primary);color:#fff}
  .w5-btn.light{background:#fff;color:var(--ls-primary)}
  .w5-nav{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:24px;padding:14px var(--w5-pad);background:color-mix(in srgb,var(--ls-page) 92%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid color-mix(in srgb,var(--ls-primary) 10%,transparent)}
  .w5-brand{font:600 19px var(--ls-head);color:var(--ls-primary);margin-right:auto}
  .w5-brand img{height:40px;width:auto;display:block}
  .w5-links{display:flex;gap:22px;font-size:14px;color:var(--ls-primary);font-weight:500}
  .w5-links a:hover{opacity:.7}
  .w5-nav .w5-btn{padding:10px 18px;font-size:14px}
  .w5-hero{position:relative;min-height:min(86vh,760px);display:flex;align-items:flex-end;overflow:hidden;color:#fff}
  .w5-hero-img{position:absolute;inset:0;background-size:cover;background-position:center;transform:scale(1.04);animation:w5zoom 18s ease-out forwards}
  @keyframes w5zoom{to{transform:scale(1)}}
  .w5-hero:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.05) 35%,rgba(0,0,0,.68))}
  .w5-hero-in{position:relative;z-index:1;width:100%;padding:0 var(--w5-pad) clamp(28px,5vw,56px)}
  .w5-vtag{position:absolute;top:16px;right:16px;z-index:1;background:rgba(0,0,0,.55);color:#fff;font-size:12px;font-weight:600;border-radius:999px;padding:6px 12px}
  .w5-chip{display:inline-block;background:var(--ls-accent);color:#fff;border-radius:999px;padding:5px 14px;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
  .w5-hero h1{font-size:clamp(38px,6vw,76px)!important;color:#fff!important;margin:14px 0 6px!important}
  .w5-hero-sub{font-size:clamp(16px,1.6vw,19px);opacity:.92;margin:0 0 4px}
  .w5-hero-row{display:flex;flex-wrap:wrap;align-items:center;gap:14px 28px;margin-top:18px}
  .w5-price{font:600 clamp(26px,3vw,36px) var(--ls-head)}
  .w5-facts{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:15px}
  .w5-facts span+span:before{content:"·";margin-right:18px;opacity:.6}
  .w5-hero-btns{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
  .w5-sec{padding:clamp(48px,7vw,96px) var(--w5-pad)}
  .w5-eyebrow{display:block;font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--ls-accent);margin-bottom:12px}
  .w5-intro{display:grid;grid-template-columns:1.3fr 1fr;gap:clamp(28px,5vw,72px);align-items:start}
  .w5-intro h2{font-size:clamp(30px,3.6vw,46px)!important;color:var(--ls-primary)!important;margin-bottom:18px!important}
  .w5-intro p{margin:0 0 14px;font-size:17px}
  .w5-sheet{background:#fff;border-radius:18px;padding:8px 22px;box-shadow:0 18px 40px -28px rgba(0,0,0,.35)}
  .w5-sheet div{display:flex;justify-content:space-between;gap:12px;padding:13px 0;border-bottom:1px solid color-mix(in srgb,var(--ls-primary) 10%,transparent)}
  .w5-sheet div:last-child{border:0}
  .w5-sheet span{opacity:.75}.w5-sheet b{color:var(--ls-primary)}
  .w5-tint{background:var(--ls-tint)}
  .w5-quick{display:flex;flex-wrap:wrap;justify-content:center;gap:0;background:var(--ls-primary);color:#fff}
  .w5-quick div{padding:18px clamp(14px,2.4vw,34px);text-align:center;border-right:1px solid rgba(255,255,255,.14)}
  .w5-quick div:last-child{border:0}
  .w5 .w5-quick small{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#fff!important;opacity:.75}
  .w5-quick b{font:500 20px var(--ls-head);color:#fff}
  .w5-prologue{text-align:center;max-width:900px;margin:0 auto;padding-bottom:clamp(20px,3vw,40px)!important}
  .w5-prologue h2{font-size:clamp(32px,4.4vw,58px)!important;color:var(--ls-primary)!important}
  .w5 .w5-prologue p{font-size:18px;margin-top:16px;color:var(--ls-text)!important}
  .w5-ch{display:grid;grid-template-columns:1.25fr 1fr;gap:clamp(28px,6vw,90px);align-items:center;padding:clamp(28px,5vw,70px) var(--w5-pad)}
  .w5-ch.flip{grid-template-columns:1fr 1.25fr}
  .w5-ch.flip .w5-ch-pics{order:2}
  .w5-ch-pics{position:relative;padding-bottom:12%}
  .w5 .w5-ch-pics .main{width:88%;aspect-ratio:4/3;height:auto;max-height:none;object-fit:cover;border-radius:18px;display:block}
  .w5-ch.flip .w5-ch-pics .main{margin-left:auto}
  .w5-ch-pics .inset{position:absolute;width:44%;aspect-ratio:1;object-fit:cover;border-radius:14px;right:0;bottom:0;border:6px solid var(--ls-page);box-shadow:0 18px 40px -24px rgba(0,0,0,.45)}
  .w5-ch.flip .w5-ch-pics .inset{right:auto;left:0}
  .w5-ch-num{display:block;font:500 64px/1 var(--ls-head);color:var(--ls-accent)!important;opacity:.35;margin-bottom:6px}
  .w5-ch-txt h3{font-size:clamp(28px,3vw,40px)!important;color:var(--ls-primary)!important;margin-bottom:14px!important}
  .w5 .w5-ch-txt p{font-size:17.5px;color:var(--ls-text)!important;margin:0;max-width:480px}
  .w5-note{margin:18px 0 0;font:italic 400 clamp(18px,1.8vw,22px)/1.5 var(--ls-head);color:#fff}
  .w5-note cite{display:block;font:600 13px var(--ls-body);font-style:normal;letter-spacing:.12em;text-transform:uppercase;margin-top:10px;opacity:.8}
  .w5-hl{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:28px}
  .w5-hl figure{margin:0;background:#fff;border-radius:18px;overflow:hidden}
  .w5-hl img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block}
  .w5-hl figcaption{padding:18px 20px 22px}
  .w5-hl b{display:block;font:500 22px var(--ls-head);color:var(--ls-primary);margin-bottom:4px}
  .w5-hl small{font-size:15px;opacity:.85}
  .w5-h2{font-size:clamp(28px,3.2vw,42px)!important;color:var(--ls-primary)!important}
  .w5-gal{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:clamp(120px,15vw,210px);gap:10px;margin-top:28px}
  .w5 .w5-gal button{border:0!important;padding:0!important;margin:0!important;border-radius:12px!important;overflow:hidden;cursor:zoom-in;background:#ddd!important;min-height:0!important;width:100%!important;height:100%!important;box-shadow:none!important}
  .w5 p,.w5 li,.w5 small,.w5 span{color:inherit!important}
  .w5 .w5-intro p,.w5 .w5-hl small,.w5 .w5-hood li span{color:var(--ls-text)!important}
  .w5 .w5-hero-sub,.w5 .w5-contact p{color:#fff!important}
  .w5 .w5-eyebrow{color:var(--ls-accent)!important}
  .w5 .w5-contact .w5-eyebrow{color:#fff!important}
  .w5 .w5-form p{color:var(--ls-text)!important}
  .w5 .w5-want span{color:var(--ls-primary)!important}.w5 .w5-want input:checked+span{color:#fff!important}
  .w5 .w5-form textarea{height:110px!important;min-height:0!important}
  .w5 .w5-btn{border-radius:999px!important;min-height:0!important;box-shadow:none!important}
  .w5 .w5-btn.light{background:#fff!important;color:var(--ls-primary)!important}
  .w5 .w5-btn.solid{background:var(--ls-accent)!important;color:#fff!important}
  .w5 .w5-btn.dark{background:var(--ls-primary)!important;color:#fff!important}
  .w5-gal img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .5s}
  .w5-gal button:hover img{transform:scale(1.04)}
  .w5-gal .big{grid-column:span 2;grid-row:span 2}.w5-gal .wide{grid-column:span 2}
  .w5-center{text-align:center;margin-top:24px}
  .w5-open{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:16px;background:var(--ls-primary);color:#fff;border-radius:18px;padding:24px 28px;margin:0 var(--w5-pad)}
  .w5-open b{font:500 24px var(--ls-head)}.w5-open small{display:block;opacity:.85;font-size:15px}
  .w5-hood{display:grid;grid-template-columns:1fr 1fr;gap:clamp(24px,5vw,64px);align-items:center}
  .w5-hood ul{list-style:none;padding:0;margin:18px 0 22px;display:grid;gap:10px}
  .w5-hood li{display:flex;justify-content:space-between;gap:12px;padding:12px 16px;background:#fff;border-radius:12px}
  .w5-hood li b{color:var(--ls-primary)}
  .w5-hood img{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:18px;display:block}
  .w5-contact{display:grid;grid-template-columns:1fr 1.1fr;gap:clamp(24px,5vw,64px);align-items:start;background:var(--ls-primary);color:#fff;border-radius:26px;padding:clamp(26px,4vw,52px);margin:0 var(--w5-pad) clamp(48px,7vw,96px)}
  .w5-contact h2{font-size:clamp(30px,3.4vw,44px)!important;color:#fff!important;margin-bottom:14px!important}
  .w5-agent{display:flex;gap:16px;align-items:center;margin:22px 0}
  .w5-agent img,.w5-agent .w5-ini{width:76px;height:76px;border-radius:50%;object-fit:cover;flex:none}
  .w5-ini{display:grid;place-items:center;background:var(--ls-accent);color:#fff;font:600 24px var(--ls-head)}
  .w5-agent b{display:block;font:500 22px var(--ls-head)}.w5-agent small{display:block;opacity:.85;font-size:14px}
  .w5-reach{display:flex;flex-wrap:wrap;gap:10px}
  .w5-form{background:#fff;color:var(--ls-text);border-radius:18px;padding:24px;display:grid;gap:10px}
  .w5-form h3{font-size:24px!important;color:var(--ls-primary)!important}
  .w5-want{display:flex;gap:8px;flex-wrap:wrap}
  .w5-want label{flex:1;min-width:140px}
  .w5-want input{position:absolute;opacity:0}
  .w5-want span{display:block;text-align:center;border-radius:999px;padding:10px 12px;font-weight:600;font-size:14px;background:var(--ls-tint);color:var(--ls-primary);cursor:pointer}
  .w5-want input:checked+span{background:var(--ls-primary);color:#fff}
  .w5 .w5-form input:not([type=radio]),.w5 .w5-form textarea{width:100%;border:1px solid color-mix(in srgb,var(--ls-primary) 22%,transparent)!important;border-radius:10px!important;padding:12px 14px!important;font:15px var(--ls-body)!important;background:#fff!important;color:#222!important}
  .w5-form .w5-btn{width:100%}
  .w5-fine{font-size:12.5px;opacity:.75;margin:0}
  .w5-foot{padding:28px var(--w5-pad) 96px;font-size:13px;display:grid;gap:8px;border-top:1px solid color-mix(in srgb,var(--ls-primary) 12%,transparent)}
  .w5-foot div{display:flex;flex-wrap:wrap;gap:6px 18px;opacity:.8}
  .w5-eho{display:inline-flex;align-items:center;gap:8px;font-weight:600}
  .w5-eho i{display:inline-block;width:22px;height:18px;border:2px solid currentColor;border-radius:2px;position:relative}
  .w5-eho i:before{content:"=";position:absolute;inset:0;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:14px;line-height:1}
  .w5-bar{display:none}
  .w5-lb{position:fixed;inset:0;z-index:100000;background:rgba(10,14,18,.94);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:14px;padding:20px}
  .w5-lb img{max-width:min(1200px,94vw);max-height:78vh;border-radius:10px}
  .w5-lb-row{display:flex;gap:10px;align-items:center;color:#fff;font:600 14px system-ui}
  .w5-lb-row button{background:#fff;color:#12354d;border:0;border-radius:999px;padding:10px 20px;font-weight:600;cursor:pointer}
  .w5-narrow .w5-links{display:none}
  @media(max-width:760px){.w5-links{display:none}.w5-nav .w5-btn{display:none}}
  .w5-narrow .w5-nav .w5-btn{display:none}
  @media(max-width:760px){.w5-ch,.w5-ch.flip{grid-template-columns:1fr;gap:18px}.w5 .w5-ch-pics{padding-bottom:16%}.w5 .w5-ch-pics .main{width:92%!important;height:62vw!important;max-height:none!important;aspect-ratio:auto!important}.w5 .w5-ch-pics .inset{width:40%!important;height:40vw!important;aspect-ratio:auto!important}.w5-ch.flip .w5-ch-pics{order:0}.w5-quick div{flex:1 1 33%;padding:14px 8px}.w5-quick b{font-size:17px}.w5-ch-num{font-size:44px}.w5-intro,.w5-hood,.w5-contact{grid-template-columns:1fr}.w5-hl{grid-template-columns:1fr}.w5-gal{grid-template-columns:repeat(2,1fr);grid-auto-rows:150px}.w5-gal .big{grid-column:span 2}.w5-hero{min-height:74vh}.w5-hero-btns .w5-btn{flex:1}
    .w5-bar{display:grid;grid-template-columns:1fr 1fr 1.6fr;gap:8px;position:fixed;left:0;right:0;bottom:0;z-index:20;padding:10px 12px calc(10px + env(safe-area-inset-bottom));background:var(--ls-page);box-shadow:0 -8px 24px -12px rgba(0,0,0,.3)}
    .w5-bar .w5-btn{padding:12px 8px;font-size:14px}.w5-contact{border-radius:20px}}
  .lp-view .w5-bar,.home-site-view .w5-bar{display:none!important}
  .lp-view .w5-hero{min-height:440px}
  .lp-stats.w5-stats{grid-template-columns:repeat(4,1fr)}
  /* Your website, on the campaign page */
  .ws-box{display:flex;flex-wrap:wrap;align-items:center;gap:16px 22px;background:#fff;border:1px solid #d8effd;border-radius:18px;padding:16px 18px;margin:0 0 18px}
  .ws-thumb{width:96px;height:72px;border-radius:10px;background-size:cover;background-position:center;flex:none}
  .ws-txt{flex:1;min-width:220px;color:#12354d}
  .ws-txt b{display:block;font-size:16px}
  .ws-txt a{color:#12354d;text-decoration:underline;font-size:14px;word-break:break-all}
  .ws-txt small{display:block;font-size:13px;margin-top:2px;color:#12354d;opacity:.85}
  .ws-btns{display:flex;flex-wrap:wrap;gap:8px}
  .lp-bar a{color:inherit;text-decoration:underline}
  .ws-btns button{border:0;border-radius:999px;padding:11px 18px;font:600 14px 'DM Sans',sans-serif;cursor:pointer}
  .ws-btns .go{background:#12354d;color:#fff}.ws-btns .soft{background:#e2f0f8;color:#12354d}
  html.dark .shell .ws-box{background:#fff}
  .ws-share{display:grid;gap:8px;margin-top:14px}
  .ws-share button{display:flex;gap:12px;align-items:center;width:100%;text-align:left;border:0;border-radius:12px;padding:13px 14px;background:#e2f0f8;color:#12354d;font:600 15px 'DM Sans',sans-serif;cursor:pointer}
  .ws-share button{flex-direction:column;align-items:flex-start;gap:2px}
  .ws-share small{display:block!important;font-weight:400;font-size:13px}
  .ws-qr{display:grid;place-items:center;margin-top:10px}
  `;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const OAK = {
    status: 'Just listed', headline: 'A Hill Country home built around the view.',
    story: ['Limestone, glass and white oak open to a long infinity pool, a covered outdoor room with a stone fireplace, and views that run all the way to Lake Travis.',
      'Inside, the main living spaces flow into one another under vaulted ceilings, with walls of glass on both sides, so the light moves through the house all day.'],
    sheet: [['Price', '$845,000'], ['Bedrooms', '4'], ['Bathrooms', '3.5'], ['Living area', '3,420 sq ft'], ['Lot', '1.2 acres'], ['Year built', '2019'], ['Garage', '3 cars']],
    highlights: [['photo-07', 'Infinity-edge pool', 'Set on the edge of the slope, looking out over the hills.'], ['photo-10', 'Lake views', 'From the deck, the kitchen and the primary suite.'], ['photo-08', 'An outdoor room', 'Covered, with a stone fireplace and space to gather.']],
    gallery: ['photo-01', 'photo-02', 'photo-03', 'photo-04', 'photo-05', 'photo-06', 'photo-07', 'photo-08', 'photo-09', 'photo-10', 'photo-11', 'photo-12', 'photo-13', 'photo-14'],
    hood: [['Downtown Austin', '25 min'], ['Lake Travis', '6 min'], ['Hill Country Galleria', '12 min'], ['Austin-Bergstrom Airport', '40 min']],
    open: ['Open house', 'Saturday, Nov 29 · 1:00 to 4:00 PM'],
    chapters: [
      ['The arrival', 'It starts at the threshold.', 'A limestone path winds up under old live oaks to a wide white oak door. Open it, and the house gives you the view straight away: glass from front to back, and the hills beyond.', 'photo-11', 'photo-01'],
      ['The heart of the house', 'One big room, full of light.', 'Vaulted ceilings, walls of glass on both sides and a stone fireplace that anchors it all. The kitchen sits right in the middle, so whoever is cooking is never out of the conversation.', 'photo-04', 'photo-03'],
      ['The evenings', 'Where the day ends up.', 'Step out to the covered outdoor room with its own fireplace, then down to the infinity pool on the edge of the slope. At sunset the water and the lake line up.', 'photo-07', 'photo-08'],
      ['The mornings', 'Mornings feel this quiet.', 'The primary suite looks out into the trees. Wake up to the light coming through the oaks, and coffee on the deck above the valley.', 'photo-06', 'photo-10']
    ],
    note: 'This is one of those homes you have to stand in to understand. Come at golden hour if you can: that is when the light runs through the whole house and across the pool. I would love to show you around.'
  };
  const P = n => 'sample/' + n + '.jpg';
  let w5Photos = [];

  window.listingSiteHTML = function (c, index) {
    const d = listingSiteData(c);
    loadListingFonts(d.fonts);
    const x = c.address === '1248 Oakridge Drive' ? OAK : null;
    const photos = x ? x.gallery.map(P) : d.photos;
    w5Photos = photos;
    const first = d.agent.split(' ')[0];
    const tel = d.phone.replace(/[^\d+]/g, '');
    const facts = [d.beds && d.beds + ' beds', d.baths && d.baths + ' baths', d.sqft && d.sqft + ' sq ft', d.lot].filter(Boolean);
    const sheet = x ? x.sheet : [['Price', d.price], ['Bedrooms', d.beds], ['Bathrooms', d.baths], ['Living area', d.sqft && d.sqft + ' sq ft'], ['Lot', d.lot]].filter(r => r[1]);
    const hero = photos[0];
    const tiles = photos.slice(0, 8).map((p, i) => `<button type="button" class="${i === 0 ? 'big' : i === 3 ? 'wide' : ''}" onclick="w5Light(${i})" aria-label="Open photo ${i + 1}"><img src="${esc(p)}" alt="" loading="lazy"></button>`).join('');
    const legal = d.legal.filter(l => !/equal housing/i.test(l));
    const hs = d.headStyle || {};
    return `<div class="lsite w5${hs.dash ? ' w5-dash' : ''}${hs.bold ? ' w5-bold' : ''}" style="${hs.weight ? `--ls-hw:${hs.weight};` : ''}${hs.case ? `--ls-hcase:${hs.case};` : ''}${hs.stretch ? `--ls-hstretch:${hs.stretch};` : ''}${hs.ls ? `--ls-hls:${hs.ls};` : ''}${hs.lh ? `--ls-hlh:${hs.lh};` : ''}${d.second ? `--ls-second:${esc(d.second)};` : ''}--ls-primary:${esc(d.primary)};--ls-accent:${esc(d.accent)};--ls-tint:${esc(d.tint)};--ls-page:${esc(d.page)};--ls-text:${esc(d.text)};--ls-head:'${esc(d.fonts[0])}',Georgia,serif;--ls-body:'${esc(d.fonts[1] || d.fonts[0])}',system-ui,sans-serif">
  <nav class="w5-nav"><a class="w5-brand" href="#">${d.logo ? `<img src="${esc(d.logo)}" alt="${esc(d.brokerage)}" onerror="this.replaceWith(document.createTextNode(this.alt))">` : esc(d.brokerage || d.agent)}</a>
    <div class="w5-links"><a href="#" onclick="return w5Go(this,'w5-photos')">Photos</a><a href="#" onclick="return w5Go(this,'w5-details')">Details</a><a href="#" onclick="return w5Go(this,'w5-hood')">Neighborhood</a><a href="#" onclick="return w5Go(this,'w5-contact')">Contact</a></div>
    <a class="w5-btn dark" href="#" onclick="return w5Go(this,'w5-contact')">Schedule a showing</a></nav>
  <header class="w5-hero"><div class="w5-hero-img" style="background-image:url('${esc(hero)}')"></div>
    <div class="w5-hero-in">${x ? `<span class="w5-chip">${esc(x.status)}</span>` : ''}
      <h1>${esc(d.address)}</h1><p class="w5-hero-sub">${esc(d.city)}</p>
      <div class="w5-hero-row">${d.price ? `<span class="w5-price">${esc(d.price)}</span>` : ''}<span class="w5-facts">${facts.map(f => `<span>${esc(f)}</span>`).join('')}</span></div>
      <div class="w5-hero-btns"><a class="w5-btn solid" href="#" onclick="return w5Go(this,'w5-contact')">Schedule a showing</a><button type="button" class="w5-btn light" onclick="w5Light(0)">${photos.length === 1 ? 'See the photo' : `See all ${photos.length} photos`}</button>${x ? `<button type="button" class="w5-btn light" onclick="toast('On the live page, the listing video plays right here behind the address, muted and looping. This button turns the sound on.')">Sound on</button>` : ''}</div></div>${x ? '<span class="w5-vtag">Listing video plays here</span>' : ''}</header>
  <div class="w5-quick" id="w5-details">${sheet.map(r => `<div><small>${esc(r[0])}</small><b>${esc(String(r[1]))}</b></div>`).join('')}</div>
  ${x ? `<section class="w5-sec w5-prologue"><span class="w5-eyebrow">The story of ${esc(d.address)}</span><h2>${esc(x.headline)}</h2></section>
  ${x.chapters.map((ch, i) => `<section class="w5-ch${i % 2 ? ' flip' : ''}"><div class="w5-ch-pics"><img class="main" src="${esc(P(ch[3]))}" alt="" loading="lazy"><img class="inset" src="${esc(P(ch[4]))}" alt="" loading="lazy"></div><div class="w5-ch-txt"><span class="w5-ch-num">${String(i + 1).padStart(2, '0')}</span><span class="w5-eyebrow">${esc(ch[0])}</span><h3>${esc(ch[1])}</h3><p>${esc(ch[2])}</p></div></section>`).join('')}` : `<section class="w5-sec w5-prologue"><span class="w5-eyebrow">About this home</span><h2>Welcome home.</h2>${d.about ? `<p>${esc(d.about)}</p>` : ''}</section>`}
  <section class="w5-sec" id="w5-photos"><span class="w5-eyebrow">Every photo</span><h2 class="w5-h2">Take a look around.</h2><div class="w5-gal">${tiles}</div><div class="w5-center"><button type="button" class="w5-btn dark" onclick="w5Light(0)">${photos.length === 1 ? 'View the photo' : `View all ${photos.length} photos`}</button></div></section>
  ${x && x.open ? `<div class="w5-open"><div><b>${esc(x.open[0])}</b><small>${esc(x.open[1])}</small></div><a class="w5-btn solid" href="#" onclick="return w5Go(this,'w5-contact')">Let ${esc(first)} know you're coming</a></div>` : ''}
  ${x ? `<section class="w5-sec w5-hood" id="w5-hood"><div><span class="w5-eyebrow">The neighborhood</span><h2 class="w5-h2">Quiet hills, close to everything.</h2><ul>${x.hood.map(h => `<li><span>${esc(h[0])}</span><b>${esc(h[1])}</b></li>`).join('')}</ul><a class="w5-btn dark" href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(d.address + ', ' + d.city)}" target="_blank" rel="noopener">Open in Maps</a></div><img src="${esc(P('photo-02'))}" alt="" loading="lazy"></section>` : ''}
  <section class="w5-contact" id="w5-contact"><div><span class="w5-eyebrow" style="color:#fff;opacity:.85">Your agent</span><h2>Want to see it in person?</h2>${x && x.note ? `<blockquote class="w5-note">“${esc(x.note)}”<cite>${esc(d.agent)}</cite></blockquote>` : `<p style="margin:0;opacity:.9">${esc(first)} will reply the same day, usually within the hour.</p>`}
      <div class="w5-agent">${d.headshot ? `<img src="${esc(d.headshot)}" alt="">` : `<span class="w5-ini">${esc(d.agent.split(' ').map(w => w[0]).slice(0, 2).join(''))}</span>`}<div><b>${esc(d.agent)}</b><small>${esc(d.brokerage)}</small>${d.license ? `<small>License ${esc(d.license)}</small>` : ''}${d.phone ? `<small>${esc(d.phone)}</small>` : ''}</div></div>
      <div class="w5-reach">${d.phone ? `<a class="w5-btn light" href="tel:${esc(tel)}" onclick="listingCallTap(event,${index})">Call ${esc(first)}</a><a class="w5-btn light" href="sms:${esc(tel)}" onclick="listingTextTap(event,${index})">Text ${esc(first)}</a>` : ''}</div></div>
    <form class="w5-form" onsubmit="event.preventDefault();listingFormSent(this,${index})"><h3>Contact ${esc(first)}</h3>
      <div class="w5-want"><label><input type="radio" name="want" value="showing" checked><span>Schedule a showing</span></label><label><input type="radio" name="want" value="question"><span>Ask a question</span></label></div>
      <input name="name" required placeholder="Your name" aria-label="Your name"><input name="email" type="email" required placeholder="Email" aria-label="Email"><input name="phone" type="tel" placeholder="Phone (optional)" aria-label="Phone">
      <textarea name="message" rows="3" placeholder="When would you like to see it?" aria-label="Message"></textarea>
      <input name="website" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px" value="">
      <button class="w5-btn solid">Send to ${esc(first)}</button><p class="w5-fine">Your details go only to ${esc(d.agent)}.</p></form></section>
  <footer class="w5-foot"><div>${legal.map(l => `<span>${esc(l)}</span>`).join('')}</div><div><span class="w5-eho"><i></i>Equal Housing Opportunity</span><span>Information is believed accurate but not guaranteed. Buyers should verify all details.</span></div></footer>
  <div class="w5-bar">${d.phone ? `<a class="w5-btn dark" href="tel:${esc(tel)}" onclick="listingCallTap(event,${index})">Call</a><a class="w5-btn dark" href="sms:${esc(tel)}" onclick="listingTextTap(event,${index})">Text</a>` : ''}<a class="w5-btn solid" href="#" onclick="return w5Go(this,'w5-contact')">Schedule a showing</a></div>
</div>`;
  };

  window.listingTextTap = function (event, index) {
    if (listingPublic()) { try { navigator.sendBeacon('/api/public/listing/' + encodeURIComponent(listingPublic()) + '/text'); } catch (e) {} return; }
    event.preventDefault();
    const c = [...state.campaigns, ...examples][index];
    if (typeof campaignLeads === 'function' && !(typeof leadsIsServer === 'function' && leadsIsServer(c))) {
      campaignLeads(c).unshift({ id: Date.now(), source: 'text', name: 'Text from your listing page', where: 'Listing page text button', ago: 'Just now', text: 'Tapped Text on your listing page.', done: false });
      persist();
    }
    if (typeof refreshLeads === 'function') refreshLeads(index);
    refreshListingStats(index);
    toast('Text tap counted as a text lead. On a phone this opens Messages.');
  };
  const statsHTML = s => `<div><b>${s.visits.toLocaleString()}</b><small>Visits</small></div><div><b>${s.forms}</b><small>Form leads</small></div><div><b>${s.calls}</b><small>Call leads</small></div><div><b>${s.texts}</b><small>Text leads</small></div>`;
  const baseStats = window.listingPageStats;
  window.listingPageStats = function (c) {
    const out = baseStats(c);
    const leads = (typeof campaignLeads === 'function') ? campaignLeads(c) : [];
    out.texts = leads.filter(l => l.source === 'text').length;
    return out;
  };
  const basePanel = window.listingPagePanel;
  window.listingPagePanel = function (c, index, draft) {
    return basePanel(c, index, draft).replace(/fills in the form or taps Call/g, 'fills in the form, taps Call or taps Text')
      .replace(/<button type="button" class="campaign-primary" onclick="openListingPage\((\d+)\)">View full page<\/button>/, (m, i) => `<div class="ws-btns"><button class="go" onclick="openListingPage(${i})">Preview your website</button><button class="soft" onclick="wsCopy(${i})">Copy link</button><button class="soft" onclick="wsShare(${i})">Share</button></div>`)
      .replace(/<div class="lp-bar">([^<]*)<\/div>/, (m, a) => `<div class="lp-bar"><a href="#" onclick="openListingPage(${index});return false">${a}</a></div>`)
      .replace(/<div class="lp-stats">[\s\S]*?<\/div><\/div>/, '<div class="lp-stats w5-stats">' + statsHTML(listingPageStats(c)) + '</div>');
  };
  window.refreshListingStats = function (index) {
    const c = [...state.campaigns, ...examples][index];
    document.querySelectorAll('.lp-stats').forEach(el => { el.classList.add('w5-stats'); el.innerHTML = statsHTML(listingPageStats(c)); });
  };
  window.w5Go = function (el, id) {
    const root = el.closest('.lsite'); const t = root && root.querySelector('#' + id);
    if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return false;
  };
  window.w5Light = function (i) {
    document.querySelector('.w5-lb')?.remove();
    const n = w5Photos.length; let k = ((i % n) + n) % n;
    const lb = document.createElement('div'); lb.className = 'w5-lb';
    const draw = () => { lb.innerHTML = `<img src="${esc(w5Photos[k])}" alt="Photo ${k + 1}"><div class="w5-lb-row"><button onclick="event.stopPropagation();w5Light(${k - 1})">Previous</button><span>${k + 1} of ${n}</span><button onclick="event.stopPropagation();w5Light(${k + 1})">Next</button><button onclick="this.closest('.w5-lb').remove()">Close</button></div>`; };
    draw(); lb.onclick = e => { if (e.target === lb) lb.remove(); };
    document.body.appendChild(lb);
  };

  // Your website: on every unlocked campaign, review or live.
  const live = c => 'https://' + listingPageAddress(c);
  function websiteBox(c, index) {
    const photo = c.address === '1248 Oakridge Drive' ? P('photo-01') : (listingSiteData(c).photos[0]);
    return `<div class="ws-box" id="ws-box"><span class="ws-thumb" style="background-image:url('${esc(photo)}')"></span>
      <div class="ws-txt"><b>Your website for this home</b><a href="#" onclick="openListingPage(${index});return false">${esc(listingPageAddress(c))}</a><small>Live now. Your posts and ad send people here. Share it with anyone.</small></div>
      <div class="ws-btns"><button class="go" onclick="openListingPage(${index})">Preview your website</button><button class="soft" onclick="wsCopy(${index})">Copy link</button><button class="soft" onclick="wsShare(${index})">Share</button></div></div>`;
  }
  window.wsCopy = function (index) {
    const c = [...state.campaigns, ...examples][index];
    try { navigator.clipboard.writeText(live(c)); } catch (e) {}
    toast('Link copied. Paste it into a text, an email or a post.');
  };
  window.wsShare = function (index) {
    const c = [...state.campaigns, ...examples][index], url = live(c), d = listingSiteData(c);
    const title = c.address + (d.price ? ' · ' + d.price : '');
    if (navigator.share && /Mobi|Android|iPhone/i.test(navigator.userAgent)) { navigator.share({ title, text: 'Take a look at ' + c.address, url }).catch(() => {}); return; }
    const body = encodeURIComponent('Take a look at ' + c.address + ':\n' + url);
    show(`<span class="eyebrow">SHARE YOUR WEBSITE</span><h2>Send ${esc(c.address)} to anyone.</h2>
      <p>Your link shows a photo of the home and the price wherever you paste it.</p>
      <div class="ws-share">
        <button onclick="wsCopy(${index})">Copy link<small>${esc(url)}</small></button>
        <button onclick="location.href='mailto:?subject=${encodeURIComponent(title)}&body=${body}'">Email it<small>Opens your email with the link in it</small></button>
        <button onclick="location.href='sms:?&body=${body}'">Text it<small>On your phone, opens Messages with the link in it</small></button>
      </div>
      <div class="ws-actions" style="margin-top:16px"><button class="campaign-primary" onclick="modal.close()">Done</button></div>`);
  };

  // Review: the website is built with everything else, so it sits with the plan and the calendar.
  const baseDetails5 = window.details;
  window.details = function (index) {
    baseDetails5.apply(this, arguments);
    const c = [...state.campaigns, ...examples][index];
    if (!c || document.getElementById('listing-page')) return;
    const step = [...document.querySelectorAll('#content .campaign-step-title')].find(h => /Ready to go\?|Campaign approved/.test(h.textContent));
    const sec = step && (step.closest('.review-approval') || step.closest('section, .panel'));
    if (!sec) return;
    sec.insertAdjacentHTML('beforebegin', listingPagePanel(c, index, true).replace(/Resmara built this website for the home in your brand\.[^<]*/, 'Resmara built this website for the home in your brand, with your campaign. It tells the home’s story, and your posts and ad send people here. Look it over, and share the link with anyone.'));
    const span = step.querySelector('span'); if (span) span.textContent = '4';
    if (typeof setupFolds === 'function') setupFolds();
  };
  const w5Oak = () => Math.max(0, [...state.campaigns, ...examples].findIndex(c => c.address === '1248 Oakridge Drive'));
  const h5 = window.__previewHash || location.hash;
  if (h5 === '#website') setTimeout(() => { history.replaceState(null, '', location.pathname + '#website'); state.clientSignedIn = true; dashboard('campaigns'); details(w5Oak()); }, 80);
})();

// Review copy only: Engine 6 mockup (the active campaign). Two reports on day 7 and day 14: the
// agent's full report (ad spend, hooks, leads by source, every post, the ad audit log) and the
// seller version (no cost or spend), downloadable for the agent to send.
(function () {
  const css = `
  .r6-tabs{display:inline-flex;background:#e2f0f8;border-radius:999px;padding:4px;gap:4px}
  .r6-tabs button{border:0;border-radius:999px;padding:8px 16px;font:600 14px 'DM Sans',sans-serif;background:transparent;color:#12354d;cursor:pointer}
  .r6-tabs button.on{background:#12354d;color:#fff}
  #pr-view.r6-agent .pr-doc.r6-seller{display:none}
  #pr-view:not(.r6-agent) .pr-doc.r6-agentdoc{display:none}
  .r6-note{font-size:13px;color:#12354d;margin:0 0 12px}
  .r6-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
  .r6-grid>div{background:#f2f8fc;border-radius:14px;padding:14px}
  .r6-grid b{display:block;font:400 22px 'Archivo Black','Arial Black',sans-serif;color:#12354d;letter-spacing:-.5px}
  .r6-grid span{display:block;font-size:12px;color:#12354d;opacity:.75;margin-top:4px}
  .r6-tbl{width:100%;border-collapse:collapse;font-size:13.5px;color:#12354d}
  .r6-tbl th{text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.7;padding:8px 10px;border-bottom:1px solid #d8effd}
  .r6-tbl td{padding:9px 10px;border-bottom:1px solid #eef5fa;vertical-align:middle}
  .r6-tbl td.n,.r6-tbl th.n{text-align:right;white-space:nowrap}
  .r6-tag{display:inline-block;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700}
  .r6-tag.win{background:#12354d;color:#fff}.r6-tag.swap{background:#d94c0d;color:#fff}.r6-tag.new{background:#e2f0f8;color:#12354d}
  .r6-bars{display:grid;gap:8px}
  .r6-bar{display:grid;grid-template-columns:150px 1fr 40px;gap:10px;align-items:center;font-size:13.5px;color:#12354d}
  .r6-bar i{display:block;height:12px;border-radius:6px;background:#12354d}
  .r6-bar.o i{background:#d94c0d}
  .r6-log{list-style:none;margin:0;padding:0;display:grid;gap:8px}
  .r6-log li{display:grid;grid-template-columns:120px 1fr;gap:12px;font-size:13.5px;color:#12354d;background:#f2f8fc;border-radius:12px;padding:10px 12px}
  .r6-log b{font-weight:700}
  .r6-recs{margin:0;padding-left:18px;color:#12354d;font-size:14px;display:grid;gap:6px}
  @media(max-width:900px){.r6-grid{grid-template-columns:repeat(3,1fr)}}
  `;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  const n = v => Number(v).toLocaleString('en-US');

  function agentSections(day) {
    const full = day >= 14, k = full ? 1 : 0.52;
    const spend = full ? 50 : 23.4, clicks = Math.round(238 * k * 1.02);
    const hooks = [
      ['Have you seen a pool like this?', Math.round(4200 * k), Math.round(101 * k), 'win', 'Winning'],
      ['This entry sets the tone.', Math.round(3900 * k), Math.round(62 * k), '', ''],
      ['Wait till you see the back porch.', 1310, 8, 'swap', 'Replaced on day 3'],
      ['Sunsets come with the house.', Math.round(2600 * k), Math.round(48 * k), 'new', 'Added on day 3']
    ];
    const leads = [['Ad comments', 1], ['Post comments', 2], ['Website form', 1], ['Calls', 1], ['Texts', 1]];
    const maxL = Math.max(...leads.map(l => l[1]));
    const sources = [['The ad', 61], ['Facebook posts', 27], ['Shared link', 12]];
    const P = typeof SAMPLE_POSTS !== 'undefined' ? SAMPLE_POSTS : [];
    const posts = Array.from({ length: full ? 14 : 7 }, (_, i) => { const s = 0.7 + ((i * 37) % 9) / 10; return [i + 1, (P[i] && P[i].headline) || 'Day ' + (i + 1) + ' post', Math.round(980 * s), Math.round(46 * s), Math.round(9 * s), Math.round(7 * s), Math.round(12 * s)]; });
    const log = [
      ['Day 1 · 8:02 AM', 'Meta approved the ad. It started delivering on time.'],
      ['Day 1 · 2:00 PM', 'Delivery normal. No ads ran overnight (11 PM to 6 AM), as set.'],
      ['Day 3 · 10:00 AM', 'Hook 3 ("Wait till you see the back porch") had 8 clicks from 1,310 views, far behind the others. Paused it and added a new hook: "Sunsets come with the house."'],
      ['Day 5 · 10:00 AM', 'Spending on pace: on track to use the full budget evenly over 14 days.'],
      full ? ['Day 9 · 10:00 AM', 'People were seeing the ad about 4 times each. Rotated hook 2 forward to keep it fresh.'] : null,
      ['Every day', 'Website up and the ad link working. Your Meta connection and payment method healthy.']
    ].filter(Boolean);
    return `
    <section class="pr-sec"><span class="pr-label">YOUR AD · ${full ? 'ALL 14 DAYS' : 'DAYS 1–7'} · FOR YOU ONLY</span>
      <div class="r6-grid"><div><b>$${spend.toFixed(2)}</b><span>Spent of $50.00</span></div><div><b>$${(spend / clicks).toFixed(2)}</b><span>Cost per click</span></div><div><b>${n(clicks)}</b><span>Link clicks</span></div><div><b>${(clicks / (full ? 120 : 62)).toFixed(1)}%</b><span>Click rate</span></div><div><b>${n(Math.round(9840 * k))}</b><span>People reached</span></div><div><b>${full ? '2.4' : '1.9'}</b><span>Times each person saw it</span></div></div></section>
    <section class="pr-sec"><span class="pr-label">YOUR HOOKS, SIDE BY SIDE</span>
      <table class="r6-tbl"><tr><th>Hook</th><th class="n">Views</th><th class="n">Clicks</th><th class="n">Click rate</th><th></th></tr>
      ${hooks.map(h => `<tr><td>${esc(h[0])}</td><td class="n">${n(h[1])}</td><td class="n">${n(h[2])}</td><td class="n">${(h[2] / h[1] * 100).toFixed(1)}%</td><td class="n">${h[4] ? `<span class="r6-tag ${h[3]}">${h[4]}</span>` : ''}</td></tr>`).join('')}</table></section>
    <section class="pr-sec"><span class="pr-label">LEADS BY SOURCE</span>
      <div class="r6-bars">${leads.map(l => `<div class="r6-bar${/Calls|Texts|form/.test(l[0]) ? ' o' : ''}"><span>${l[0]}</span><i style="width:${l[1] / maxL * 100}%"></i><b>${l[1]}</b></div>`).join('')}</div></section>
    <section class="pr-sec"><span class="pr-label">YOUR WEBSITE</span>
      <p class="r6-note"><b>${n(full ? 412 : 214)} visits</b> to homes.resmara.com/1248-oakridge-drive. Where they came from:</p>
      <div class="r6-bars">${sources.map(s => `<div class="r6-bar"><span>${s[0]}</span><i style="width:${s[1]}%"></i><b>${s[1]}%</b></div>`).join('')}</div></section>
    <section class="pr-sec"><span class="pr-label">EVERY POST</span>
      <table class="r6-tbl"><tr><th>Day</th><th>Post</th><th class="n">Reach</th><th class="n">Likes</th><th class="n">Comments</th><th class="n">Saves</th><th class="n">Clicks</th></tr>
      ${posts.map(p => `<tr><td>${p[0]}</td><td>${esc(p[1])}</td><td class="n">${n(p[2])}</td><td class="n">${p[3]}</td><td class="n">${p[4]}</td><td class="n">${p[5]}</td><td class="n">${p[6]}</td></tr>`).join('')}</table></section>
    <section class="pr-sec"><span class="pr-label">WHAT RESMARA CHECKED AND CHANGED (AD AUDIT)</span>
      <ul class="r6-log">${log.map(l => `<li><b>${l[0]}</b><span>${esc(l[1])}</span></li>`).join('')}</ul></section>
    <section class="pr-sec"><span class="pr-label">FOR YOU: WHAT TO DO NEXT</span>
      <ol class="r6-recs"><li>Call Emily Carter back today: she asked to tour Saturday morning (website form).</li><li>Reply to the 2 post comments asking if it's still available. They're on your board under Campaign leads.</li><li>${full ? 'Interest was still climbing on day 13. Run it until it sells keeps it going with a fresh round.' : 'The pool hook is winning. Week two keeps leading with it.'}</li><li>Download the seller version and send it to your seller.</li></ol></section>`;
  }

  const baseOpen = window.openPropertyReport;
  window.openPropertyReport = async function (index, day, btn) {
    await baseOpen.apply(this, arguments);
    const box = document.querySelector('#pr-view'); if (!box) return;
    const seller = box.querySelector('.pr-doc'); if (!seller || box.querySelector('.r6-agentdoc')) return;
    seller.classList.add('r6-seller');
    const agent = seller.cloneNode(true); agent.classList.remove('r6-seller'); agent.classList.add('r6-agentdoc');
    const kick = agent.querySelector('.pr-kicker'); if (kick) kick.textContent = kick.textContent.replace('PROPERTY REPORT', 'YOUR REPORT').replace('FINAL REPORT', 'YOUR FINAL REPORT');
    const first = agent.querySelector('.pr-sec'); if (first) first.insertAdjacentHTML('afterend', agentSections(day));
    const foot = agent.querySelector('.pr-foot span:last-child'); if (foot) foot.textContent = 'For you only: includes ad spend · Example report, illustrative numbers';
    seller.insertAdjacentElement('afterend', agent);
    box.classList.add('r6-agent');
    const bar = box.querySelector('.pr-bar');
    if (bar) bar.innerHTML = `<div class="r6-tabs" role="tablist"><button class="on" onclick="r6View(this,true)">Your report</button><button onclick="r6View(this,false)">Seller version</button></div>
      <div><button type="button" class="pr-close" onclick="openPropertyReport(${index},${day},document.querySelector('.pr-pick.on'))">Close</button><button type="button" class="campaign-primary" onclick="downloadReportPDF(this)">Download seller version (PDF)</button></div>`;
    bar.insertAdjacentHTML('afterend', `<p class="r6-note">Your report includes your ad spend and is just for you. The seller version has no cost or spend anywhere: download it and send it to your seller.</p>`);
  };
  window.r6View = function (b, agent) {
    const box = document.querySelector('#pr-view'); box.classList.toggle('r6-agent', agent);
    b.parentNode.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
  };

  // Pending or sold: the agent can tell us from the same Pause pop-up, and Resmara pauses
  // everything right away when it reads it from the listing itself.
  const status = c => ((state.listingStatus || {})[c && c.address]) || '';
  window.pauseCampaign = function (i) {
    const c = [...state.campaigns, ...examples][i];
    show(`<span class="eyebrow">PAUSE CAMPAIGN</span><h2>Pause ${esc(c.address)}?</h2>
      <p>Your scheduled posts stop and your listing ad pauses, so Meta stops spending your ad budget. Nothing is deleted. Resume any time and it picks up where it left off.</p>
      <div class="w6-pend"><b>Did it go pending or sell?</b><span>Tell us and we stop all marketing right away: your ad, your posts and your website's showing requests.</span>
      <div class="w6-pend-btns"><button class="campaign-primary" onclick="w6Mark(${i},'pending')">It's pending</button><button class="campaign-primary" onclick="w6Mark(${i},'sold')">It sold</button></div></div>
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Keep running</button><button class="campaign-primary" onclick="setCampaignPaused(${i},true)">Just pause it</button></div>`);
  };
  window.w6Mark = function (i, st) {
    const c = [...state.campaigns, ...examples][i];
    state.listingStatus = Object.assign({}, state.listingStatus, { [c.address]: st });
    setCampaignPaused(i, true);
    toast(st === 'sold' ? 'Congratulations. Your ad, posts and showing requests are stopped, and your website shows Sold.' : 'Paused right away: your ad, your posts and your website’s showing requests. Your website shows Pending.');
  };
  const baseResume = window.resumeCampaign;
  window.resumeCampaign = function (i) {
    const c = [...state.campaigns, ...examples][i];
    if (status(c)) { const m = Object.assign({}, state.listingStatus); delete m[c.address]; state.listingStatus = m; }
    baseResume(i);
  };
  const baseCard = window.campaignCard;
  window.campaignCard = function (c, top) {
    const html = baseCard.apply(this, arguments), st = status(c);
    if (!st || !campaignPaused(c)) return html;
    return st === 'sold'
      ? html.replace('>Paused<', '>Completed · Sold<').replace(/<button type="button" class="card-pause resume"[^>]*>[^<]*<\/button>/, '')
      : html.replace('>Paused<', '>Paused · Pending<');
  };
  // The website stops marketing the home.
  const baseSite = window.listingSiteHTML;
  window.listingSiteHTML = function (c, index) {
    let html = baseSite.apply(this, arguments); const st = status(c);
    if (!st) return html;
    const label = st === 'sold' ? 'Sold' : 'Pending';
    html = html.replace(/<span class="w5-chip">[^<]*<\/span>/, `<span class="w5-chip">${label}</span>`)
      .replace(/Schedule a showing/g, 'Ask about similar homes')
      .replace('<header class="w5-hero">', `<div class="w6-banner">${st === 'sold' ? 'This home has sold.' : 'This home is under contract.'} Ask ${esc(listingSiteData(c).agent.split(' ')[0])} about similar homes.</div><header class="w5-hero">`)
      .replace(/<span class="w5-vtag">[^<]*<\/span>/, '').replace(/<button type="button" class="w5-btn light" onclick="toast\('On the live page, the listing video[^"]*">Sound on<\/button>/, '');
    return html;
  };
  const st6 = document.createElement('style');
  st6.textContent = `.w6-pend{background:#e2f0f8;border-radius:14px;padding:14px 16px;margin:14px 0;color:#12354d}
    .w6-pend b{display:block;font-size:16px}.w6-pend span{display:block;font-size:14px;margin:4px 0 10px}
    .w6-pend-btns{display:flex;gap:8px;flex-wrap:wrap}.w6-pend-btns .campaign-primary{background:#12354d!important}
    .w6-banner{background:var(--ls-accent);color:#fff;text-align:center;font-weight:700;padding:12px 16px;font-size:15px}`;
  document.head.appendChild(st6);
  const h6 = window.__previewHash || location.hash;
  if (h6 === '#pending') setTimeout(() => {
    history.replaceState(null, '', location.pathname + '#pending'); state.clientSignedIn = true;
    const i = Math.max(0, [...state.campaigns, ...examples].findIndex(c => c.address === '1248 Oakridge Drive'));
    dashboard('campaigns'); pauseCampaign(i);
  }, 80);
})();

// Review copy only: Engine 8 mockup (Run it until it sells). The emails a set-and-forget agent
// gets, and the card when a renewal is on hold. Open with #emails.
(function () {
  const css = `
  .e8-wrap{max-width:760px;margin:0 auto;padding:28px 18px 60px;display:grid;gap:26px}
  .e8-intro h1{margin:0 0 6px;color:#12354d;font:800 30px 'DM Sans',sans-serif}
  .e8-intro p{margin:0;color:#12354d}
  .e8-label{font-size:12px;font-weight:800;letter-spacing:.12em;color:#12354d;text-transform:uppercase;margin-bottom:8px}
  .e8-mail{background:#fff;border:1px solid #d8effd;border-radius:18px;overflow:hidden;box-shadow:0 16px 40px -30px rgba(18,53,77,.5)}
  .e8-meta{padding:12px 18px;border-bottom:1px solid #e2f0f8;font-size:13px;color:#12354d}
  .e8-meta b{display:block;font-size:15px}
  .e8-head{background:#12354d;padding:16px 22px}
  .e8-head img{height:26px;display:block}
  .e8-body{padding:22px 24px 26px;color:#12354d;font:15px/1.6 'DM Sans',sans-serif}
  .e8-body h2{margin:0 0 10px;font:800 22px/1.25 'DM Sans',sans-serif;color:#12354d}
  .e8-body p{margin:0 0 12px;color:#12354d}
  .e8-home{display:flex;gap:14px;align-items:center;background:#e2f0f8;border-radius:14px;padding:10px;margin:14px 0}
  .e8-home img{width:84px;height:62px;object-fit:cover;border-radius:10px}
  .e8-home b{display:block}.e8-home small{display:block;font-size:13px}
  .e8-btn{display:inline-block;background:#d94c0d;color:#fff;border-radius:999px;padding:12px 22px;font-weight:700;text-decoration:none;margin-top:4px}
  .e8-btn.navy{background:#12354d}
  .e8-btns{display:flex;gap:10px;flex-wrap:wrap}
  .e8-foot{padding:12px 24px;border-top:1px solid #e2f0f8;font-size:12px;color:#12354d;opacity:.8}
  .e8-card-hold{margin-top:8px;background:#d94c0d;color:#fff;border-radius:10px;padding:8px 12px;font-size:13px;font-weight:700;display:flex;justify-content:space-between;gap:8px;align-items:center}
  .e8-card-hold button{background:#fff;color:#12354d;border:0;border-radius:999px;padding:6px 12px;font-weight:700;cursor:pointer}
  `;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  const home = (sub) => `<div class="e8-home"><img src="sample/photo-01.jpg" alt=""><div><b>1248 Oakridge Drive</b><small>Austin, TX · ${sub || 'Run it until it sells is on'}</small></div></div>`;
  const mail = (label, from, subject, title, paras, buttons, note, sub) => `<section><div class="e8-label">${label}</div><article class="e8-mail">
    <div class="e8-meta"><b>${subject}</b>From Resmara &lt;support@resmara.com&gt; · to ${from}</div>
    <div class="e8-head"><img src="resmara-logo-white.png" alt="Resmara"></div>
    <div class="e8-body"><h2>${title}</h2>${home(sub)}${paras.map(p => `<p>${p}</p>`).join('')}<div class="e8-btns">${buttons}</div></div>
    <div class="e8-foot">${note || 'You turned on Run it until it sells for this home. Turn it off any time from the campaign card.'}</div></article></section>`;
  const btn = (t, navy) => `<a class="e8-btn${navy ? ' navy' : ''}" href="#" onclick="return false">${t}</a>`;
  window.e8Emails = function () {
    const to = 'morgan@morganco.com';
    document.querySelector('#content').innerHTML = `<div class="e8-wrap">
      <div class="e8-intro"><h1>Run it until it sells: the emails</h1><p>Agents on set it and forget it may not open Resmara for months, so these emails are how Resmara talks to them. One button each.</p></div>
      ${mail('1 · A round is renewed', to, 'Round 3 for 1248 Oakridge Drive goes live Saturday', 'Round 3 is ready and goes live Saturday.', ['We built a fresh 14 days for 1248 Oakridge Drive: new posts, a new story and new ads, led by what got the most attention last round.', 'We charged $39 to your card on file. It goes live Saturday at 8:00 AM with the same ad budget. <b>There’s nothing you need to do.</b>'], btn('See the campaign'))}
      ${mail('2 · It goes pending', to, '1248 Oakridge Drive went pending, so we paused your campaign', 'Looks like 1248 Oakridge Drive went pending.', ['We paused your ad, your posts and your website’s showing requests right away, so nothing is marketing the home while it’s under contract.', 'We’ll keep checking every day. If it comes back on the market, we’ll pick up where we left off. If it sells, we’ll close the campaign out. No new rounds are built or charged while it’s pending.'], btn('See the campaign'))}
      ${mail('3 · Back on the market', to, '1248 Oakridge Drive is back on the market. Your campaign is running again', '1248 Oakridge Drive is back on the market.', ['The listing shows for sale again with you as the listing agent, so your campaign is running again: your ad and the rest of this round’s posts picked up where they left off, and the renewals continue.', 'Your website is taking showing requests again.'], btn('See the campaign'))}
      ${mail('4 · The card is declined (after 3 tries)', to, 'We couldn’t renew your campaign for 1248 Oakridge Drive', 'We couldn’t renew your campaign.', ['Round 4 for 1248 Oakridge Drive is built and ready, but your card was declined, so nothing was charged and it hasn’t gone live.', 'Please check your billing on Resmara. As soon as your card works, round 4 goes live on its own.'], btn('Check billing'), 'We tried your card 3 times, once a day. Your current round finished as planned.')}
      ${mail('5 · Campaigns without it turned on: day 12', to, 'Keep the momentum going on 1248 Oakridge Drive', 'Keep the momentum going.', ['Your campaign for 1248 Oakridge Drive ends in 2 days. Run it again for a fresh 14 days of new posts and new ads, built from what worked this time.', 'Or turn on Run it until it sells, and we’ll keep it going every 2 weeks until it sells.'], btn('Run it again · $39') + btn('Run it until it sells', true), 'Run it again is $39 for 14 days. Your ad budget is billed separately by Meta.', 'Day 12 of 14')}
      ${mail('6 · A price change we can\u2019t read', to, 'We noticed a price change on 1248 Oakridge Drive', 'We noticed a price change on 1248 Oakridge Drive.', ['Your post on Instagram says the price on this home has improved, but we can\u2019t find the new price online yet, so your website isn\u2019t showing a price right now.', '<b>Would you like us to update it?</b> Pick one. Either way, your website and the posts that haven\u2019t gone out yet are updated right away.'], `<a class="e8-btn" href="#" onclick="e8Price();return false">Set a new price</a><a class="e8-btn navy" href="#" onclick="e8Price(true);return false">Don\u2019t show a price</a>`, 'These buttons are just for you and this home, and work for 7 days. No sign-in needed.', 'Your listing website')}
      <section id="e8-price-page"></section>
      <section><div class="e8-label">On the campaign card: renewal on hold</div><article class="card" style="max-width:360px"><img src="sample/photo-01.jpg" alt="" style="width:100%;height:170px;object-fit:cover;border-radius:16px 16px 0 0"><div style="padding:14px"><h3 style="margin:0;color:#12354d">1248 Oakridge Drive</h3><p style="margin:2px 0 0;color:#12354d">Austin, TX · Round 3, day 14 of 14</p><div class="e8-card-hold"><span>Renewal on hold: card declined</span><button onclick="dashboard('billing')">Check billing</button></div></div></article></section>
    </div>`;
    window.scrollTo(0, 0);
  };
  window.e8PriceDone = function (v) {
    const f = document.getElementById('e8-pf'); if (!f) return;
    const n = String(v || '').replace(/[^0-9]/g, '');
    f.outerHTML = n ? `<p><b>Saved. Your website now shows Listed at $${Number(n).toLocaleString('en-US')}</b>, and the posts that haven\u2019t gone out yet are updated.</p>`
      : `<p><b>Done. Your website won\u2019t show a price for this home</b>, and we won\u2019t ask again for this listing. Visitors see \u201cAsk Morgan about pricing\u201d instead.</p>`;
  };
  window.e8Price = function (noPrice) {
    const box = document.getElementById('e8-price-page');
    box.innerHTML = `<div class="e8-label">${noPrice ? 'After Don\u2019t show a price: one tap, done' : 'The page Set a new price opens'}</div><article class="e8-mail"><div class="e8-head"><img src="resmara-logo-white.png" alt="Resmara"></div>
      <div class="e8-body"><h2>What\u2019s the right price?</h2>${home('Your listing website')}
      <p>Please type in the current list price for this home. We\u2019ll update your website and the posts that haven\u2019t gone out yet.</p>
      <form id="e8-pf" onsubmit="event.preventDefault();e8PriceDone(this.p.value)">
        <label style="display:block;font-weight:700;margin:6px 0">Current list price</label>
        <input name="p" required inputmode="numeric" placeholder="$830,000" style="width:100%;max-width:320px;border:1px solid #d8effd;border-radius:12px;padding:12px 14px;font:600 18px 'DM Sans',sans-serif;color:#12354d">
        <div style="margin-top:12px"><button class="e8-btn" style="border:0;cursor:pointer">Save</button></div></form></div></article>`;
    if (noPrice) { const h = box.querySelector('h2'); if (h) h.textContent = 'Got it. No price on this listing.'; box.querySelector('.e8-body > p').remove(); e8PriceDone(''); }
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };
  const h8 = window.__previewHash || location.hash;
  if (h8 === '#emails') setTimeout(() => { history.replaceState(null, '', location.pathname + '#emails'); state.clientSignedIn = true; dashboard('campaigns'); e8Emails(); }, 90);
})();

// Engines 10 and 11 (Billing and Support): preview only, sample data. Open with #billing or #support.
(function () {
  const css = `.b10 .panel{margin-bottom:16px}.b10-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
  .b10-row p{margin:0;color:#12354d}.b10-btns{display:flex;gap:8px;flex-wrap:wrap}
  .b10-tbl{width:100%;border-collapse:collapse;font-size:14px;color:#12354d}.b10-tbl th{text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;padding:8px 10px;border-bottom:1px solid #d8effd}
  .b10-tbl td{padding:11px 10px;border-bottom:1px solid #eef5fa;vertical-align:middle}.b10-tbl .n{text-align:right;white-space:nowrap}
  .b10-tag{display:inline-block;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700;background:#12354d;color:#fff}.b10-tag.soft{background:#e2f0f8;color:#12354d}.b10-tag.org{background:#d94c0d}
  .b10-mini{border:0;border-radius:999px;padding:7px 14px;font:700 13px inherit;cursor:pointer;background:#e2f0f8;color:#12354d}
  .b10-card{display:flex;gap:14px;align-items:center}.b10-chip{width:46px;height:30px;border-radius:6px;background:#12354d;color:#fff;font:800 11px sans-serif;display:grid;place-items:center}
  .b10-stripe{border:1px solid #d8effd;border-radius:14px;padding:16px;background:#fff;margin:10px 0}.b10-stripe .field input{background:#f7fbff}
  .b10-stripe small{display:block;font-size:12px;color:#12354d;margin-top:8px}
  .s11-reqs article{border:1px solid #d8effd;border-radius:14px;padding:14px 16px;margin:0 0 12px;background:#fff}
  .s11-reqs .flex{display:flex;justify-content:space-between;gap:10px;align-items:center}
  .s11-msg{border-left:3px solid #d8effd;padding-left:10px;margin:10px 0 0;color:#12354d}.s11-msg.team{border-color:#d94c0d}
  .s11-msg span{font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
  .s11-sent{background:#e2f0f8;border-radius:14px;padding:14px 16px;color:#12354d;margin-top:10px}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  let untilOn = true, cardOn = true;

  window.myCredits = function () {
    const coming = untilOn ? `<table class="b10-tbl"><tr><th>Listing</th><th>Next round</th><th class="n">Amount</th><th>About</th><th></th></tr>
      <tr><td><b>1248 Oakridge Drive</b></td><td>Round 3</td><td class="n">$39 + tax where it applies</td><td>Dec 3</td><td class="n"><button class="b10-mini" onclick="b10TurnOff()">Turn off</button></td></tr></table>
      <p class="fine" style="margin:10px 0 0">Run it until it sells charges $39 every 2 weeks when each new round is built, until the home is marked sold or you turn it off.</p>`
      : `<p class="fine" style="margin:0">Nothing coming up. Run it until it sells isn't on for any listing.</p>`;
    $('#content').innerHTML = `<div class="b10"><div class="welcome billing-head"><h1>Billing</h1></div>
      <section class="panel"><h3>Card on file</h3>${cardOn ? `<div class="b10-row"><div class="b10-card"><span class="b10-chip">VISA</span><p><b>Visa ending 4417</b><br><span class="fine">Expires 08/28 · saved with Stripe; Resmara never sees the number</span></p></div>
        <div class="b10-btns"><button class="alt" onclick="b10Card()">Change card</button><button class="nc-cancel" onclick="b10Remove()">Remove</button></div></div>`
        : `<div class="b10-row"><p>No card saved yet. You'll add one when you unlock your next campaign.</p><button class="campaign-primary" onclick="b10Card()">Add a card</button></div>`}</section>
      <section class="panel"><h3>Coming up</h3>${coming}</section>
      <section class="panel"><h3>Purchases</h3><table class="b10-tbl"><tr><th>Date</th><th>Listing</th><th>What</th><th class="n">Amount</th><th class="n">Tax</th><th>Status</th><th></th></tr>
        <tr><td>Nov 19</td><td>1248 Oakridge Drive</td><td>Round 2 (Run it until it sells)</td><td class="n">$39.00</td><td class="n">$0.00</td><td><span class="b10-tag">Paid</span></td><td class="n"><button class="b10-mini" onclick="toast('Preview: opens Stripe’s receipt in a new tab.')">Receipt</button></td></tr>
        <tr><td>Nov 5</td><td>1248 Oakridge Drive</td><td>Campaign</td><td class="n">$49.00</td><td class="n">$0.00</td><td><span class="b10-tag">Paid</span></td><td class="n"><button class="b10-mini" onclick="toast('Preview: opens Stripe’s receipt in a new tab.')">Receipt</button></td></tr>
        <tr><td>Oct 28</td><td>76 Willow Lane</td><td>Campaign</td><td class="n">$49.00</td><td class="n">$0.00</td><td><span class="b10-tag soft">Refunded</span></td><td class="n"><button class="b10-mini" onclick="toast('Preview: opens Stripe’s receipt in a new tab.')">Receipt</button></td></tr></table>
        <p class="fine" style="margin:10px 0 0">Tax is added only where your state requires it. Your ad budget is billed by Meta to your own ad account, so it isn't here.</p></section>
      <div class="billing-close"><button class="campaign-primary" onclick="b10Close()">Close my account</button></div></div>`;
  };
  window.b10Card = function () {
    show(`<span class="eyebrow">CARD ON FILE</span><h2>${cardOn ? 'Change your card' : 'Add a card'}</h2>
      <p>The new card is used for every campaign and every Run it until it sells round.</p>
      <div class="b10-stripe"><label class="field">Card number<input readonly placeholder="1234 1234 1234 1234"></label>
        <div class="nc-row"><label class="field">Expiry<input readonly placeholder="MM / YY"></label><label class="field">CVC<input readonly placeholder="CVC"></label><label class="field">ZIP<input readonly placeholder="96001"></label></div>
        <small>Stripe's secure card form, inside this pop-up. Preview only: nothing can be typed here.</small></div>
      <div class="modal-actions"><button class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary" onclick="cardOn=true;modal.close();b10Saved()">Save card</button></div>`);
  };
  window.b10Saved = function () { cardOn = true; myCredits(); toast('Card saved. Every campaign and round is charged to it.'); };
  window.b10Remove = function () {
    if (untilOn) {
      show(`<span class="eyebrow">REMOVE CARD</span><h2>Run it until it sells needs a card.</h2><p>Run it until it sells is on for <b>1248 Oakridge Drive</b>. Add a new card, or turn it off first.</p>
        <div class="modal-actions"><button class="nc-cancel" onclick="modal.close()">Keep this card</button><button class="alt" onclick="b10TurnOff()">Turn it off</button><button class="campaign-primary" onclick="b10Card()">Add a new card</button></div>`);
      return;
    }
    show(`<span class="eyebrow">REMOVE CARD</span><h2>Remove Visa ending 4417?</h2><p>You'll add a card again when you unlock your next campaign.</p>
      <div class="modal-actions"><button class="nc-cancel" onclick="modal.close()">Keep it</button><button class="campaign-primary" onclick="cardOn=false;window.cardOn=false;modal.close();b10NoCard()">Remove card</button></div>`);
  };
  window.b10NoCard = function () { cardOn = false; myCredits(); toast('Card removed.'); };
  window.b10TurnOff = function () {
    show(`<span class="eyebrow">RUN IT UNTIL IT SELLS</span><h2>Turn it off for 1248 Oakridge Drive?</h2><p>Round 2 keeps running until Dec 6. No more rounds are built and nothing more is charged.</p>
      <div class="modal-actions"><button class="nc-cancel" onclick="modal.close()">Keep it on</button><button class="campaign-primary" onclick="b10Off()">Turn off</button></div>`);
  };
  window.b10Off = function () { untilOn = false; modal.close(); myCredits(); toast('Turned off. No more charges for 1248 Oakridge Drive.'); };
  window.b10Close = function () {
    show(`<span class="eyebrow">CLOSE YOUR ACCOUNT</span><h2>This can't be undone.</h2>
      <p>Closing your account stops everything right away:</p>
      <ul class="until-sold-list"><li>Scheduled posts and the ads Resmara runs stop.</li><li>Run it until it sells turns off for every listing.</li><li>Your listing websites come down.</li><li>Your saved card is removed and Facebook is disconnected.</li><li>Your data is deleted within 30 days. Purchases are kept for tax records.</li></ul>
      <p><b>Nothing is refunded.</b> Posts and ads already published stay on your Page and ad account.</p>
      <label class="field">Type your email to confirm<input id="b10Email" type="email" placeholder="morgan@example.com"></label>
      <div class="modal-actions"><button class="nc-cancel" onclick="modal.close()">Keep my account</button><button class="campaign-primary" onclick="toast('Preview: the account would close now, and the Your account is closed email goes out.');modal.close()">Close my account</button></div>`);
  };

  // ---- Support ----
  window.supportPage = function () {
    $('#content').innerHTML = `<div class="welcome"><h1>Support.</h1></div>
      <div class="notice page-intro">We reply within <b>1 business day</b> (Monday to Friday, Pacific time). Most questions are answered faster by <b>Ask Resmara</b>, the chat in the corner.</div>
      <div class="grid2"><div class="panel"><span class="eyebrow">OPEN A REQUEST</span><h3>Tell us what you need.</h3><div id="s11Form">
        <label class="field">Which listing?<select id="s11Listing"><option>1248 Oakridge Drive</option><option>76 Willow Lane</option><option>Not about a listing</option></select></label>
        <label class="field">Subject<input id="s11Subject" maxlength="120" placeholder="e.g. Can I change the ad photo?"></label>
        <label class="field">Message<textarea rows="5" maxlength="4000" placeholder="What happened, and what did you expect instead?"></textarea></label>
        <button class="campaign-primary" onclick="s11Send()">Send request</button></div></div>
      <div class="panel"><span class="eyebrow">YOUR REQUESTS</span><h3>What we have from you.</h3><div class="s11-reqs">
        <article><div class="flex"><b>Setup session</b><span class="b10-tag">Upcoming</span></div><p class="fine" style="margin:6px 0 0">Tue, Nov 25 · 10:00 AM · Google Meet, 30 minutes</p>
          <div class="b10-btns" style="margin-top:10px"><button class="b10-mini" onclick="toast('Preview: opens the Google Meet link.')">Join</button><button class="b10-mini" onclick="toast('Preview: opens Calendly to reschedule.')">Reschedule</button></div></article>
        <article><div class="flex"><b>Instagram post didn't go out</b><span class="b10-tag org">Received</span></div><p class="fine" style="margin:6px 0 0">#1046 · 1248 Oakridge Drive · opened by Resmara today</p>
          <div class="s11-msg"><span>Resmara</span><p style="margin:2px 0 0">Your day 4 post couldn't publish to Instagram because the login expired. Reconnect in Accounts and we'll post it straight away.</p></div></article>
        <article><div class="flex"><b>Can I change the ad photo?</b><span class="b10-tag">Answered</span></div><p class="fine" style="margin:6px 0 0">#1041 · 1248 Oakridge Drive · Nov 20</p>
          <div class="s11-msg"><span>You</span><p style="margin:2px 0 0">The ad is using the front of the house. Can I use the kitchen instead?</p></div>
          <div class="s11-msg team"><span>Adam from Resmara</span><p style="margin:2px 0 0">Yes. Open the campaign, click the ad, then Swap photo and pick the kitchen. It updates the ad within the hour.</p></div></article>
        <article><div class="flex"><b>Report question</b><span class="b10-tag soft">Closed</span></div><p class="fine" style="margin:6px 0 0">#1032 · Nov 12 · closed 7 days after our answer. Reply any time to reopen it.</p></article>
      </div></div></div>`;
  };
  window.s11Send = function () {
    const box = document.getElementById('s11Form'); if (!box) return;
    box.insertAdjacentHTML('beforeend', `<div class="s11-sent"><b>Got it. We'll reply by Tuesday at 5 PM.</b><br>We've emailed you a copy. Request #1047.</div>`);
  };
  // The chat says it's an AI assistant in its first message.
  const first = document.querySelector('#pip-messages .pip-reply');
  if (first) first.textContent = 'Hi, I’m Ask Resmara, an AI assistant. I can answer most questions about Resmara and your account, and I’ll pass anything else to our team. What can I help with?';

  const h10 = window.__previewHash || location.hash;
  if (h10 === '#billing') setTimeout(() => { history.replaceState(null, '', location.pathname + '#billing'); state.clientSignedIn = true; dashboard('credits'); }, 90);
  if (h10 === '#support') setTimeout(() => { history.replaceState(null, '', location.pathname + '#support'); state.clientSignedIn = true; dashboard('support'); const p = document.querySelector('#pip-chat'); if (p) p.hidden = false; }, 90);
})();
