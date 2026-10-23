<script lang="ts">
  import { onDestroy } from 'svelte';

  type Report = {
    mint: string;
    status: string;
    token: { name: string | null; symbol: string | null };
    selected_pool: {
      dex: string | null; pool_id: string; price_usd: number | null; liquidity_usd: number | null;
      windows: { m5: { price_change_pct: number | null; volume_usd: number | null; observed_buys: number | null; observed_sells: number | null } };
    } | null;
    score: { status: string; value: number | null; block_reasons: string[]; missing_evidence: string[]; conflicts: string[] };
  };

  let mint = '';
  let loading = false;
  let error = '';
  let report: Report | null = null;
  let controller: AbortController | null = null;

  const labels: Record<string, string> = {
    mintable: 'Можно выпустить дополнительные токены',
    freezable: 'Адреса с токеном могут быть заморожены',
    non_transferable: 'Токен нельзя передать другому адресу',
    default_frozen: 'Новые счета с токеном заморожены',
    transfer_hook: 'Переводы проходят через дополнительное правило',
    transfer_fee_upgradable: 'Комиссию за перевод можно изменить',
    balance_mutable_authority: 'Баланс токенов может быть изменён',
    closable: 'Счёт с токеном можно закрыть',
    default_account_state_upgradable: 'Состояние новых счетов можно изменить',
    transfer_hook_upgradable: 'Правило переводов можно изменить',
    rugged: 'RugCheck сообщает о проблеме с токеном',
    pool_liquidity: 'Недостаточная ликвидность пула',
    low_pool_liquidity: 'Ликвидность пула ниже $1 000',
    pool_liquidity_sources_disagree: 'Источники расходятся в оценке ликвидности',
    transfer_fee_bps: 'Нет данных о комиссии за перевод',
    full_transfer_fee: 'Комиссия за перевод составляет 100%',
    usd_price: 'Нет цены в USD',
    holder_concentration: 'Нет данных о концентрации токенов на адресах',
    rugcheck_findings: 'Нет данных о замечаниях RugCheck',
    activity_5m: 'Нет данных об активности за 5 минут'
  };
  const explain = (reason: string) => labels[reason] ?? reason.replaceAll('_', ' ');
  const money = (value: number | null | undefined) => value == null ? 'Нет данных' : '$' + value.toLocaleString('en-US', { maximumFractionDigits: value < 0.01 ? 10 : 4 });
  const count = (value: number | null | undefined) => value == null ? 'Нет данных' : value.toLocaleString('ru-RU');
  const percent = (value: number | null | undefined) => value == null ? 'Нет данных' : (value > 0 ? '+' : '') + value.toLocaleString('ru-RU') + '%';

  async function search() {
    const address = mint.trim();
    error = '';
    report = null;
    if (!address) {
      error = 'Вставьте адрес токена Solana.';
      return;
    }
    controller?.abort();
    controller = new AbortController();
    loading = true;
    try {
      const response = await fetch('/inspector', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mint: address }), signal: controller.signal
      });
      if (response.status === 422) {
        error = 'Проверьте адрес: нужен полный mint-адрес токена Solana.';
        return;
      }
      if (response.status === 429) {
        error = 'Сервис занят. Повторите поиск через несколько секунд.';
        return;
      }
      if (!response.ok && response.status !== 503) throw new Error('request_failed');
      report = await response.json() as Report;
    } catch (cause) {
      if ((cause as Error).name !== 'AbortError') error = 'Не удалось получить отчёт. Проверьте подключение к серверу и повторите поиск.';
    } finally {
      loading = false;
    }
  }

  onDestroy(() => controller?.abort());
</script>

