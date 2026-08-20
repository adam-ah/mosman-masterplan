(function () {
  var IDX = window.IDX;
  if (!IDX) return;
  var V = IDX.V, P = IDX.P, TK = IDX.TK, TG = IDX.TG, T = IDX.T, M = IDX.M, S = IDX.S;
  var ROOT = location.pathname.indexOf('/sections/') > -1 ? '../' : '';
  var NDOC = T.length;
  var postCache = {}, triCache = {};
  var KEY = 'mmp.query', SIDE = 'mmp.side';

  function b36(s) { return parseInt(s, 36); }

  function posting(i) {
    var c = postCache[i];
    if (c) return c;
    var raw = P[i], out = [], prev = 0;
    if (raw.length) {
      var parts = raw.split(',');
      for (var k = 0; k < parts.length; k++) {
        var p = parts[k], dot = p.indexOf('.'), f = 1, d;
        if (dot > -1) { d = b36(p.slice(0, dot)); f = b36(p.slice(dot + 1)); }
        else d = b36(p);
        prev += d;
        out.push(prev, f);
      }
    }
    postCache[i] = out;
    return out;
  }

  function trigram(g) {
    var hit = triCache[g];
    if (hit !== undefined) return hit;
    var lo = 0, hi = TK.length - 1, at = -1;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (TK[mid] === g) { at = mid; break; }
      TK[mid] < g ? (lo = mid + 1) : (hi = mid - 1);
    }
    var out = [];
    if (at > -1) {
      var parts = TG[at].split(','), prev = 0;
      for (var k = 0; k < parts.length; k++) { prev += b36(parts[k]); out.push(prev); }
    }
    triCache[g] = out;
    return out;
  }

  function lowerBound(w) {
    var lo = 0, hi = V.length;
    while (lo < hi) { var mid = (lo + hi) >> 1; V[mid] < w ? (lo = mid + 1) : (hi = mid); }
    return lo;
  }

  function exact(w) { var i = lowerBound(w); return (i < V.length && V[i] === w) ? i : -1; }

  function prefixes(w, cap) {
    var i = lowerBound(w), out = [];
    while (i < V.length && V[i].lastIndexOf(w, 0) === 0 && out.length < cap) { out.push(i); i++; }
    return out;
  }

  function editWithin(a, b, max) {
    var la = a.length, lb = b.length;
    if (Math.abs(la - lb) > max) return max + 1;
    var prev = new Array(lb + 1), cur = new Array(lb + 1), i, j;
    for (j = 0; j <= lb; j++) prev[j] = j;
    for (i = 1; i <= la; i++) {
      cur[0] = i;
      var best = cur[0];
      for (j = 1; j <= lb; j++) {
        var cost = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
        if (cur[j] < best) best = cur[j];
      }
      if (best > max) return max + 1;
      var t = prev; prev = cur; cur = t;
    }
    return prev[lb];
  }

  function fuzzy(w, cap) {
    var max = w.length >= 8 ? 2 : w.length >= 4 ? 1 : 0;
    if (!max) return [];
    var padded = '$' + w + '$', counts = {}, k, list, n;
    for (k = 0; k < padded.length - 2; k++) {
      list = trigram(padded.slice(k, k + 3));
      for (n = 0; n < list.length; n++) counts[list[n]] = (counts[list[n]] || 0) + 1;
    }
    var cand = [];
    for (var key in counts) if (counts[key] >= 2) cand.push([counts[key], +key]);
    cand.sort(function (a, b) { return b[0] - a[0]; });
    var out = [];
    for (k = 0; k < cand.length && k < 400 && out.length < cap; k++) {
      var vi = cand[k][1], d = editWithin(w, V[vi], max);
      if (d <= max) out.push([vi, d]);
    }
    return out;
  }

  function termsOf(qs) {
    return (qs.toLowerCase().match(/[a-z0-9][a-z0-9'&/-]*/g) || [])
      .filter(function (t) { return t.length > 1; });
  }

  function search(qs) {
    var terms = termsOf(qs);
    if (!terms.length) return [];
    var scores = new Float64Array(NDOC), hits = new Uint8Array(NDOC);
    for (var ti = 0; ti < terms.length; ti++) {
      var w = terms[ti], variants = [];
      var e = exact(w);
      if (e > -1) variants.push([e, 1.0]);
      var pf = prefixes(w, 40);
      for (var a = 0; a < pf.length; a++) if (pf[a] !== e) variants.push([pf[a], 0.62]);
      if (variants.length < 3) {
        var fz = fuzzy(w, 12);
        for (var b = 0; b < fz.length; b++) if (fz[b][0] !== e) variants.push([fz[b][0], fz[b][1] === 1 ? 0.45 : 0.3]);
      }
      var touched = {};
      for (var vI = 0; vI < variants.length; vI++) {
        var vi = variants[vI][0], wt = variants[vI][1], pl = posting(vi);
        var idf = Math.log(1 + NDOC / (1 + pl.length / 2));
        for (var p = 0; p < pl.length; p += 2) {
          var d = pl[p], f = pl[p + 1];
          var sc = wt * idf * (1 + Math.log(f));
          if (sc > (touched[d] || 0)) { scores[d] += sc - (touched[d] || 0); touched[d] = sc; }
        }
      }
      for (var dk in touched) hits[dk] += 1;
    }
    var res = [], phrase = terms.length > 1 ? qs.toLowerCase().replace(/\s+/g, ' ').trim() : null;
    for (var d2 = 0; d2 < NDOC; d2++) {
      if (!scores[d2]) continue;
      var cov = hits[d2] / terms.length;
      if (cov < 0.5 && terms.length > 1) continue;
      var sc2 = scores[d2] * Math.pow(cov, 2.2);
      if (phrase && T[d2].toLowerCase().indexOf(phrase) > -1) sc2 *= 3.5;
      res.push([sc2, d2]);
    }
    res.sort(function (x, y) { return y[0] - x[0]; });
    return res.slice(0, 200);
  }

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function snippet(text, terms) {
    var low = text.toLowerCase(), at = -1;
    for (var i = 0; i < terms.length; i++) {
      var k = low.indexOf(terms[i]);
      if (k > -1 && (at === -1 || k < at)) at = k;
    }
    if (at === -1) at = 0;
    var start = Math.max(0, at - 70), end = Math.min(text.length, start + 210);
    var s = esc(text.slice(start, end));
    var uniq = terms.slice().sort(function (a, b) { return b.length - a.length; });
    for (var j = 0; j < uniq.length; j++) {
      if (uniq[j].length < 2) continue;
      var pat = uniq[j].replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      s = s.replace(new RegExp('(' + pat + ')', 'gi'), '$1');
    }
    s = s.replace(//g, '<mark>').replace(//g, '</mark>');
    return (start > 0 ? '…' : '') + s + (end < text.length ? '…' : '');
  }

  var q = document.getElementById('q');
  var box = document.getElementById('results');
  var side = document.getElementById('side');
  var toggle = document.getElementById('toggle');
  var qclear = document.getElementById('qclear');
  var hint = document.getElementById('hint');
  var secnav = document.getElementById('secnav');
  if (!q || !box) return;

  var curList = [], curTerms = [];
  var here = { file: location.pathname.split('/').pop(), page: null };
  if (location.hash.indexOf('#p') === 0) here.page = parseInt(location.hash.slice(2), 10);

  function hrefFor(d) {
    var m = M[d];
    return ROOT + S[m[0]].f + '#p' + m[1];
  }

  function render(list, terms) {
    curList = list; curTerms = terms;
    if (!list.length) {
      box.innerHTML = '<div class="empty">No matches</div>';
      document.body.classList.add('searching');
      return;
    }
    var h = '<div class="rcount">' + list.length + (list.length === 200 ? '+' : '') + ' hits</div>';
    for (var i = 0; i < list.length; i++) {
      var d = list[i][1], m = M[d], sec = S[m[0]];
      var active = (sec.f.split('/').pop() === here.file && m[1] === here.page) ? ' on' : '';
      h += '<a class="r' + active + '" href="' + hrefFor(d) + '" data-i="' + i + '">'
        + '<span class="rh"><b>' + esc(sec.l || '—') + '</b> ' + esc(sec.t)
        + '<i>p.' + m[1] + '</i></span>'
        + '<span class="rs">' + snippet(T[d], terms) + '</span></a>';
    }
    box.innerHTML = h;
    document.body.classList.add('searching');
    var on = box.querySelector('.r.on');
    if (on) on.scrollIntoView({ block: 'center' });
  }

  function clearResults() {
    box.innerHTML = '';
    curList = [];
    document.body.classList.remove('searching');
    try { sessionStorage.removeItem(KEY); } catch (e) {}
  }

  function run(store) {
    var val = q.value.trim();
    if (val.length < 2) { clearResults(); return; }
    var t0 = performance.now();
    var res = search(val);
    render(res, termsOf(val));
    var rc = box.querySelector('.rcount');
    if (rc) rc.textContent += '  ·  ' + (performance.now() - t0).toFixed(0) + ' ms';
    if (store !== false) { try { sessionStorage.setItem(KEY, val); } catch (e) {} }
  }

  var timer;
  q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 70); });
  if (qclear) qclear.addEventListener('click', function () { q.value = ''; clearResults(); q.focus(); });

  function markActive() {
    here.file = location.pathname.split('/').pop();
    here.page = location.hash.indexOf('#p') === 0 ? parseInt(location.hash.slice(2), 10) : null;
    var items = box.querySelectorAll('.r'), found = null;
    for (var i = 0; i < items.length; i++) {
      var d = curList[+items[i].getAttribute('data-i')][1], m = M[d];
      var hit = S[m[0]].f.split('/').pop() === here.file && m[1] === here.page;
      items[i].classList.toggle('on', hit);
      if (hit && !found) found = items[i];
    }
    if (found) found.scrollIntoView({ block: 'nearest' });
    var prev = document.querySelector('.pg.target');
    if (prev) prev.classList.remove('target');
    if (here.page) {
      var el = document.getElementById('p' + here.page);
      if (el) el.classList.add('target');
    }
  }

  function step(dir) {
    if (!curList.length) return;
    var items = box.querySelectorAll('.r');
    if (!items.length) return;
    var at = -1;
    for (var i = 0; i < items.length; i++) if (items[i].classList.contains('on')) { at = i; break; }
    var next = at < 0 ? (dir > 0 ? 0 : items.length - 1) : at + dir;
    if (next < 0 || next >= items.length) return;
    location.href = items[next].getAttribute('href');
    markActive();
  }

  window.addEventListener('hashchange', markActive);

  function setSide(open) {
    document.body.classList.toggle('nosidebar', !open);
    try { sessionStorage.setItem(SIDE, open ? '1' : '0'); } catch (e) {}
  }
  if (toggle) toggle.addEventListener('click', function () {
    setSide(document.body.classList.contains('nosidebar'));
  });

  document.addEventListener('keydown', function (e) {
    var typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
    if (e.key === '/' && !typing) { e.preventDefault(); setSide(true); q.focus(); q.select(); return; }
    if (e.key === '\\' && !typing) { e.preventDefault(); setSide(document.body.classList.contains('nosidebar')); return; }
    if (e.key === 'Escape') { if (typing) q.blur(); return; }
    if (typing) {
      if (e.key === 'ArrowDown') { e.preventDefault(); step(1); }
      if (e.key === 'ArrowUp') { e.preventDefault(); step(-1); }
      return;
    }
    if (e.key === 'j' || e.key === 'J') { e.preventDefault(); step(1); }
    if (e.key === 'k' || e.key === 'K') { e.preventDefault(); step(-1); }
  });

  if (secnav) {
    var links = secnav.querySelectorAll('.navitem');
    for (var i = 0; i < links.length; i++) {
      if (links[i].getAttribute('href').split('/').pop() === here.file) links[i].classList.add('on');
    }
  }

  if (here.page) {
    var el = document.getElementById('p' + here.page);
    if (el) {
      el.classList.add('target');
      setTimeout(function () { el.scrollIntoView({ block: 'start' }); }, 0);
    }
  }

  var stored = '';
  try { stored = sessionStorage.getItem(KEY) || ''; } catch (e) {}
  try { if (sessionStorage.getItem(SIDE) === '0') document.body.classList.add('nosidebar'); } catch (e) {}
  if (stored) { q.value = stored; run(false); }
  if (hint && stored) hint.classList.add('dim');
})();
