/* AQIQAT AI — құралдар логикасы мен нәтижелерді көрсету */
window.AQ = (function () {
  const $ = (s, r = document) => r.querySelector(s);
  const csrf = () => document.querySelector('meta[name="csrf-token"]').content;
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(u || '') ? esc(u) : '#');

  async function api(url, body, isForm) {
    let res;
    try {
      res = await fetch(url, {
        method: 'POST',
        headers: isForm ? { 'X-CSRF-Token': csrf() } : { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
        body: isForm ? body : JSON.stringify(body || {}),
        credentials: 'same-origin',
      });
    } catch (e) {
      throw new Error('Серверге қосылу мүмкін болмады. Интернет байланысын тексеріңіз.');
    }
    let data = null;
    try { data = await res.json(); } catch (e) { /* JSON емес жауап */ }
    if (res.status === 401) { location.href = '/login?next=' + encodeURIComponent(location.pathname); throw new Error('Жүйеге кіру қажет.'); }
    if (!res.ok) throw new Error((data && data.error) || `Сервер қатесі (${res.status}).`);
    return data;
  }

  // ---------- Күйлер ----------
  function loading(el, title, sub) {
    const start = Date.now();
    el.innerHTML = `<div class="state-box scan-line"><span class="orb"></span><div><b>${esc(title)}</b><small>${esc(sub)} · <span class="elapsed">0</span> сек</small></div></div>`;
    const span = el.querySelector('.elapsed');
    const timer = setInterval(() => { span.textContent = Math.floor((Date.now() - start) / 1000); }, 1000);
    return () => clearInterval(timer);
  }
  function showError(el, msg) {
    el.innerHTML = `<div class="state-box error"><span style="font-size:26px">⚠️</span><div><b>Талдау орындалмады</b><small style="color:#ffc2cc">${esc(msg)}</small></div></div>`;
  }
  function setBusy(btn, busy) {
    if (!btn) return;
    btn.classList.toggle('loading', busy);
    btn.disabled = busy;
  }
  async function run(form, resultEl, opts) {
    const btn = form ? form.querySelector('button[type="submit"]') : opts.button;
    setBusy(btn, true);
    const stop = loading(resultEl, opts.title, opts.sub);
    try {
      const data = await opts.request();
      stop();
      resultEl.innerHTML = opts.render(data) + savedLink(data.history_id);
      opts.after && opts.after(data);
      resultEl.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
      animateGauges(resultEl);
    } catch (e) {
      stop();
      showError(resultEl, e.message);
    } finally {
      setBusy(btn, false);
    }
  }
  const savedLink = (id) => (id ? `<div class="note" style="border-style:solid">Нәтиже тарихқа сақталды. <a href="/history/${Number(id)}">Тарихта ашу →</a></div>` : '');

  // ---------- Визуал элементтер ----------
  const levelColor = (lvl) => ({ good: '#49E5B1', low: '#49E5B1', likely_true: '#49E5B1', medium: '#FFC857', insufficient: '#FFC857', bad: '#FF5C78', high: '#FF5C78', likely_false: '#FF5C78' }[lvl] || '#55E7FF');
  function gauge(value, label, lvl, text) {
    const r = 46, c = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(100, Number(value) || 0));
    return `<div class="gauge"><svg viewBox="0 0 112 112"><circle cx="56" cy="56" r="${r}" fill="none" stroke="rgba(140,170,255,.12)" stroke-width="9"/>
      <circle class="g-arc" cx="56" cy="56" r="${r}" fill="none" stroke="${levelColor(lvl)}" stroke-width="9" stroke-linecap="round"
        stroke-dasharray="${c}" stroke-dashoffset="${c}" data-target="${c * (1 - pct / 100)}" style="transition:stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1);filter:drop-shadow(0 0 6px ${levelColor(lvl)})"/></svg>
      <div class="g-val"><div>${text != null ? esc(text) : pct}<small>${esc(label)}</small></div></div></div>`;
  }
  function animateGauges(root) {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      root.querySelectorAll('.g-arc').forEach((a) => { a.style.strokeDashoffset = a.dataset.target; });
      root.querySelectorAll('.meter i[data-w]').forEach((m) => { m.style.width = m.dataset.w + '%'; });
    }));
  }
  function verdictBox(lvl, gaugeHtml, title, text) {
    return `<div class="verdict v-${esc(lvl)}">${gaugeHtml}<div><h4>${esc(title)}</h4><p>${esc(text)}</p></div></div>`;
  }
  const signalIcon = { good: '✓', bad: '!', warn: '!', info: 'i' };
  const signals = (list) => `<ul class="signal-list">${list.map((s) => `<li><span class="si ${esc(s.type)}">${signalIcon[s.type] || '•'}</span><span>${esc(s.text)}</span></li>`).join('')}</ul>`;
  const kv = (obj) => {
    const rows = Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && v !== '');
    return rows.length ? `<dl class="kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>` : '<p style="color:var(--muted)">Деректер табылмады.</p>';
  };
  const card = (title, body, full) => `<div class="res-card${full ? ' full' : ''}"><h5>${esc(title)}</h5>${body}</div>`;
  const note = (t) => (t ? `<div class="note">${esc(t)}</div>` : '');
  function highlight(text, spans, render) {
    let out = '', pos = 0;
    for (const s of spans) {
      if (s.start < pos) continue;
      out += esc(text.slice(pos, s.start)) + render(s, text.slice(s.start, s.end));
      pos = s.end;
    }
    return out + esc(text.slice(pos));
  }
  function evidenceList(items, used) {
    if (!items || !items.length) return '<p style="color:var(--muted);margin:0">Байланысты материалдар табылмады.</p>';
    return `<div class="evidence">${items.map((e, i) => `<a class="ev-item${used && used.includes(i) ? ' used' : ''}" href="${safeUrl(e.url)}" target="_blank" rel="noopener noreferrer">
      <b>${esc(e.title)}<em>${esc(e.source || '')}${used && used.includes(i) ? ' · AI қолданды' : ''}</em></b><p>${esc(e.snippet || '')}</p></a>`).join('')}</div>`;
  }
  function copyBtn(id, label) {
    return `<button type="button" class="btn btn-ghost btn-sm" onclick="AQ.copy('${id}', this)">${esc(label || 'Көшіру')}</button>`;
  }
  async function copy(id, btn) {
    const el = document.getElementById(id);
    try {
      await navigator.clipboard.writeText(el.innerText);
      const old = btn.textContent; btn.textContent = 'Көшірілді ✓';
      setTimeout(() => { btn.textContent = old; }, 1600);
    } catch (e) { btn.textContent = 'Көшіру мүмкін болмады'; }
  }

  // ---------- 1. Ақпаратты тексеру ----------
  function renderFactcheck(r) {
    const conf = r.verdict === 'insufficient' ? null : r.confidence;
    let html = verdictBox(r.verdict, gauge(conf ?? 0, conf == null ? 'дәлел аз' : 'сенімділік', r.verdict, conf == null ? '?' : `${conf}%`), r.verdict_label, r.summary);
    html += '<div class="res-grid">';
    const basis = r.basis.map((b) => ({ type: 'info', text: b }));
    const flagSignals = r.flags.map((f) => ({ type: 'bad', text: `${f.text} («${f.match}»)` }));
    if (r.attributed) flagSignals.push({ type: 'good', text: 'Мәтінде дереккөзге сілтеме немесе атрибуция бар.' });
    else flagSignals.push({ type: 'warn', text: 'Мәтінде дереккөз көрсетілмеген.' });
    flagSignals.push({ type: r.manipulation.level === 'low' ? 'good' : 'warn', text: `Манипуляциялық тіл: ${r.manipulation.label} (${r.manipulation.count} белгі).` });
    html += card('Тұжырым негізі', signals(basis.concat(flagSignals)));
    let aiHtml;
    if (r.ai) {
      const label = { likely_true: 'Шынайы болуы мүмкін', likely_false: 'Жалған болуы мүмкін', insufficient: 'Дәлел жеткіліксіз' }[r.ai.verdict];
      aiHtml = `<p><span class="badge ${esc(r.ai.verdict)}">${esc(label)}</span> <span class="badge info">модель сенімділігі ${Number(r.ai.confidence)}%</span></p>`;
      aiHtml += r.ai.explanation ? `<p>${esc(r.ai.explanation)}</p>` : `<p style="color:var(--muted)">Модель (${esc(r.ai.model)}) табылған дереккөз үзінділерін мәлімдемемен салыстырды${r.ai.used.length ? `: ${r.ai.used.length} материал ескерілді (төменде белгіленген)` : ''}.</p>`;
      aiHtml += r.ai.local
        ? '<p style="color:var(--dim);font-size:13px;margin:0">Бұл — жергілікті шағын модельдің пікірі. Ол жиі қателесетіндіктен, қорытынды тұжырымға әсер етпейді. Дәлірек талдау үшін серверге тегін Gemini API кілтін қосыңыз.</p>'
        : '<p style="color:var(--dim);font-size:13px;margin:0">AI түсіндірмесі — тексерілмеген пікір. Сыртқы дереккөздермен салыстырыңыз.</p>';
    } else if (r.ai_status && r.ai_status.provider) {
      aiHtml = '<p style="color:var(--muted)">AI қызметі қазір жауап бермеді (тегін нұсқада 30 секундта бір сұрау шектеуі бар). Тұжырым белгілер мен дереккөздерге негізделді — жарты минуттан кейін қайталап көріңіз.</p>';
    } else {
      aiHtml = '<p style="color:var(--muted)">AI моделі қосылмаған. Тұжырым тек мәтін белгілері мен табылған дереккөздерге негізделді.</p>';
    }
    html += card('AI түсіндірмесі', aiHtml);
    html += card(`Сыртқы дереккөздерден табылған материалдар${r.keywords.length ? ' · іздеу: ' + r.keywords.join(', ') : ''}`, evidenceList(r.evidence, r.ai && r.ai.used), true);
    html += card('Әрі қарай қалай тексеру керек', `<ul class="tips">${r.tips.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`, true);
    html += '</div>' + note(r.note);
    return html;
  }
  function initFactcheck() {
    const form = $('#fc-form');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = $('#fc-text').value.trim();
      const out = $('#fc-result');
      if (text.length < 15) return showError(out, 'Мәлімдемені толығырақ жазыңыз (кемінде 15 таңба).');
      run(form, out, {
        title: 'Ақпарат талдануда…',
        sub: 'Мәтін белгілері, Wikipedia іздеуі және AI салыстыруы орындалуда',
        request: () => api('/api/factcheck', { text }),
        render: renderFactcheck,
      });
    });
  }

  // ---------- 2. Дереккөз ----------
  function renderSource(r) {
    let html = verdictBox(r.level, gauge(r.score, 'белгілер', r.level), r.label, `${r.host} · HTTP ${r.http_status}`);
    html += '<div class="res-grid">';
    html += card('Бет туралы мәлімет', kv({
      'Тақырыбы': r.title, 'Сайт атауы': r.site_name, 'Автор': r.author || 'көрсетілмеген',
      'Жарияланған': r.published || 'табылмады', 'Жаңартылған': r.modified, 'Мазмұн түрі': r.content_type,
      'Сөз саны': r.word_count, 'Соңғы URL': r.url !== r.requested_url ? r.url : null,
    }));
    const rd = r.rdap;
    html += card('Домен тізілімі (RDAP)', rd ? kv({
      'Домен': r.domain, 'Тіркелген': rd.registered ? rd.registered.slice(0, 10) : null,
      'Жасы': r.age_days != null ? `${Math.floor(r.age_days / 365.25)} жыл ${Math.floor((r.age_days % 365.25) / 30)} ай` : null,
      'Мерзімі бітеді': rd.expires ? rd.expires.slice(0, 10) : null, 'Тіркеуші': rd.registrar,
    }) + `<p style="margin:10px 0 0;font-size:12.5px"><a href="${safeUrl(rd.rdap_url)}" target="_blank" rel="noopener">RDAP жазбасын ашу →</a></p>`
      : `<p style="color:var(--muted);margin:0">«${esc(r.domain)}» үшін ашық тіркеу деректері қолжетімсіз. Бұл аймақтың тізілімі RDAP қызметін ұсынбауы мүмкін.</p>`);
    html += card('Сенімділік белгілері', signals(r.signals), true);
    if (r.description) html += card('Беттің сипаттамасы', `<p>${esc(r.description)}</p>`);
    if (r.external_domains.length) html += card('Сілтеме жасалған домендер', `<p class="mono">${r.external_domains.map(esc).join(' · ')}</p>`);
    html += card('Байланысты материалдар', evidenceList(r.related) +
      `<div class="copy-row">${r.search_links.map((l) => `<a class="btn btn-ghost btn-sm" href="${safeUrl(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join('')}</div>`, true);
    html += '</div>' + note(r.note);
    return html;
  }
  function initSource() {
    const form = $('#src-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const url = $('#src-url').value.trim();
      const out = $('#src-result');
      if (!url) return showError(out, 'Сайт немесе мақала сілтемесін енгізіңіз.');
      run(form, out, {
        title: 'Дереккөз талдануда…', sub: 'Бет жүктелуде, домен тізілімі мен энциклопедия сұралуда',
        request: () => api('/api/source', { url, text: $('#src-text').value.trim() }),
        render: renderSource,
      });
    });
  }

  // ---------- 3. Медиа ----------
  function renderMedia(r, previewUrl) {
    let html = verdictBox(r.level, gauge(r.level === 'low' ? 85 : r.level === 'medium' ? 50 : 20, 'таза', r.level, { low: '✓', medium: '!', high: '!!' }[r.level]), r.label, r.filename);
    html += '<div class="res-grid">';
    html += card('Файл туралы', kv(r.info));
    html += card('Метадеректер', kv(r.metadata));
    html += card('Табылған белгілер', signals(r.findings), true);
    if (r.ela) {
      const metrics = `<p style="font-size:13.5px;color:var(--muted);margin:10px 0 0">Ең үлкен айырмашылық: ${r.ela.max_diff} · орташа: ${r.ela.mean} · айқын аймақтар: ${r.ela.bright_ratio}%</p>`;
      if (r.ela.image) {
        html += card('ELA — қысу деңгейінің картасы', `<div class="ela-wrap">
          ${previewUrl ? `<figure><img src="${previewUrl}" alt="Түпнұсқа"><figcaption>Түпнұсқа</figcaption></figure>` : ''}
          <figure><img src="${r.ela.image}" alt="ELA картасы"><figcaption>ELA: ашық аймақтар қайта сығуға басқаша жауап береді</figcaption></figure></div>${metrics}
          <p style="font-size:13px;color:var(--dim);margin:8px 0 0">Біркелкі жарық жиектер мен мәтін — қалыпты құбылыс. Тек жеке объектінің айналасында ерекше жарқыраған аймақ күдік тудыруы мүмкін.</p>`, true);
      } else {
        html += card('ELA көрсеткіштері', metrics, true);
      }
    }
    html += card('Түпнұсқаны іздеу', `<p>Автоматты кері іздеу қызметі қосылмаған. Файлды төмендегі қызметтерге өзіңіз жүктеп, бұрын жарияланған-жарияланбағанын тексеріңіз:</p>
      <div class="copy-row">${r.reverse_search.map((l) => `<a class="btn btn-ghost btn-sm" href="${safeUrl(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join('')}</div>
      <p class="mono" style="margin-top:14px">SHA-256: ${esc(r.sha256)}</p>`, true);
    html += '</div>' + note(r.note);
    return html;
  }
  function initMedia() {
    const form = $('#media-form'), input = $('#media-file'), dz = $('#dropzone'), pv = $('#preview');
    const out = $('#media-result');
    let file = null, url = null;
    const IMG = ['jpg', 'jpeg', 'png', 'webp', 'gif'], VID = ['mp4', 'mov', 'webm', 'm4v'];
    const setFile = (f) => {
      if (!f) return;
      const ext = (f.name.split('.').pop() || '').toLowerCase();
      if (!IMG.includes(ext) && !VID.includes(ext)) return showError(out, 'Бұл формат қолдау көрсетілмейді. Рұқсат етілген: JPG, PNG, WEBP, GIF, MP4, MOV, WEBM.');
      if (IMG.includes(ext) && f.size > 15 * 1024 * 1024) return showError(out, 'Сурет 15 МБ-тан аспауы керек.');
      if (VID.includes(ext) && f.size > 60 * 1024 * 1024) return showError(out, 'Видео 60 МБ-тан аспауы керек.');
      file = f;
      if (url) URL.revokeObjectURL(url);
      url = URL.createObjectURL(f);
      $('#pv-media').innerHTML = IMG.includes(ext) ? `<img src="${url}" alt="Алдын ала қарау">` : `<video src="${url}" muted playsinline controls></video>`;
      $('#pv-name').textContent = f.name;
      $('#pv-meta').textContent = `${(f.size / 1024 / 1024).toFixed(2)} МБ · ${IMG.includes(ext) ? 'Сурет' : 'Видео'}`;
      pv.classList.add('show');
      dz.style.display = 'none';
      out.innerHTML = '';
    };
    input.addEventListener('change', () => setFile(input.files[0]));
    ['dragenter', 'dragover'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove('drag'); }));
    dz.addEventListener('drop', (e) => setFile(e.dataTransfer.files[0]));
    $('#pv-clear').addEventListener('click', () => {
      file = null; input.value = ''; pv.classList.remove('show'); dz.style.display = ''; out.innerHTML = '';
    });
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!file) return showError(out, 'Алдымен файл таңдаңыз.');
      const fd = new FormData();
      fd.append('file', file);
      pv.classList.add('scanning');
      run(form, out, {
        title: 'Медиа талдануда…', sub: 'Файл серверге жүктеліп, метадеректер мен қысу деңгейі тексерілуде',
        request: () => api('/api/media', fd, true).finally(() => pv.classList.remove('scanning')),
        render: (r) => renderMedia(r, file && file.type.startsWith('image/') ? url : null),
      });
    });
  }

  // ---------- 4. Алаяқтық ----------
  function renderScam(r) {
    let html = verdictBox(r.level, gauge(r.score, 'тәуекел', r.level), `Тәуекел деңгейі: ${r.label}`, r.summary);
    html += '<div class="res-grid">';
    if (r.input) {
      html += card('Белгіленген мәтін', `<div class="highlighted">${highlight(r.input, r.hits, (s, t) => `<mark class="m-${esc(s.category)}" title="${esc(s.label)}">${esc(t)}</mark>`)}</div>`, true);
    }
    const sig = r.signals.length ? `<div class="cat-list">${r.signals.map((s) => `<div class="cat-item"><b>${esc(s.label)} <span class="badge high">${s.count}</span></b><p>${esc(s.why)}</p><div class="advice">${esc(s.advice)}</div></div>`).join('')}</div>`
      : '<p style="color:var(--muted);margin:0">Алаяқтыққа тән белгілер табылмады.</p>';
    html += card('Анықталған белгілер', sig);
    const urls = r.urls.length ? r.urls.map((u) => `<div class="cat-item" style="margin-bottom:10px"><b><span class="mono" style="color:var(--text)">${esc(u.host || u.url)}</span><span class="badge ${u.flags.length ? (u.score >= 30 ? 'high' : 'medium') : 'low'}">${u.flags.length ? u.flags.length + ' белгі' : 'таза'}</span></b>
      ${u.flags.length ? `<ul class="tips" style="margin-top:8px">${u.flags.map((f) => `<li>${esc(f)}</li>`).join('')}</ul>` : `<p>Сілтеме құрылымында айқын қауіп белгілері жоқ${u.age_days != null ? ` · домен жасы ${Math.floor(u.age_days / 365)} жыл` : ''}.</p>`}</div>`).join('')
      : '<p style="color:var(--muted);margin:0">Хабарламада сілтеме табылмады.</p>';
    html += card('Сілтемелерді талдау', urls);
    html += card('Қауіпсіздік кеңестері', `<ul class="tips">${r.advice.map((a) => `<li>${esc(a)}</li>`).join('')}</ul>`, true);
    html += '</div>' + note(r.note);
    return html;
  }
  function initScam() {
    const form = $('#scam-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = $('#scam-text').value.trim(), url = $('#scam-url').value.trim();
      const out = $('#scam-result');
      if (text.length < 5 && !url) return showError(out, 'Хабарлама мәтінін немесе сілтемені енгізіңіз.');
      run(form, out, {
        title: 'Хабарлама тексерілуде…', sub: 'Алаяқтық үлгілері мен сілтеме домендері талдануда',
        request: () => api('/api/scam', { text, url }),
        render: renderScam,
      });
    });
  }

  // ---------- 5. Манипуляция ----------
  function renderManipulation(r) {
    let html = verdictBox(r.level, gauge(r.intensity, 'қарқын', r.level), r.label, `${r.flags.length} белгі · ${r.word_count} сөз`);
    html += '<div class="res-grid">';
    if (r.input) {
      const legend = r.categories.map((c) => `<span class="m-${esc(c.key)}" style="display:inline-block"><mark class="m-${esc(c.key)}">${esc(c.label)}</mark></span>`).join('');
      html += card('Белгіленген фрагменттер', `<div class="legend">${legend}</div><div class="highlighted">${highlight(r.input, r.flags, (s, t) => `<mark class="m-${esc(s.category)}" title="${esc(s.label)}">${esc(t)}</mark>`)}</div>`, true);
    }
    html += card('Неге анықталды', r.categories.length ? `<div class="cat-list">${r.categories.map((c) => `<div class="cat-item"><b>${esc(c.label)} <span class="badge medium">${c.count}</span></b><p>${esc(c.why)}</p></div>`).join('')}</div>`
      : '<p style="color:var(--muted);margin:0">Мәтін бейтарап көрінеді: манипуляциялық тәсілдер табылмады.</p>');
    if (r.flags.length) {
      html += card('Бейтарап балама тұжырым', `<div class="highlighted" id="neutral-text">${esc(r.neutral)}</div><div class="copy-row">${copyBtn('neutral-text', 'Бейтарап нұсқаны көшіру')}</div>
        <p style="font-size:12.5px;color:var(--dim);margin:10px 0 0">Автоматты ұсыныс: бояуы күшті сөздер бейтарап баламалармен ауыстырылды не алынып тасталды. Мағынасын өзіңіз тексеріңіз.</p>`);
    }
    html += '</div>' + note(r.note);
    return html;
  }
  function initManipulation() {
    const form = $('#man-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = $('#man-text').value.trim();
      const out = $('#man-result');
      if (text.length < 20) return showError(out, 'Талдау үшін кемінде 20 таңба енгізіңіз.');
      run(form, out, {
        title: 'Мәтін талдануда…', sub: 'Эмоциялық, қорқыту және біржақты тәсілдер ізделуде',
        request: () => api('/api/manipulation', { text }),
        render: renderManipulation,
      });
    });
  }

  // ---------- 6. Жеке деректер ----------
  function renderPrivacy(r, text) {
    let html = verdictBox(r.level, gauge(r.level === 'low' ? 100 : r.level === 'medium' ? 55 : 15, 'қауіпсіздік', r.level, r.total), r.label,
      r.total ? `${r.total} құпия фрагмент табылды. Жарияламас бұрын оларды өшіріңіз немесе бүркемелеңіз.` : 'Мәтінде жеке немесе құпия деректер үлгілері табылмады.');
    html += '<div class="res-grid">';
    if (text && r.items) {
      html += card('Табылған фрагменттер (бүркемеленген)', `<div class="highlighted">${highlight(text, r.items, (s) => `<mark class="m-${esc(s.risk)}" title="${esc(s.label)}">${esc(s.masked)}</mark>`)}</div>`, true);
    }
    html += card('Тәуекел түсіндірмесі', r.groups.length ? `<div class="cat-list">${r.groups.map((g) => `<div class="cat-item"><b>${esc(g.label)} <span class="badge ${esc(g.risk)}">${g.count} · ${g.risk === 'high' ? 'жоғары' : 'орташа'}</span></b><p>${esc(g.why)}</p></div>`).join('')}</div>`
      : '<p style="color:var(--muted);margin:0">Тәуекелдер анықталмады.</p>', !r.redacted);
    if (r.redacted && r.total) {
      html += card('Жариялауға қауіпсіз нұсқа', `<div class="highlighted" id="clean-text">${esc(r.redacted)}</div>
        <div class="copy-row">${copyBtn('clean-text', 'Тазартылған мәтінді көшіру')}<button type="button" class="btn btn-primary btn-sm" onclick="AQ.applyClean()">Мәтінді тазарту</button></div>`);
    }
    html += '</div>' + note(r.note);
    return html;
  }
  let lastClean = null;
  function initPrivacy() {
    const form = $('#pv-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = $('#pv-text').value;
      const out = $('#pv-result');
      if (text.trim().length < 5) return showError(out, 'Тексеру үшін мәтін енгізіңіз.');
      run(form, out, {
        title: 'Мәтін тексерілуде…', sub: 'Телефон, ЖСН, карта, құпиясөз және кілт үлгілері ізделуде',
        request: () => api('/api/privacy', { text }),
        render: (r) => { lastClean = r.redacted; return renderPrivacy(r, text.trim()); },
      });
    });
  }
  function applyClean() {
    if (lastClean == null) return;
    const ta = $('#pv-text');
    ta.value = lastClean;
    ta.dispatchEvent(new Event('input'));
    ta.focus();
    ta.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // ---------- Ойын ----------
  function initQuiz() {
    const intro = $('#q-intro'), play = $('#q-play'), end = $('#q-end'), qcard = $('#q-card');
    const fb = $('#q-feedback'), answers = [...document.querySelectorAll('.ans')];
    let current = null;

    const toast = (a) => {
      const t = document.createElement('div');
      t.className = 'toast-ach';
      t.innerHTML = `<span class="a-ic">${esc(a.icon)}</span><div><small style="color:var(--green)">Жаңа жетістік!</small><br><b>${esc(a.title)}</b></div>`;
      document.body.appendChild(t);
      setTimeout(() => { t.style.transition = 'opacity .4s'; t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 3200);
    };
    const unlock = (list) => list.forEach((a, i) => {
      const el = document.querySelector(`.ach[data-ach="${a.key}"]`);
      if (el) el.classList.add('on');
      setTimeout(() => toast(a), i * 700);
    });
    const show = (q, levelName) => {
      current = q;
      $('#q-num').textContent = `Сұрақ ${q.number} / ${q.total}`;
      $('#q-cat').textContent = q.category;
      $('#q-claim').textContent = q.claim;
      $('#q-level').textContent = levelName;
      $('#q-progress').style.width = `${((q.number - 1) / q.total) * 100}%`;
      fb.innerHTML = '';
      answers.forEach((b) => { b.disabled = false; b.classList.remove('right', 'wrong', 'picked'); });
      play.classList.remove('enter'); void play.offsetWidth; play.classList.add('enter');
      qcard.classList.remove('enter'); void qcard.offsetWidth; qcard.classList.add('enter');
      window.dispatchEvent(new CustomEvent('aq:quiz', { detail: 'next' }));
    };
    const loadLeaders = async () => {
      try {
        const res = await fetch('/api/quiz/leaderboard', { credentials: 'same-origin' });
        const rows = await res.json();
        $('#leader').innerHTML = rows.length ? rows.map((r) => `<li><span>${esc(r.name)}</span><b>${Number(r.score)}</b></li>`).join('') : '<li><span>Әзірге нәтиже жоқ — бірінші болыңыз!</span></li>';
      } catch (e) { $('#leader').innerHTML = '<li><span>Жүктеу мүмкін болмады.</span></li>'; }
    };
    const start = async (btn) => {
      setBusy(btn, true);
      try {
        const d = await api('/api/quiz/start');
        intro.hidden = true; end.hidden = true; play.hidden = false;
        $('#q-score').textContent = '0'; $('#q-streak').textContent = '0';
        document.querySelectorAll('.ach').forEach((a) => a.classList.remove('on'));
        show(d.question, d.level_name);
      } catch (e) {
        fb.innerHTML = ''; alert(e.message);
      } finally { setBusy(btn, false); }
    };
    $('#q-start').addEventListener('click', (e) => start(e.currentTarget));
    answers.forEach((b) => b.addEventListener('click', async () => {
      if (!current) return;
      answers.forEach((x) => { x.disabled = true; });
      b.classList.add('picked');
      let d;
      try {
        d = await api('/api/quiz/answer', { id: current.id, answer: b.dataset.answer });
      } catch (e) {
        fb.innerHTML = `<div class="feedback no"><p>${esc(e.message)}</p></div>`;
        answers.forEach((x) => { x.disabled = false; });
        return;
      }
      answers.forEach((x) => { if (x.dataset.answer === d.right_answer) x.classList.add('right'); });
      if (!d.correct) b.classList.add('wrong');
      window.dispatchEvent(new CustomEvent('aq:quiz', { detail: d.correct ? 'right' : 'wrong' }));
      $('#q-score').textContent = d.score;
      $('#q-streak').textContent = d.streak;
      $('#q-progress').style.width = `${(d.answered / current.total) * 100}%`;
      const src = d.sources.length ? `<div class="src">Дереккөз: ${d.sources.map((s) => `<a href="${safeUrl(s.url)}" target="_blank" rel="noopener">${esc(s.title)} ↗</a>`).join(' · ')}</div>` : '<div class="src" style="color:var(--muted);font-size:13px">Тексерілетін дереккөз жоқ — дәл осы сабақтың мәні.</div>';
      fb.innerHTML = `<div class="feedback ${d.correct ? 'ok' : 'no'}"><h4>${d.correct ? `Дұрыс! +${d.gained} ұпай` : `Қате. Дұрыс жауап: «${esc(d.right_label)}»`}</h4><p>${esc(d.explain)}</p>${src}
        <div class="copy-row" style="margin-top:14px"><button type="button" class="btn btn-primary btn-sm" id="q-next">${d.finished ? 'Нәтижені көру' : 'Келесі сұрақ →'}</button></div></div>`;
      unlock(d.new_achievements || []);
      $('#q-next').focus({ preventScroll: true });
      $('#q-next').addEventListener('click', () => {
        if (!d.finished) return show(d.next, d.level_name);
        const s = d.summary;
        const best = Math.max(Number($('#q-best').textContent) || 0, s.score);
        $('#q-best').textContent = best;
        play.hidden = true; end.hidden = false; current = null;
        const pct = Math.round((s.correct / s.total) * 100);
        end.innerHTML = `<div style="font-size:54px">${pct >= 80 ? '🏆' : pct >= 50 ? '⭐' : '📚'}</div>
          <p class="q-claim" style="margin-bottom:8px">${s.score} ұпай</p>
          <p style="color:var(--muted);margin:0 0 6px">${s.correct} / ${s.total} дұрыс жауап · ең ұзын серия: ${s.best_streak}</p>
          <p style="margin:0 0 24px">${pct >= 80 ? 'Керемет! Сіз — нағыз фактчекер.' : pct >= 50 ? 'Жақсы нәтиже! Түсіндірмелерді оқып, тағы байқап көріңіз.' : 'Білім орталығындағы кеңестерді оқып, қайта ойнап көріңіз.'}</p>
          <div class="copy-row" style="justify-content:center"><button type="button" class="btn btn-primary" id="q-restart"><span class="spinner"></span><span class="btn-icon">↻</span> Қайта ойнау</button><a href="/learn" class="btn btn-ghost">Білім орталығы</a></div>`;
        $('#q-restart').addEventListener('click', (e) => start(e.currentTarget));
        loadLeaders();
      });
    }));
    loadLeaders();
  }

  // ---------- Тарихтан көрсету ----------
  function renderHistory(tool, r) {
    const el = $('#hist-result');
    const map = { factcheck: renderFactcheck, source: renderSource, media: (x) => renderMedia(x, null), scam: renderScam, manipulation: renderManipulation, privacy: (x) => renderPrivacy(x, null) };
    try {
      el.innerHTML = (r.input && tool === 'factcheck' ? card('Тексерілген мәтін', `<p>${esc(r.input)}</p>`, true).replace('res-card', 'res-card" style="margin-bottom:16px') : '') + (map[tool] ? map[tool](r) : '');
      animateGauges(el);
    } catch (e) {
      showError(el, 'Бұл жазбаны көрсету мүмкін болмады.');
    }
  }

  return { initFactcheck, initSource, initMedia, initScam, initManipulation, initPrivacy, initQuiz, renderHistory, copy, applyClean };
})();