<main class:has-report={report || loading || error} class="inspector">
  <div class="search-block">
    <h1>Search coin. <span>Receive score.</span></h1>
    <form class="search-field" on:submit|preventDefault={search}>
      <input bind:value={mint} disabled={loading} aria-label="Solana token mint address" placeholder="Paste token address" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" />
      <button type="submit" disabled={loading} aria-label={loading ? 'Поиск выполняется' : 'Найти токен'} title="Найти токен">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg>
      </button>
    </form>
    {#if loading}<p class="message" role="status">Собираем данные о токене…</p>{/if}
    {#if error}<p class="message error" role="alert">{error}</p>{/if}
    {#if report}
      <section class="report" aria-label="Отчёт Inspector">
        <div class="report-head">
          <div>
            <p class="eyebrow">INSPECTOR / SOLANA</p>
            <h2>{report.token.name ?? report.token.symbol ?? 'Токен без названия'}</h2>
            {#if report.token.name && report.token.symbol}<p class="symbol">{report.token.symbol}</p>{/if}
          </div>
          <div class="score" class:blocked={report.score.status === 'blocked'}>
            <span>SONAR SCORE</span>
            <strong>{report.score.value == null ? '—' : report.score.value + '/100'}</strong>
            <small>{report.score.status === 'blocked' ? 'Заблокирован' : report.score.status === 'insufficient_data' ? 'Недостаточно данных' : 'Оценка рисков'}</small>
          </div>
        </div>
        <p class="address">{report.mint}</p>
        {#if report.status === 'no_data'}
          <p class="notice">Источники не нашли достаточно данных об этом токене.</p>
        {:else if report.status === 'unavailable'}
          <p class="notice">Источники сейчас недоступны. Повторите поиск позже.</p>
        {:else}
          {#if report.status === 'partial'}<p class="notice">Отчёт неполный: часть данных не удалось получить.</p>{/if}
          <div class="facts">
            <div><span>Цена USD</span><strong>{money(report.selected_pool?.price_usd)}</strong></div>
            <div><span>Ликвидность пула</span><strong>{money(report.selected_pool?.liquidity_usd)}</strong></div>
            <div><span>Площадка</span><strong>{report.selected_pool?.dex ?? 'Нет данных'}</strong></div>
            <div><span>Цена за 5 минут</span><strong>{percent(report.selected_pool?.windows.m5.price_change_pct)}</strong></div>
            <div><span>Объём за 5 минут</span><strong>{money(report.selected_pool?.windows.m5.volume_usd)}</strong></div>
            <div><span>Наблюдавшиеся покупки / продажи за 5 минут</span><strong>{count(report.selected_pool?.windows.m5.observed_buys)} / {count(report.selected_pool?.windows.m5.observed_sells)}</strong></div>
          </div>
          {#if report.selected_pool}<p class="pool">Pool ID: {report.selected_pool.pool_id}</p>{/if}
        {/if}
        {#if report.score.block_reasons.length}
          <div class="reasons"><h3>Причины блокировки</h3>{#each report.score.block_reasons as reason}<p>• {explain(reason)}</p>{/each}</div>
        {/if}
        {#if report.score.missing_evidence.length || report.score.conflicts.length}
          <div class="reasons"><h3>Недостающие или противоречивые данные</h3>{#each [...report.score.missing_evidence, ...report.score.conflicts] as reason}<p>• {explain(reason)}</p>{/each}</div>
        {/if}
        <p class="disclaimer">Предварительная оценка наблюдаемых рисков. Не прогноз роста и не рекомендация к покупке. Время получения отчёта не подтверждает свежесть цены.</p>
      </section>
    {/if}
  </div>
</main>

<style>
  .inspector { display: flex; align-items: center; justify-content: center; min-height: calc(100svh - 108px); box-sizing: border-box; padding: 32px 24px 140px; }
  .inspector.has-report { align-items: flex-start; padding-top: 70px; }
  .search-block { width: min(620px, 100%); }
  h1 { margin: 0 0 28px; color: #ff65ba; font: 400 clamp(10px, 1.1vw, 13px)/2 'Press Start', monospace; text-align: center; text-shadow: 0 0 24px #ff209f35; }
  h1 span { white-space: nowrap; }
  .search-field { display: flex; align-items: center; gap: 12px; padding: 8px; border: 1px solid #ffffff20; border-radius: 18px; background: #252029; box-shadow: 0 12px 40px #09070b25; transition: border-color 250ms, box-shadow 350ms; }
  .search-field:focus-within { border-color: #ff65ba90; box-shadow: 0 0 32px #ff209f12; }
  input { min-width: 0; flex: 1; padding: 12px 14px; border: 0; outline: none; background: transparent; color: #f5edf4; font: 15px/1.5 ui-monospace, monospace; }
  input::placeholder { color: #a99aaf; }
  button { display: grid; place-items: center; flex: none; width: 48px; height: 48px; padding: 12px; border: 0; border-radius: 11px; background: #ff65ba; color: #251221; cursor: pointer; transition: transform 200ms, box-shadow 200ms; }
  button:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 5px 20px #ff65ba55; }
  button:focus-visible { outline: 2px solid #fff; outline-offset: 3px; }
  button:disabled { opacity: .65; cursor: wait; }
  button svg { width: 24px; height: 24px; }
  .message { margin: 18px 8px; color: #d8cada; font: 18px/1.4 'VT323', monospace; }
  .message.error { color: #ff9bbd; }
  .report { margin-top: 28px; padding: 26px; border: 1px solid #ff65ba60; border-radius: 18px; background: #252029; color: #f5edf4; box-shadow: 0 14px 48px #09070b50; animation: appear 350ms ease-out; }
  .report-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
  .eyebrow, .score span { color: #ff65ba; font: 9px/1.6 'Press Start', monospace; }
  .eyebrow { margin: 0 0 15px; }
  h2 { margin: 0; overflow-wrap: anywhere; font: 36px/1.1 'VT323', monospace; }
  .symbol { margin: 4px 0 0; color: #c5b3c9; font: 20px 'VT323', monospace; }
  .score { min-width: 148px; text-align: right; }
  .score strong { display: block; margin: 9px 0 2px; color: #ff65ba; font: 38px/1 'VT323', monospace; }
  .score.blocked strong { color: #ff9bbd; }
  .score small { color: #c5b3c9; font: 17px/1.2 'VT323', monospace; }
  .address, .pool { overflow-wrap: anywhere; color: #a99aaf; font: 12px/1.6 ui-monospace, monospace; }
  .address { margin: 20px 0 24px; }
  .pool { margin: 18px 0 0; }
  .notice { padding: 12px 14px; border: 1px solid #ff65ba40; border-radius: 10px; color: #f2d4e7; font: 18px/1.3 'VT323', monospace; }
  .facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .facts div { min-width: 0; padding: 14px; border: 1px solid #ffffff15; border-radius: 10px; background: #ffffff05; }
  .facts span, .facts strong { display: block; overflow-wrap: anywhere; font: 17px/1.2 'VT323', monospace; }
  .facts span { min-height: 37px; color: #bcaabe; }
  .facts strong { margin-top: 5px; color: #fff; font-size: 22px; }
  .reasons { margin-top: 22px; }
  .reasons h3 { margin: 0 0 8px; color: #ff9bbd; font: 20px 'VT323', monospace; }
  .reasons p { margin: 4px 0; color: #e3d6e5; font: 17px/1.3 'VT323', monospace; }
  .disclaimer { margin: 24px 0 0; padding-top: 18px; border-top: 1px solid #ffffff20; color: #aa98ae; font: 16px/1.3 'VT323', monospace; }
  @keyframes appear { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  @media (max-width: 700px) { .inspector { min-height: calc(100svh - 88px); padding: 24px 20px 112px; } .inspector.has-report { padding-top: 32px; } h1 { max-width: 300px; margin: 0 auto 24px; } input { font-size: 16px; padding-inline: 8px; } .report { padding: 18px; } .facts { grid-template-columns: 1fr; } .facts span { min-height: 0; } .score { min-width: 112px; } .score strong { font-size: 30px; } }
  @media (prefers-reduced-motion: reduce) { .search-field, button { transition: none; } .report { animation: none; } }
</style>
