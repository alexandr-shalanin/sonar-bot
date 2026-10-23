<script lang="ts">
  import { onDestroy } from 'svelte';
  type Candidate = {
    name: string; score: number; emblem: number; mint: string; pool: string | null; pool_id: string | null;
    first_seen_ms: number; last_seen_ms: number;
    price_usd: number | null; price_source: string | null;
    price_source_ms: number | null; price_seen_ms: number | null;
    price_status: 'fresh' | 'stale' | 'unavailable';
    signals: Record<string, number | null>;
    risk: { status: 'blocked' | 'waiting' | 'review'; block_reasons: string[]; missing_evidence: string[] };
  };
  const riskLabels = { blocked: 'Заблокирован', waiting: 'Недостаточно данных', review: 'Для ручной проверки' };
  const artworks = [
    { name: 'Mooncat', shape: 'M5 7V3h5v4h12V3h5v20h-4v5H9v-5H5Z', detail: 'M9 12h4v4H9Zm10 0h4v4h-4Zm-6 8h6v3h-6Z' },
    { name: 'Volt', shape: 'M16 2h10l-7 11h8L13 30l3-13H6Z', detail: 'M18 5h4l-7 10h5l-4 6 1-7h-6Z' },
    { name: 'Orbit', shape: 'M11 4h10v3h5v6h5v6h-5v6h-5v3H11v-3H6v-6H1v-6h5V7h5Z', detail: 'M11 8h10v4H11ZM5 15h7v3H5Zm7-3h8v3h-8Zm8-3h7v3h-7Zm-9 12h10v3H11Z' },
    { name: 'Boo', shape: 'M10 3h12v4h4v5h3v17h-5v-4h-5v4h-6v-4H8v4H3V12h3V7h4Z', detail: 'M9 12h5v6H9Zm10 0h5v6h-5Zm-5 9h5v3h-5Z' },
    { name: 'Royal', shape: 'M2 7h4v4h5V6h3V2h4v4h3v5h5V7h4v13h-4v8H6v-8H2Z', detail: 'M9 22h14v3H9Zm5-9h4v5h-4ZM5 13h4v4H5Zm18 0h4v4h-4Z' },
    { name: 'Spore', shape: 'M11 2h10v4h5v5h4v10H21v8H11v-8H2V11h4V6h5Z', detail: 'M11 7h5v5h-5Zm10 5h5v5h-5ZM6 14h5v4H6Zm8 8h4v4h-4Z' },
    { name: 'Prism', shape: 'M11 2h10l9 11-14 17L2 13Z', detail: 'M12 6h8l4 5H8Zm2 8h4l-2 10Zm-7 0h4l2 8Zm14 0h4l-6 8Z' },
    { name: 'Astro', shape: 'M19 2h11v11h-4v5h-5v5h-5v6H9v-6H3v-7h6v-5h5V6h5ZM3 25h4v4H3Z', detail: 'M20 7h5v5h-5Zm-8 10h5v5h-5Z' },
    { name: 'Bloom', shape: 'M12 2h8v5h5v5h5v8h-5v5h-5v5h-8v-5H7v-5H2v-8h5V7h5Z', detail: 'M12 12h8v8h-8Zm1-7h6v4h-6ZM5 13h4v6H5Zm18 0h4v6h-4ZM13 23h6v4h-6Z' }
  ];
  const demoScores = [98, 88, 74, 58, 96, 83, 69, 42, 91];
  const rarity = (score: number) => score >= 95 ? 'legendary' : score >= 80 ? 'epic' : score >= 65 ? 'rare' : 'common';
  const now = Date.now();
  const candidates: Candidate[] = Array.from({ length: 9 }, (_, index) => ({
    name: artworks[index].name, score: demoScores[index], emblem: index,
    mint: `DEMO${index + 1}ExampleTokenAddressForDesignOnly000${index + 1}`,
    pool: 'DEMO POOL', pool_id: `DemoPoolExample${index + 1}`,
    first_seen_ms: now - (index + 1) * 180_000, last_seen_ms: now,
    price_usd: index === 7 ? null : 0.0000124 * (index + 1), price_source: 'DEMO',
    price_source_ms: index === 7 ? null : now - (index === 5 ? 120_000 : 4000),
    price_seen_ms: index === 7 ? null : now - (index === 5 ? 120_000 : 4000),
    price_status: index === 7 ? 'unavailable' : index === 5 ? 'stale' : 'fresh',
    signals: { price_change_1m_pct: index === 7 ? null : 3.2 - index * 1.4,
      price_change_5m_pct: index === 7 ? null : 12.5 - index * 2,
      observed_buys_1m_approx: 18 + index * 3, observed_sells_1m_approx: 7 + index,
      observed_buys_5m_approx: 65 + index * 4, observed_sells_5m_approx: 28 + index * 2 },
    risk: { status: 'waiting', block_reasons: [], missing_evidence: ['risk_reports'] }
  }));
  let copied = '';
  let copyError = '';
  let copyReset: ReturnType<typeof setTimeout>;
  onDestroy(() => clearTimeout(copyReset));
  const short = (value: string) => `${value.slice(0, 6)}…${value.slice(-5)}`;
  const price = (value: number | null) => value == null ? 'Нет цены' : `$${value.toLocaleString('en-US', { maximumSignificantDigits: 6 })}`;
  const change = (value: number | null | undefined) => value == null ? 'Нет данных' : `${value > 0 ? '+' : ''}${value.toLocaleString('ru-RU', { maximumFractionDigits: 2 })}%`;
  function age(timestamp: number | null) {
    if (timestamp == null) return 'Нет данных';
    const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
    if (seconds < 60) return `${seconds} с`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} мин`;
    return `${Math.floor(seconds / 3600)} ч`;
  }
  function fresh(token: Candidate) {
    return token.price_status === 'fresh' && token.price_source_ms != null && token.price_seen_ms != null &&
      now - token.price_source_ms <= 30_000 && now - token.price_seen_ms <= 30_000;
  }
  function tilt(node: HTMLElement) {
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    const pointer = matchMedia('(hover: hover) and (pointer: fine)');
    let frame = 0;
    let bounds: DOMRect | null = null;
    function move(event: PointerEvent) {
      if (motion.matches || !pointer.matches || event.pointerType !== 'mouse') return;
      bounds ??= node.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
      const y = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        node.style.setProperty('--rx', ((.5 - y) * 12) + 'deg');
        node.style.setProperty('--ry', ((x - .5) * 12) + 'deg');
        node.style.setProperty('--mx', (x * 100) + '%');
        node.style.setProperty('--my', (y * 100) + '%');
        node.style.setProperty('--lx', ((x - .5) * 14) + 'px');
        node.style.setProperty('--ly', ((y - .5) * 14) + 'px');
        node.classList.add('tilting');
      });
    }
    function reset() {
      cancelAnimationFrame(frame);
      bounds = null;
      node.classList.remove('tilting');
      node.style.setProperty('--rx', '0deg');
      node.style.setProperty('--ry', '0deg');
      node.style.setProperty('--lx', '0px');
      node.style.setProperty('--ly', '0px');
    }
    node.addEventListener('pointermove', move);
    node.addEventListener('pointerleave', reset);
    node.addEventListener('pointercancel', reset);
    window.addEventListener('scroll', reset, { passive: true, capture: true });
    window.addEventListener('resize', reset);
    pointer.addEventListener('change', reset);
    motion.addEventListener('change', reset);
    return { destroy() {
      reset();
      node.removeEventListener('pointermove', move);
      node.removeEventListener('pointerleave', reset);
      node.removeEventListener('pointercancel', reset);
      window.removeEventListener('scroll', reset, true);
      window.removeEventListener('resize', reset);
      pointer.removeEventListener('change', reset);
      motion.removeEventListener('change', reset);
    } };
  }
  async function copy(mint: string) {
    clearTimeout(copyReset);
    copied = '';
    copyError = '';
    try { await navigator.clipboard.writeText(mint); copied = mint; }
    catch { copyError = mint; }
    copyReset = setTimeout(() => { copied = ''; copyError = ''; }, 2000);
  }
</script>

<main class="candidates-page">
  <div class="page-heading">
    <h1>Candidates<span> /</span></h1>
    <div class="tools" aria-label="Фильтры и сортировка — скоро">
      <button disabled title="Фильтры появятся позже"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 7h16M7 12h10M10 17h4" /></svg>Фильтры</button>
      <button disabled title="Настройка сортировки появится позже"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M8 4v16m-4-4 4 4 4-4M15 5h5m-5 6h4m-4 6h3" /></svg>Сначала новые</button>
    </div>
  </div>
  <div class="cards">
    {#each candidates as token (token.mint)}
      <article class="token-card {rarity(token.score)}" use:tilt>
        <div class="artwork">
          <div class="art-surface" aria-hidden="true"></div>
          <span class="emblem-shadow" aria-hidden="true"></span>
          <div class="edition"><span class="stripes" aria-hidden="true"></span><span>{rarity(token.score)}</span></div>
          <span class="token-age">{age(token.first_seen_ms)}</span>
          <div class="orbit-ring" aria-hidden="true"></div>
          <svg class="emblem" viewBox="0 0 32 32" shape-rendering="crispEdges" aria-hidden="true">
            <path class="emblem-shape" d={artworks[token.emblem].shape} />
            <path class="emblem-detail" d={artworks[token.emblem].detail} />
          </svg>
          <span class="art-caption">SONAR COLLECTION / 00{token.emblem + 1}</span>
          <span class="sparkles" aria-hidden="true"></span>
          <span class="art-glass" aria-hidden="true"></span>
        </div>
        <div class="identity"><span>SOLANA / DEMO</span><span>{fresh(token) ? 'СВЕЖАЯ ЦЕНА' : token.price_usd == null ? 'НЕТ ЦЕНЫ' : 'ЦЕНА УСТАРЕЛА'}</span></div>
        <div class="name-row"><h2>{token.name}</h2><div class="score-badge"><span>SCORE</span><strong>{token.score}<small>/100</small></strong></div></div>
        <div class="mint-row">
          <span class="mint" title={token.mint}>{short(token.mint)}</span>
          <button class="copy" class:is-copied={copied === token.mint} on:click={() => copy(token.mint)}
            aria-label={copied === token.mint ? 'Адрес скопирован' : copyError === token.mint ? 'Не удалось скопировать. Повторить' : 'Копировать полный mint-адрес'}
            title={copyError === token.mint ? 'Не удалось скопировать. Повторите попытку' : token.mint}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              {#if copied === token.mint}<path d="m5 12 4 4L19 6" />
              {:else if copyError === token.mint}<path d="m7 7 10 10M17 7 7 17" />
              {:else}<path d="M8 8h12v12H8zM4 15V4h11" />{/if}
            </svg>
          </button>
        </div>
        <div class="risk"><span aria-hidden="true">{token.risk.status === 'blocked' ? '×' : token.risk.status === 'waiting' ? '…' : '↗'}</span>{riskLabels[token.risk.status]}</div>
        <div class="quote"><strong>{price(token.price_usd)}</strong><span>{token.price_source ?? 'Нет источника'} · {age(token.price_source_ms)}</span></div>
        <div class="metrics">
          <div><span>Изменение · 1 мин</span><strong>{fresh(token) ? change(token.signals.price_change_1m_pct) : 'Нет данных'}</strong></div>
          <div><span>Наблюдавшиеся сделки · 1 мин</span><strong>{token.signals.observed_buys_1m_approx ?? '—'} <small>покупок</small> / {token.signals.observed_sells_1m_approx ?? '—'} <small>продаж</small></strong></div>
        </div>
      </article>
    {/each}
  </div>
</main>

<style>
  .candidates-page { max-width: 1320px; margin: 0 auto; padding: 48px 40px 80px; }
  .page-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 36px; }
  h1 { margin: 0; font: 400 clamp(17px, 2.2vw, 28px)/1.6 'Press Start', monospace; color: #ff65ba; text-shadow: 0 0 24px #ff209f30; }
  h1 span { color: #ff209f; }
  .tools { display: flex; flex-wrap: wrap; gap: 10px; }
  .tools button { display: flex; align-items: center; gap: 8px; min-height: 42px; padding: 8px 14px; border: 1px solid #ffffff20; border-radius: 8px; background: #252029; color: #b8acbb; font: 12px system-ui, sans-serif; cursor: not-allowed; }
  .tools svg { width: 18px; height: 18px; }
  .cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 28px; align-items: start; }
  .token-card { --paper: #c0c4cc; --ink: #202733; --art: #929ba9; --accent: #edf0f4; --rx: 0deg; --ry: 0deg; --mx: 50%; --my: 50%; --lx: 0px; --ly: 0px; position: relative; transform-style: preserve-3d; min-width: 0; padding: 12px 16px 0; border: 1px solid #ffffff60; border-radius: 14px; background: var(--paper); color: var(--ink); box-shadow: 0 10px 0 -5px #09070c, 0 16px 30px #09070c60; font: 13px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; transform: perspective(1000px) rotateX(var(--rx)) rotateY(var(--ry)); transition: transform 450ms cubic-bezier(.2,.8,.2,1), box-shadow 350ms; }
  .token-card.tilting { z-index: 2; transition: transform 100ms ease-out, box-shadow 350ms; }
  .legendary { --paper: #efd082; --ink: #382810; --art: #b77b2c; --accent: #fff4c6; background: linear-gradient(125deg, #f2d587 0%, #ffedba 19%, #ddb354 43%, #f9e2a0 70%, #e8c470 100%); border-color: #fff0b6; box-shadow: 0 10px 0 -5px #38260d, 0 12px 40px #dfaa3a25; }
  .epic { --paper: #c5a8f0; --ink: #32204e; --art: #7b4ab0; --accent: #f4e9ff; background: linear-gradient(130deg, #d5bafb, #b89be3 55%, #d4bbf5); border-color: #e3caff; box-shadow: 0 10px 0 -5px #281b3b, 0 12px 30px #a26bde18; }
  .rare { --paper: #8fbce8; --ink: #162e49; --art: #4b82b8; --accent: #d5eaff; }
  .token-card::after { content: ''; position: absolute; z-index: 3; inset: 0; border-radius: inherit; pointer-events: none; opacity: 0; background: radial-gradient(circle at var(--mx) var(--my), #fff9 0%, #fff2 18%, transparent 52%); mix-blend-mode: soft-light; transition: opacity 400ms; }
  .legendary.tilting::after { opacity: .9; }
  .epic.tilting::after { opacity: .4; }
  .legendary.tilting { box-shadow: 0 18px 35px #08050a90, 0 0 30px #e9c36535; }
  .epic.tilting { box-shadow: 0 18px 35px #08050a90, 0 0 20px #ad78ed20; }
  .artwork { position: relative; display: grid; place-items: center; height: 238px; border-radius: 7px; transform-style: preserve-3d; }
  .art-surface { position: absolute; inset: 0; overflow: hidden; border-radius: inherit; transform: translateZ(2px); background: radial-gradient(circle at 50% 45%, #ffffff40, transparent 65%), radial-gradient(var(--ink) .5px, transparent .8px) 0 0 / 4px 4px, var(--art); }
  .artwork::after { content: ''; position: absolute; inset: 12px; border: 1px solid #ffffff30; border-radius: 50%; pointer-events: none; transform: translateZ(8px); }
  .edition { transform: translateZ(58px); position: absolute; z-index: 2; left: 0; top: 0; display: flex; flex-direction: column; gap: 7px; padding: 0 16px 12px 0; background: var(--paper); clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%); font-size: 11px; line-height: 1.2; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; }
  .stripes { width: 90px; height: 7px; background: repeating-linear-gradient(115deg, var(--ink) 0 5px, transparent 5px 8px); }
  .token-age { transform: translateZ(58px); position: absolute; z-index: 2; right: 10px; top: 10px; color: var(--accent); font-size: 11px; font-weight: 700; }
  .orbit-ring { position: absolute; width: 146px; height: 146px; border: 1px solid #ffffff35; border-radius: 50%; transform: translate3d(calc(var(--lx) * .3), calc(var(--ly) * .3), 14px) rotate(-25deg) scaleX(1.35); }
  .emblem { z-index: 1; width: 132px; height: 132px; overflow: visible; filter: drop-shadow(calc(0px - var(--lx)) calc(5px - var(--ly)) 1px #0003); transform: translate3d(var(--lx), var(--ly), 36px); }
  .emblem-shape { fill: var(--ink); stroke: var(--accent); stroke-width: 1; paint-order: stroke; }
  .emblem-detail { fill: var(--accent); }
  .art-caption { transform: translateZ(58px); position: absolute; z-index: 2; bottom: 14px; color: var(--accent); font: 9px/1.4 ui-monospace, monospace; letter-spacing: 1.8px; }
  .legendary .art-surface::before, .epic .art-surface::before { content: ''; position: absolute; inset: -80%; pointer-events: none; }
  .legendary .art-surface::before { background: repeating-conic-gradient(from 20deg at 50% 50%, transparent 0deg 12deg, #fff2 16deg, transparent 24deg 40deg), linear-gradient(120deg, transparent 35%, #fff6 45%, #ffe8a088 49%, transparent 58%); animation: gold-foil 12s ease-in-out infinite alternate; }
  .epic .art-surface::before { opacity: .45; background: repeating-linear-gradient(125deg, transparent 0 45px, #eab9ff66 46px 47px, transparent 48px 65px), linear-gradient(125deg, transparent 35%, #86dcff55 43%, #f5d0ff66 49%, transparent 58%); animation: epic-foil 15s ease-in-out infinite alternate; }
  .emblem-shadow { position: absolute; width: 124px; height: 40px; top: calc(50% + 43px); border-radius: 50%; background: radial-gradient(ellipse, #0005, transparent 68%); transform: translate3d(calc(0px - var(--lx)), calc(0px - var(--ly)), 4px); pointer-events: none; }
  .art-glass { position: absolute; inset: 0; border: 1px solid #ffffff35; border-radius: inherit; box-shadow: inset 0 1px 0 #ffffff35, inset 0 -1px 0 #0002; transform: translateZ(52px); pointer-events: none; }
  .legendary .art-glass, .epic .art-glass { background: linear-gradient(135deg, #ffffff0a, transparent 40%, #ffffff08); }
  .legendary.tilting .art-glass { background: radial-gradient(ellipse at var(--mx) var(--my), #fff5, transparent 62%), linear-gradient(125deg, transparent 40%, #fff2 49%, transparent 56%); }
  .epic.tilting .art-glass { background: radial-gradient(ellipse at var(--mx) var(--my), #f4dfff26, transparent 62%); }
  .orbit-ring, .emblem, .emblem-shadow { transition: transform 450ms cubic-bezier(.2,.8,.2,1), filter 450ms; }
  .tilting .orbit-ring, .tilting .emblem, .tilting .emblem-shadow { transition-duration: 100ms; }
  .sparkles { display: none; pointer-events: none; transform: translate3d(calc(var(--lx) * -.25), calc(var(--ly) * -.25), 22px); }
  .legendary .sparkles { display: block; position: absolute; z-index: 2; inset: 0; background: radial-gradient(ellipse 1px 8px at 18% 56%, #fff 60%, transparent 100%), radial-gradient(ellipse 8px 1px at 18% 56%, #fff 60%, transparent 100%), radial-gradient(ellipse 1px 6px at 81% 28%, #fff 60%, transparent 100%), radial-gradient(ellipse 6px 1px at 81% 28%, #fff 60%, transparent 100%), radial-gradient(ellipse 1px 5px at 73% 76%, #fff 60%, transparent 100%), radial-gradient(ellipse 5px 1px at 73% 76%, #fff 60%, transparent 100%); animation: twinkle 4s ease-in-out infinite alternate; }
  .epic .sparkles { display: block; position: absolute; z-index: 2; inset: 0; opacity: .5; background: radial-gradient(circle at 18% 70%, #fff 0 1px, transparent 2px), radial-gradient(circle at 80% 30%, #fff 0 1px, transparent 2px), radial-gradient(circle at 78% 78%, #e6d3ff 0 1px, transparent 2px); }
  @keyframes gold-foil { from { transform: translateX(-8%) rotate(-8deg); } to { transform: translateX(8%) rotate(12deg); } }
  @keyframes epic-foil { from { transform: translateX(-10%); } to { transform: translateX(10%); } }
  @keyframes twinkle { 0%, 15% { opacity: .25; } 60%, 100% { opacity: .95; } }
  .identity { display: flex; justify-content: space-between; gap: 8px; margin-top: 17px; font: 700 10px/1.5 -apple-system, BlinkMacSystemFont, sans-serif; letter-spacing: .6px; }
  .identity span:last-child { font: 9px/1.4 system-ui, sans-serif; font-weight: 700; }
  .mint-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 7px 0; }
  .name-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 14px 0 3px; }
  .score-badge { flex: none; text-align: right; }
  .score-badge > span { display: block; font-size: 8px; font-weight: 800; letter-spacing: 1.5px; }
  .score-badge strong { display: block; font-size: 25px; line-height: 1.1; font-weight: 800; font-variant-numeric: tabular-nums; }
  .score-badge small { font-size: 11px; margin-left: 2px; font-weight: 500; }
  .mint { font: 12px/1.4 ui-monospace, monospace; }
  h2 { min-width: 0; overflow: hidden; margin: 0; font: 850 clamp(26px, 2.5vw, 34px)/1.2 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: -1.2px; }
  .copy { display: grid; place-items: center; flex: none; width: 44px; height: 44px; border: 1px solid currentColor; border-radius: 7px; background: transparent; color: inherit; cursor: pointer; }
  .copy svg { width: 20px; height: 20px; }
  .copy.is-copied { background: var(--ink); color: var(--paper); }
  .copy.is-copied path { stroke-dasharray: 24; animation: checkmark 240ms ease-out both; }
  @keyframes checkmark { from { stroke-dashoffset: 24; } to { stroke-dashoffset: 0; } }
  .risk { display: flex; align-items: center; gap: 8px; min-height: 30px; font-weight: 700; }
  .risk > span { display: grid; place-items: center; width: 20px; height: 20px; border: 1px solid currentColor; font: 20px 'VT323', monospace; }
  .quote { display: flex; flex-direction: column; gap: 3px; padding: 15px 0; border-bottom: 1px solid #25122140; }
  .quote strong { font: 750 27px/1.2 -apple-system, BlinkMacSystemFont, sans-serif; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
  .quote > span { font-size: 11px; }
  .metrics { display: flex; flex-direction: column; gap: 12px; padding: 16px 0; }
  .metrics > div { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 5px 10px; }
  .metrics > div > span { font-size: 11px; }
  .metrics strong { font: 650 13px/1.4 -apple-system, BlinkMacSystemFont, sans-serif; font-variant-numeric: tabular-nums; }
  .metrics small { font: 11px system-ui, sans-serif; }
  button:focus-visible { outline: 3px solid #251221; outline-offset: 3px; }
  @media (max-width: 1050px) { .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 650px) { .candidates-page { padding: 32px 20px 60px; } .cards { grid-template-columns: minmax(0, 1fr); gap: 24px; } .page-heading { margin-bottom: 26px; } .artwork { height: 230px; } h2 { font-size: 24px; } }
  @media (hover: none), (pointer: coarse) { .token-card { transform: none; transform-style: flat; } .artwork { transform-style: flat; } .emblem { transform: none; } .orbit-ring { transform: rotate(-25deg) scaleX(1.35); } .emblem-shadow { transform: none; } .legendary .art-surface::before, .epic .art-surface::before { animation: none; } }
  @media (prefers-reduced-motion: reduce) { .token-card, .token-card.tilting { transition: none; transform: none; transform-style: flat; } .artwork { transform-style: flat; } .orbit-ring, .emblem, .emblem-shadow { transition: none; } .emblem { transform: none; } .orbit-ring { transform: rotate(-25deg) scaleX(1.35); } .emblem-shadow { transform: none; } .legendary .art-surface::before, .epic .art-surface::before, .legendary .sparkles { animation: none; } .token-card::after { display: none; } .copy.is-copied path { animation: none; } }
</style>
