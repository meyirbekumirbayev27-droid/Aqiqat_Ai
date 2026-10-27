/* AQIQAT AI — ортақ интерфейс әрекеттері */
(function () {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.classList.toggle('reduced-motion', reduce);

  // ---------- Жұлдызды фон ----------
  const canvas = document.getElementById('stars');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let stars = [], w, h, dpr;
    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth; h = window.innerHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(260, Math.floor((w * h) / 6500));
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w, y: Math.random() * h,
        r: Math.random() * 1.2 + 0.2, a: Math.random() * 0.7 + 0.2,
        s: Math.random() * 0.015 + 0.003, p: Math.random() * Math.PI * 2,
        c: Math.random() < 0.15 ? '165,107,255' : Math.random() < 0.3 ? '85,231,255' : '245,247,255',
      }));
    };
    const draw = (t) => {
      ctx.clearRect(0, 0, w, h);
      for (const s of stars) {
        const tw = reduce ? s.a : s.a * (0.55 + 0.45 * Math.sin(t * s.s * 0.06 + s.p));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${s.c},${tw})`;
        ctx.fill();
      }
      if (!reduce) requestAnimationFrame(draw);
    };
    resize();
    window.addEventListener('resize', resize);
    requestAnimationFrame(draw);
  }

  // ---------- Мәзірлер ----------
  const burger = document.querySelector('.burger');
  if (burger) {
    burger.addEventListener('click', () => {
      const open = document.body.classList.toggle('nav-open');
      burger.setAttribute('aria-expanded', open);
    });
    document.querySelectorAll('.main-nav > a').forEach((a) =>
      a.addEventListener('click', () => document.body.classList.remove('nav-open')));
  }
  const closeAll = (except) => {
    document.querySelectorAll('.nav-drop.open, .user-menu.open').forEach((el) => {
      if (el !== except) {
        el.classList.remove('open');
        el.querySelector('button')?.setAttribute('aria-expanded', 'false');
      }
    });
  };
  document.querySelectorAll('.nav-drop, .user-menu').forEach((wrap) => {
    const btn = wrap.querySelector('button');
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeAll(wrap);
      const open = wrap.classList.toggle('open');
      btn.setAttribute('aria-expanded', open);
    });
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-drop, .user-menu')) closeAll();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closeAll(); document.body.classList.remove('nav-open'); }
  });

  // ---------- Пайда болу анимациясы ----------
  const reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduce) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add('in'));
  }

  // ---------- Флеш хабарламаларды жасыру ----------
  document.querySelectorAll('.flash').forEach((f, i) => setTimeout(() => {
    f.style.transition = 'opacity .4s, transform .4s';
    f.style.opacity = '0'; f.style.transform = 'translateY(-8px)';
    setTimeout(() => f.remove(), 450);
  }, 5000 + i * 600));

  // ---------- Құпиясөзді көрсету / күші ----------
  document.querySelectorAll('.pw-toggle').forEach((btn) => btn.addEventListener('click', () => {
    const input = btn.parentElement.querySelector('input');
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.setAttribute('aria-label', show ? 'Құпиясөзді жасыру' : 'Құпиясөзді көрсету');
  }));
  const pw = document.querySelector('#pw-meter');
  if (pw) {
    const input = document.getElementById('password');
    const hint = document.getElementById('pw-hint');
    input.addEventListener('input', () => {
      const v = input.value;
      let s = 0;
      if (v.length >= 8) s++;
      if (v.length >= 12) s++;
      if (/\d/.test(v) && /\p{L}/u.test(v)) s++;
      if (/[A-ZА-ЯӘҒҚҢӨҰҮҺІ]/.test(v) && /[a-zа-яәғқңөұүһі]/.test(v)) s++;
      if (/[^\p{L}\d]/u.test(v)) s++;
      const colors = ['#FF5C78', '#FF5C78', '#FFC857', '#FFC857', '#49E5B1', '#49E5B1'];
      const labels = ['Өте әлсіз', 'Әлсіз', 'Орташа', 'Жақсы', 'Күшті', 'Өте күшті'];
      pw.style.width = (v ? Math.max(10, s * 20) : 0) + '%';
      pw.style.background = colors[s];
      hint.textContent = v ? `Құпиясөз күші: ${labels[s]}` : 'Кемінде 8 таңба, әріп пен сан болуы керек.';
    });
  }

  // ---------- Мысалдар мен таңба санағышы ----------
  document.querySelectorAll('[data-count]').forEach((el) => {
    const input = document.getElementById(el.dataset.count);
    const max = input.getAttribute('maxlength');
    const upd = () => { el.textContent = `${input.value.length} / ${max}`; };
    input.addEventListener('input', upd);
    upd();
  });
  document.querySelectorAll('[data-fill]').forEach((btn) => btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.fill);
    input.value = btn.dataset.text;
    input.dispatchEvent(new Event('input'));
    input.focus();
  }));
})();
