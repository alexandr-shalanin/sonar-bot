<script lang="ts">
  import { onDestroy, tick } from 'svelte';
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
  let selected: Candidate | null = null;
  let phase: 'closed' | 'opening' | 'open' | 'closing' = 'closed';
  let detailsDialog: HTMLDialogElement;
  let flight: HTMLDivElement;
  let rotor: HTMLDivElement;
  let dock: HTMLDivElement;
  let backButton: HTMLButtonElement;
  let originCard: HTMLElement;
  let sourceSize = { width: 1, height: 1 };
  let animations: Animation[] = [];
  let closeRequested = false;
  let disposed = false;
  let previousOverflow = '';
  let scrollLocked = false;
  const reasonLabels: Record<string, string> = {
    mintable: 'Возможен дополнительный выпуск токенов',
    freezable: 'Возможна заморозка токенов',
    non_transferable: 'Передача токенов запрещена',
    default_frozen: 'Токены заморожены по умолчанию',
    transfer_hook: 'Переводы зависят от дополнительной программы',
    transfer_fee_upgradable: 'Комиссия за перевод может меняться',
    full_transfer_fee: 'Комиссия за перевод составляет 100%',
    rugged: 'RugCheck сообщил о rug pull',
    low_pool_liquidity: 'Ликвидность пула ниже установленного порога',
    fresh_price: 'Нет свежей USD-цены',
    risk_reports: 'Не хватает актуальных проверок риска',
    pool_liquidity: 'Нет данных о ликвидности этого пула',
    holders: 'Нет данных о концентрации адресов',
    recent_pool_sells: 'Не наблюдались недавние продажи в этом пуле'
  };
  const timestamp = (value: number | null) => value == null ? 'Нет данных' : new Date(value).toLocaleString('ru-RU');
  const observed = (value: number | null | undefined) => value == null ? 'Нет данных' : value.toLocaleString('ru-RU');

  function unlockScroll() {
    if (scrollLocked) document.body.style.overflow = previousOverflow;
    scrollLocked = false;
  }
  onDestroy(() => {
    disposed = true;
    clearTimeout(copyReset);
    animations.forEach(animation => animation.cancel());
    detailsDialog?.close();
    unlockScroll();
  });

  function originPose(rect: DOMRect) {
    return `translate3d(${rect.left}px, ${rect.top + detailsDialog.scrollTop}px, 0) scale(${rect.width / sourceSize.width}, ${rect.height / sourceSize.height})`;
  }
  function dockPose() {
    const rect = dock.getBoundingClientRect();
    const scale = Math.min(rect.width / sourceSize.width, rect.height / sourceSize.height, 1);
    const x = rect.left + (rect.width - sourceSize.width * scale) / 2;
    const y = rect.top + (rect.height - sourceSize.height * scale) / 2 + detailsDialog.scrollTop;
    return `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
  }
  async function fly(from: string, to: string, returning = false) {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) { flight.style.transform = to; return true; }
    const options = { duration: returning ? 950 : 1150, easing: 'cubic-bezier(.4, 0, .2, 1)', fill: 'both' as FillMode };
    const direction = returning ? -1 : 1;
    animations = [
      flight.animate([{ transform: from }, { transform: to }], options),
      rotor.animate([
        { transform: 'perspective(1400px) rotateY(0deg) rotateZ(0deg)' },
        { transform: `perspective(1400px) rotateY(${direction * 360}deg) rotateZ(${direction * -5}deg)`, offset: .5 },
        { transform: `perspective(1400px) rotateY(${direction * 720}deg) rotateZ(0deg)` }
      ], options)
    ];
    try { await Promise.all(animations.map(animation => animation.finished)); }
    catch { return false; }
    if (disposed) return false;
    flight.style.transform = to;
    animations.forEach(animation => animation.cancel());
    animations = [];
    return true;
  }
  async function openDetails(token: Candidate, button: HTMLButtonElement) {
    if (phase !== 'closed') return;
    originCard = button.closest('article')!;
    originCard.style.transition = 'none';
    originCard.classList.remove('tilting');
    for (const [key, value] of Object.entries({ '--rx': '0deg', '--ry': '0deg', '--lx': '0px', '--ly': '0px' })) originCard.style.setProperty(key, value);
    const rect = originCard.getBoundingClientRect();
    originCard.style.removeProperty('transition');
    sourceSize = { width: originCard.offsetWidth, height: originCard.offsetHeight };
    closeRequested = false;
    phase = 'opening';
    selected = token;
    await tick();
    if (disposed) return;
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    scrollLocked = true;
    detailsDialog.showModal();
    detailsDialog.scrollTop = 0;
    backButton.focus({ preventScroll: true });
    if (!await fly(originPose(rect), dockPose())) return;
    if (closeRequested) { phase = 'open'; await closeDetails(); return; }
    phase = 'open';
    await tick();
    reposition();
  }
  async function closeDetails() {
    if (phase === 'opening') { closeRequested = true; return; }
    if (phase !== 'open') return;
    phase = 'closing';
    const from = getComputedStyle(flight).transform;
    if (!await fly(from, originPose(originCard.getBoundingClientRect()), true)) return;
    selected = null;
    phase = 'closed';
    detailsDialog.close();
    unlockScroll();
    await tick();
    originCard.querySelector<HTMLButtonElement>('.card-open')?.focus({ preventScroll: true });
  }
  function reposition() {
    if (phase === 'open' && dock && flight) flight.style.transform = dockPose();
  }
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
  function tilt(node: HTMLElement, enabled: boolean) {
    if (!enabled) return;
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

<svelte:window on:resize={reposition} />

{#snippet card(token: Candidate, interactive: boolean)}
      <article class="token-card {rarity(token.score)}" class:source-hidden={interactive && selected?.mint === token.mint} class:flying={!interactive} use:tilt={interactive}>
        {#if interactive}<button class="card-open" aria-label={`Открыть ${token.name}`} on:click={(event) => openDetails(token, event.currentTarget)}></button>{/if}
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
{/snippet}

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
      {@render card(token, true)}
    {/each}
  </div>
</main>

<dialog bind:this={detailsDialog} class="token-dialog phase-{phase}" aria-labelledby="token-detail-name" on:cancel|preventDefault={closeDetails}>
  <button bind:this={backButton} class="detail-back" on:click={closeDetails}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m14 6-6 6 6 6M8 12h12" /></svg>Назад к карточкам
  </button>
  <button class="detail-scrim" tabindex="-1" aria-label="Закрыть подробности" on:click={closeDetails}></button>
  {#if selected}
    <div class="detail-layout">
      <div bind:this={dock} class="card-dock" aria-hidden="true"></div>
      <section class="details-panel" aria-label="Информация о токене" inert={phase !== 'open'}>
        <div class="file-heading"><span>SONAR / TOKEN FILE</span><span>00{selected.emblem + 1}</span></div>
        <div class="detail-heading"><div><p class="detail-kicker">SOLANA · {rarity(selected.score)}</p><h2 id="token-detail-name">{selected.name}</h2></div><div class="detail-score"><span>SCORE</span><strong>{selected.score}<small>/100</small></strong></div></div>
        <div class="detail-section">
          <h3><span>01</span>Идентификаторы</h3>
          <dl class="detail-addresses"><dt>Mint-адрес</dt><dd>{selected.mint}</dd><dt>Площадка</dt><dd>{selected.pool ?? 'Нет данных'}</dd><dt>Pool ID</dt><dd>{selected.pool_id ?? 'Нет данных'}</dd></dl>
        </div>
        <div class="detail-section">
          <h3><span>02</span>Цена и наблюдения</h3>
          <div class="detail-facts"><div><span>Цена USD</span><strong>{price(selected.price_usd)}</strong></div><div><span>Состояние цены</span><strong>{fresh(selected) ? 'Свежая' : selected.price_usd == null ? 'Нет цены' : 'Устарела'}</strong></div><div><span>Источник</span><strong>{selected.price_source ?? 'Нет данных'}</strong></div><div><span>Возраст цены</span><strong>{age(selected.price_source_ms)}</strong></div></div>
          <dl class="detail-times"><div><dt>Токен обнаружен</dt><dd>{timestamp(selected.first_seen_ms)}</dd></div><div><dt>Последнее наблюдение</dt><dd>{timestamp(selected.last_seen_ms)}</dd></div><div><dt>Время цены у источника</dt><dd>{timestamp(selected.price_source_ms)}</dd></div><div><dt>Цена получена Sonar</dt><dd>{timestamp(selected.price_seen_ms)}</dd></div></dl>
        </div>
        <div class="detail-section">
          <h3><span>03</span>Короткая активность</h3>
          <div class="activity-table"><div class="activity-row activity-labels"><span>Наблюдения</span><span>1 мин</span><span>5 мин</span></div><div class="activity-row"><span>Изменение цены</span><strong>{fresh(selected) ? change(selected.signals.price_change_1m_pct) : 'Нет данных'}</strong><strong>{fresh(selected) ? change(selected.signals.price_change_5m_pct) : 'Нет данных'}</strong></div><div class="activity-row"><span>Покупки</span><strong>{observed(selected.signals.observed_buys_1m_approx)}</strong><strong>{observed(selected.signals.observed_buys_5m_approx)}</strong></div><div class="activity-row"><span>Продажи</span><strong>{observed(selected.signals.observed_sells_1m_approx)}</strong><strong>{observed(selected.signals.observed_sells_5m_approx)}</strong></div></div>
          <p class="detail-note">Наблюдавшиеся покупки и продажи приблизительные из-за поминутного хранения.</p>
        </div>
        <div class="detail-section">
          <h3><span>04</span>Проверка риска</h3>
          <p class="detail-risk">{riskLabels[selected.risk.status]}</p>
          {#each selected.risk.block_reasons as reason}<p class="risk-reason">{reasonLabels[reason] ?? 'Требуется дополнительная проверка'}</p>{/each}
          {#each selected.risk.missing_evidence as reason}<p class="risk-reason">{reasonLabels[reason] ?? 'Требуется дополнительная проверка'}</p>{/each}
          <div class="detail-facts providers"><div><span>GoPlus</span><strong>Нет данных</strong></div><div><span>RugCheck</span><strong>Нет данных</strong></div><div><span>Ликвидность пула</span><strong>Нет данных</strong></div><div><span>Концентрация адресов</span><strong>Нет данных</strong></div></div>
        </div>
      </section>
    </div>
    <div bind:this={flight} class="flight-position" inert={phase !== 'open'} style:width={sourceSize.width + 'px'} style:height={sourceSize.height + 'px'}>
      <div bind:this={rotor} class="flight-rotor">
        <div class="flight-front">{@render card(selected, false)}</div>
        <div class="flight-back {rarity(selected.score)}" aria-hidden="true"><div class="back-grid"></div><img class="engraved-cat" src="/images/void-cat.png" alt="" /></div>
      </div>
    </div>
  {/if}
</dialog>

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
  .source-hidden { visibility: hidden; }
  .card-open { position: absolute; z-index: 4; inset: 0; width: 100%; height: 100%; padding: 0; border: 0; border-radius: inherit; background: transparent; cursor: pointer; transform: translateZ(66px); }
  .token-card.flying { width: 100%; height: 100%; box-sizing: border-box; transform: none; }
  .token-card.flying::after { display: none; }
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
  .copy { position: relative; z-index: 5; transform: translateZ(70px); display: grid; place-items: center; flex: none; width: 44px; height: 44px; border: 1px solid currentColor; border-radius: 7px; background: transparent; color: inherit; cursor: pointer; }
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
  .token-dialog { position: fixed; inset: 0; width: 100%; max-width: none; height: 100%; max-height: none; margin: 0; padding: 0; border: 0; overflow: hidden; background: transparent; color: #f5edf4; font: 14px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .token-dialog::backdrop { background: #100c19b8; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
  .detail-scrim { position: fixed; inset: 0; width: 100%; height: 100%; border: 0; padding: 0; background: transparent; cursor: default; }
  .detail-back { position: fixed; top: 24px; left: 5vw; z-index: 6; display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 10px 16px; border: 1px solid #ffffff25; border-radius: 12px; background: #28212fed; color: #f4d5e7; cursor: pointer; font: 500 13px/1.3 -apple-system, BlinkMacSystemFont, sans-serif; transition: border-color 200ms, background 200ms; }
  .detail-back:hover { border-color: #ff65ba90; background: #3b2639; }
  .detail-back svg { width: 20px; height: 20px; }
  .detail-back:focus-visible { outline-color: #ff65ba; }
  .detail-layout { position: relative; display: grid; grid-template-columns: minmax(240px, .8fr) minmax(0, 1.6fr); align-items: center; gap: clamp(24px, 4vw, 64px); width: 100%; max-width: 1600px; height: 100%; min-height: 0; margin: 0 auto; padding: 88px 5vw 32px; box-sizing: border-box; pointer-events: none; }
  .card-dock { width: 100%; height: 100%; min-height: 0; }
  .flight-position { position: absolute; z-index: 3; top: 0; left: 0; transform-origin: 0 0; pointer-events: none; }
  .phase-open .flight-position { pointer-events: auto; }
  .flight-rotor { width: 100%; height: 100%; transform-style: preserve-3d; }
  .flight-front, .flight-back { position: absolute; inset: 0; width: 100%; height: 100%; backface-visibility: hidden; -webkit-backface-visibility: hidden; }
  .flight-front { transform: rotateY(0deg); }
  .flight-back { display: grid; place-items: center; overflow: hidden; box-sizing: border-box; transform: rotateY(180deg); border: 1px solid var(--accent, #edf0f4); border-radius: 14px; background: var(--paper, #c0c4cc); box-shadow: inset 0 2px 2px #ffffff60, inset 0 -2px 4px #0004, 0 20px 40px #0005; }
  .back-grid { position: absolute; inset: 0; background: linear-gradient(#00000012 1px, transparent 1px), linear-gradient(90deg, #00000012 1px, transparent 1px); background-size: 24px 24px; }
  .flight-back::after { content: ''; position: absolute; inset: 12px; border: 1px solid #0003; border-radius: 7px; box-shadow: 0 1px 0 #ffffff60, inset 0 1px 0 #ffffff60; }
  .engraved-cat { position: relative; width: 74%; max-height: 74%; object-fit: contain; opacity: .5; image-rendering: pixelated; filter: grayscale(1) brightness(.65) contrast(1.4) drop-shadow(0 2px 0 #ffffff80); mix-blend-mode: multiply; }
  .details-panel { position: relative; align-self: stretch; min-width: 0; min-height: 0; padding: clamp(22px, 3vw, 42px); border: 1px solid #ff65ba40; border-radius: 20px; overflow: auto; overscroll-behavior: contain; scrollbar-width: thin; scrollbar-color: #715064 transparent; background: linear-gradient(140deg, #342333a8, transparent 55%), #201b28f5; box-shadow: 0 28px 90px #0005, inset 0 1px 0 #ffffff0a; visibility: hidden; opacity: 0; transform: translateY(12px); pointer-events: none; transition: opacity 180ms, transform 300ms; }
  .phase-open .details-panel { visibility: visible; opacity: 1; transform: none; pointer-events: auto; animation: panel-arrive 380ms steps(1, end) both; }
  .phase-closing .details-panel { visibility: visible; opacity: 0; transform: translateY(8px); }
  .file-heading { display: flex; justify-content: space-between; gap: 16px; color: #c5a6c1; font: 10px/1.5 ui-monospace, monospace; letter-spacing: 2px; }
  .detail-heading { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin: 26px 0 34px; }
  .detail-kicker { margin: 0 0 8px; color: #ff8acb; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }
  .details-panel h2 { margin: 0; color: #fff0fa; font: 800 clamp(30px, 3.5vw, 52px)/1.1 -apple-system, BlinkMacSystemFont, sans-serif; letter-spacing: -1.5px; overflow-wrap: anywhere; }
  .detail-score { flex: none; text-align: right; }
  .detail-score > span { color: #b8a2bb; font-size: 9px; font-weight: 700; letter-spacing: 2px; }
  .detail-score strong { display: block; color: #ff87c9; font-size: 40px; font-weight: 750; line-height: 1.1; font-variant-numeric: tabular-nums; }
  .detail-score small { color: #b9a4bb; font-size: 15px; font-weight: 400; }
  .detail-section { margin-top: 26px; padding-top: 22px; border-top: 1px solid #ffffff13; }
  .detail-section h3 { display: flex; align-items: center; gap: 12px; margin: 0 0 18px; color: #eadee9; font-size: 14px; font-weight: 650; }
  .detail-section h3 > span { color: #ff65ba; font: 10px ui-monospace, monospace; }
  .details-panel dl { margin: 0; }
  .details-panel dt { color: #b4a2ba; font-size: 11px; }
  .details-panel dd { margin: 5px 0 14px; color: #f1e6f0; font: 12px/1.6 ui-monospace, monospace; overflow-wrap: anywhere; }
  .detail-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .detail-facts > div { min-width: 0; padding: 14px; border: 1px solid #ffffff10; border-radius: 10px; background: #ffffff04; }
  .detail-facts span { display: block; margin-bottom: 7px; color: #bba8c1; font-size: 11px; }
  .detail-facts strong { color: #eee2ee; font-size: 15px; font-weight: 600; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
  .detail-times { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 18px; margin-top: 18px !important; }
  .detail-times dd { font-size: 11px; }
  .activity-row { display: grid; grid-template-columns: 1.6fr 1fr 1fr; gap: 10px; align-items: center; min-height: 44px; border-bottom: 1px solid #ffffff0b; font-size: 12px; }
  .activity-row strong { text-align: right; font-weight: 550; font-variant-numeric: tabular-nums; }
  .activity-labels { color: #bca5c0; font-size: 10px; }
  .activity-labels span:not(:first-child) { text-align: right; }
  .detail-note { margin: 12px 0 0; color: #ad98b4; font-size: 11px; line-height: 1.6; }
  .detail-risk { margin: 0 0 10px; color: #f0cae1; font-size: 15px; font-weight: 650; }
  .risk-reason { margin: 7px 0; color: #c9b5ce; font-size: 12px; }
  .providers { margin-top: 18px; }
  @keyframes panel-arrive { 0% { clip-path: inset(12% 0 50%); transform: translateX(12px); filter: drop-shadow(-4px 0 #ff65ba88) drop-shadow(4px 0 #84ecff55); } 18% { clip-path: inset(0 0 0); transform: translateX(-5px); } 32% { clip-path: polygon(0 0,100% 0,100% 22%,2% 22%,2% 24%,100% 24%,100% 67%,0 67%,0 70%,98% 70%,98% 100%,0 100%); transform: translateX(3px); } 52% { clip-path: inset(0); transform: translateX(-2px); } 68% { transform: translateX(1px); filter: none; } 100% { clip-path: inset(0); transform: none; filter: none; } }
  @media (max-width: 850px) { .token-dialog { overflow-y: auto; } .detail-layout { height: auto; min-height: 100%; grid-template-columns: minmax(0, 1fr); gap: 24px; padding: 86px 20px 28px; } .card-dock { width: min(72vw, 300px); height: min(110vw, 440px); margin: 0 auto; } .details-panel { overflow: visible; border-radius: 16px; padding: 22px; } .detail-back { top: 18px; left: 20px; } }
  @media (max-width: 400px) { .details-panel { padding: 18px; } .detail-times { grid-template-columns: minmax(0, 1fr); } .detail-heading { gap: 12px; } .details-panel h2 { font-size: 30px; } .detail-score strong { font-size: 32px; } }
  @media (prefers-reduced-motion: reduce) { .phase-open .details-panel { animation: none; } .details-panel, .detail-back { transition: none; } }
  @media (max-width: 1050px) { .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 650px) { .candidates-page { padding: 32px 20px 60px; } .cards { grid-template-columns: minmax(0, 1fr); gap: 24px; } .page-heading { margin-bottom: 26px; } .artwork { height: 230px; } h2 { font-size: 24px; } }
  @media (hover: none), (pointer: coarse) { .token-card { transform: none; transform-style: flat; } .artwork { transform-style: flat; } .emblem { transform: none; } .orbit-ring { transform: rotate(-25deg) scaleX(1.35); } .emblem-shadow { transform: none; } .legendary .art-surface::before, .epic .art-surface::before { animation: none; } }
  @media (prefers-reduced-motion: reduce) { .token-card, .token-card.tilting { transition: none; transform: none; transform-style: flat; } .artwork { transform-style: flat; } .orbit-ring, .emblem, .emblem-shadow { transition: none; } .emblem { transform: none; } .orbit-ring { transform: rotate(-25deg) scaleX(1.35); } .emblem-shadow { transform: none; } .legendary .art-surface::before, .epic .art-surface::before, .legendary .sparkles { animation: none; } .token-card::after { display: none; } .copy.is-copied path { animation: none; } }
</style>
