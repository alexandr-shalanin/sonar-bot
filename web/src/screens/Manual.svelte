<script lang="ts">
  import Candidates from './Candidates.svelte';
  import Inspector from './Inspector.svelte';
  export let page: string;

  let menu: HTMLDialogElement;
  const sections = [
    { id: 'candidates', label: 'Candidates', path: 'M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 12l7-7M16 3h5v5' },
    { id: 'inspector', label: 'Inspector', path: 'M16.5 10a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0ZM15 15l6 6M7 10h6M10 7v6' },
    { id: 'tracked', label: 'Tracked', path: 'M4 4v16h16M8 14l4-5 4 3 4-7' },
    { id: 'account', label: 'Account', path: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2' }
  ];
</script>

<svelte:head><title>{page[0].toUpperCase() + page.slice(1)} — Sonar</title></svelte:head>
<svelte:window on:resize={() => { if (window.innerWidth > 700 && menu?.open) menu.close(); }} />

<div class="workspace">
  <header class="topbar">
    <a class="brand" href="#/" aria-label="Sonar — вернуться на главную">
      <img src="/images/void-cat.png" alt="" width="32" height="32" />
      <span>SONAR<span class="brand-slash">/</span></span>
    </a>

    <nav class="nav-island" aria-label="Разделы Sonar">
      {#each sections as section}
        <a href="#/{section.id}" aria-label={section.label} class:active={page === section.id} aria-current={page === section.id ? 'page' : undefined}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={section.path} /></svg>
          <span class="label"><span>{section.label}</span></span>
        </a>
      {/each}
    </nav>

    <button class="menu-toggle" type="button" aria-label="Открыть меню" aria-haspopup="dialog" on:click={() => menu.showModal()}>
      <span></span><span></span>
    </button>
  </header>

  {#if page === 'candidates'}<Candidates />{/if}
  {#if page === 'inspector'}<Inspector />{/if}

  <dialog bind:this={menu} class="mobile-menu" aria-label="Разделы Sonar">
    <button class="menu-close" type="button" aria-label="Закрыть меню" on:click={() => menu.close()}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
    </button>
    <nav aria-label="Мобильная навигация">
      {#each sections as section, index}
        <a href="#/{section.id}" class:active={page === section.id} aria-current={page === section.id ? 'page' : undefined} style:--index={index} on:click={() => menu.close()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={section.path} /></svg>
          <span>{section.label}</span>
        </a>
      {/each}
    </nav>
  </dialog>
</div>

<style>
  @font-face { font-family: 'Press Start'; src: url('/fonts/press-start-2p.ttf') format('truetype'); font-display: swap; }
  @font-face { font-family: 'VT323'; src: url('/fonts/vt323.ttf') format('truetype'); font-display: swap; }

  .workspace { --pink: #ff65ba; --ease: cubic-bezier(.22, 1, .36, 1); min-height: 100svh; background: linear-gradient(#c4b4cc0b 1px, transparent 1px), linear-gradient(90deg, #c4b4cc0b 1px, transparent 1px), #1d1921; background-size: 32px 32px; color: #f5edf4; }
  .topbar { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; padding: 24px clamp(20px, 4vw, 80px); }
  .brand { display: inline-flex; align-items: center; gap: 12px; width: fit-content; min-height: 48px; color: inherit; font: 10px 'Press Start', monospace; text-decoration: none; white-space: nowrap; }
  .brand img { display: block; object-fit: contain; image-rendering: pixelated; transition: transform 250ms var(--ease); }
  .brand:hover img { transform: translateY(-3px) rotate(-7deg); }
  .brand-slash { margin-left: 5px; color: #ff209f; }
  .nav-island { display: flex; gap: 4px; padding: 6px; border: 1px solid #ffffff14; border-radius: 22px; background: #252029; box-shadow: 0 8px 28px #09070b30; }
  .nav-island a { display: flex; align-items: center; justify-content: center; min-width: 48px; height: 48px; padding: 0 13px; border-radius: 16px; color: #b8acbb; text-decoration: none; transition: color 240ms, background 240ms; }
  .nav-island a:hover { color: #fff2fd; background: #ffffff08; }
  .nav-island a.active { color: var(--pink); background: #ff209f12; }
  .nav-island svg { flex: none; width: 22px; height: 22px; }
  .label { display: grid; grid-template-columns: 0fr; opacity: 0; transform: translateX(-5px); transition: grid-template-columns 480ms var(--ease), opacity 200ms ease, transform 400ms var(--ease); }
  .label > span { overflow: hidden; white-space: nowrap; font: 21px 'VT323', monospace; transition: padding-left 480ms var(--ease); }
  .nav-island:is(:hover, :focus-within) .label { grid-template-columns: 1fr; opacity: 1; transform: translateX(0); transition-delay: 0ms, 100ms, 0ms; }
  .nav-island:is(:hover, :focus-within) .label > span { padding-left: 10px; }
  a:focus-visible, button:focus-visible { outline: 2px solid #51d9fa; outline-offset: 4px; }
  .menu-toggle { display: none; }
  .mobile-menu { position: fixed; inset: 0; width: 100%; max-width: none; height: 100%; max-height: none; margin: 0; padding: 24px; border: 0; background: #1d1921; color: #f5edf4; opacity: 0; transform: translateY(-16px); transition: opacity 300ms ease, transform 450ms var(--ease), display 450ms allow-discrete, overlay 450ms allow-discrete; }
  .mobile-menu[open] { opacity: 1; transform: translateY(0); }
  .mobile-menu::backdrop { background: #1d1921; }
  .menu-close, .menu-toggle { align-items: center; justify-content: center; width: 48px; height: 48px; padding: 12px; border: 1px solid #ffffff18; border-radius: 16px; background: #ffffff05; color: var(--pink); cursor: pointer; }
  .menu-close { position: absolute; right: 20px; top: 24px; display: flex; }
  .menu-close svg { width: 24px; height: 24px; }
  .mobile-menu nav { display: flex; flex-direction: column; justify-content: center; gap: 36px; height: 100%; max-width: 480px; margin: auto; }
  .mobile-menu nav a { display: flex; align-items: center; gap: 20px; padding: 12px 0; color: #b8acbb; font: clamp(36px, 10vw, 56px) 'VT323', monospace; text-decoration: none; opacity: 0; transform: translateY(16px); transition: opacity 220ms, transform 320ms var(--ease), color 200ms; }
  .mobile-menu[open] nav a { opacity: 1; transform: translateY(0); transition-delay: calc(70ms + var(--index) * 60ms); }
  .mobile-menu nav a.active { color: var(--pink); text-shadow: 0 0 24px #ff209f40; }
  .mobile-menu nav svg { width: 30px; height: 30px; flex: none; }
  @starting-style {
    .mobile-menu[open] { opacity: 0; transform: translateY(-16px); }
    .mobile-menu[open] nav a { opacity: 0; transform: translateY(16px); }
  }
  @media (max-width: 700px) {
    .topbar { display: flex; justify-content: space-between; padding: 20px; }
    .nav-island { display: none; }
    .menu-toggle { display: flex; flex-direction: column; gap: 6px; }
    .menu-toggle span { width: 20px; height: 1.5px; background: currentColor; }
  }
  @media (hover: none) and (min-width: 701px) {
    .label { grid-template-columns: 1fr; opacity: 1; transform: none; }
    .label > span { padding-left: 10px; }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; }
  }
</style>
