<script lang="ts">
  import { animateOcean } from '../lib/fish';

  const titleLayers = ['title-base', 'glitch-copy glitch-cyan', 'glitch-copy glitch-yellow', 'glitch-copy glitch-red'];
  const fish = [
    { x: 17, y: 27, size: 44, color: '#ff339e', stripe: '#ffe65a' },
    { x: 79, y: 24, size: 36, color: '#51d9fa', stripe: '#ff75cc' },
    { x: 31, y: 69, size: 32, color: '#ffe65a', stripe: '#ff554e' },
    { x: 72, y: 65, size: 48, color: '#ff554e', stripe: '#ffe65a' },
    { x: 36, y: 45, size: 30, color: '#51d9fa', stripe: '#ffe65a' },
    { x: 87, y: 48, size: 34, color: '#ff339e', stripe: '#51d9fa' },
    { x: 10, y: 54, size: 28, color: '#51d9fa', stripe: '#ff554e' },
    { x: 61, y: 17, size: 30, color: '#ffe65a', stripe: '#ff339e' },
    { x: 55, y: 77, size: 28, color: '#ff75cc', stripe: '#51d9fa' },
    { x: 91, y: 75, size: 34, color: '#b88cff', stripe: '#ffe65a' },
    { x: 24, y: 16, size: 32, color: '#ff554e', stripe: '#51d9fa' },
    { x: 48, y: 55, size: 38, color: '#ffe65a', stripe: '#ff75cc' },
    { x: 67, y: 40, size: 30, color: '#b88cff', stripe: '#51d9fa' },
    { x: 19, y: 83, size: 36, color: '#ff339e', stripe: '#ffe65a' }
  ];

  function revealIdea(node: HTMLElement) {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    node.classList.add('reveal-ready');
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        node.classList.add('is-visible');
        observer.disconnect();
      }
    }, { threshold: .15 });
    observer.observe(node);
    return { destroy() { observer.disconnect(); } };
  }
</script>

<svelte:head><title>Sonar — below the surface</title></svelte:head>

<a class="skip-link" href="#main">Skip to content</a>
<div class="site-frame">
  <header class="site-header">
    <a class="wordmark" href="#main" aria-label="Sonar home">
      <img src="/images/void-cat.png" alt="" width="30" height="30" />
      <span>SONAR<span class="wordmark-slash">/</span></span>
    </a>
    <nav aria-label="Main navigation">
      <div class="socials">
        <button class="icon-link unavailable" type="button" disabled aria-label="Discord — coming soon" title="Discord — coming soon">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M19.7 5.3a18 18 0 0 0-4.5-1.4l-.6 1.2a16.5 16.5 0 0 0-5.2 0l-.6-1.2a18 18 0 0 0-4.5 1.4C1.5 9.5.8 13.6 1.2 17.7a18 18 0 0 0 5.5 2.8l1.1-1.8-1.7-.9.4-.3a13 13 0 0 0 11 0l.4.3-1.7.9 1.1 1.8a18 18 0 0 0 5.5-2.8c.5-4.8-.8-8.9-3.1-12.4ZM8.2 15c-1 0-1.8-.9-1.8-2s.8-2 1.8-2 1.8.9 1.8 2-.8 2-1.8 2Zm7.6 0c-1 0-1.8-.9-1.8-2s.8-2 1.8-2 1.8.9 1.8 2-.8 2-1.8 2Z" /></svg>
        </button>
        <a class="icon-link" href="https://github.com/alexandr-shalanin" target="_blank" rel="noopener noreferrer" aria-label="Alexandr on GitHub (opens in a new tab)">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 1a11 11 0 0 0-3.5 21.4c.6.1.8-.2.8-.5v-2c-3.4.7-4.1-1.4-4.1-1.4-.6-1.4-1.4-1.8-1.4-1.8-1.1-.8.1-.8.1-.8 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.7.4-1.3.7-1.6-2.7-.3-5.6-1.4-5.6-6.1 0-1.3.5-2.5 1.2-3.3-.1-.3-.5-1.6.1-3.3 0 0 1-.3 3.4 1.3a11.6 11.6 0 0 1 6.2 0c2.4-1.6 3.4-1.3 3.4-1.3.6 1.7.2 3 .1 3.3.8.8 1.2 2 1.2 3.3 0 4.7-2.9 5.8-5.6 6.1.4.4.8 1.1.8 2.2v3.2c0 .3.2.6.8.5A11 11 0 0 0 12 1Z" /></svg>
        </a>
      </div>
      <a class="text-link" href="#how-to-use">How to use</a>
      <button class="start-link" type="button" disabled title="The app is in development">Let’s start <span aria-hidden="true">↗</span></button>
    </nav>
  </header>

  <main id="main">
    <section class="hero" aria-labelledby="sonar-title">
      <div class="masthead">
        <div class="masthead-note"><span class="tiny-cross" aria-hidden="true"></span> A PERSONAL SOLANA PROJECT</div>
        <h1 id="sonar-title" aria-label="SONAR">
          {#each titleLayers as layer}
            <span class="title-surface {layer}" aria-hidden="true">{#each [...'SONAR'] as letter}<span class="title-letter">{letter}</span>{/each}</span>
          {/each}
        </h1>
      </div>
      <div class="ocean-stage">
        <div class="ocean motion-paused" use:animateOcean={fish}>
          <img class="reef" src="/images/ocean-reef.png" alt="" width="1536" height="1024" fetchpriority="high" />
          <div class="ocean-scanlines"></div>
          {#each fish as swimmer}
            <div class="fish-path" aria-hidden="true" style:left="{swimmer.x}%" style:top="{swimmer.y}%" style:--tail-delay="{-swimmer.x / 100}s">
              <svg width={swimmer.size} height={swimmer.size * 2 / 3} viewBox="0 0 24 16" shape-rendering="crispEdges">
                <path class="fish-tail" fill={swimmer.color} d="M0 4h3v2h4v4H3v2H0Z" />
                <path fill={swimmer.color} d="M7 6V4h4V2h7v2h4v2h2v4h-2v2h-4v2h-7v-2H7Z" />
                <path class="fish-fin" fill={swimmer.stripe} d="M11 4h7v2h-7zM7 6h4v2H7zM12 8h3v4h-3z" />
                <path fill="#211525" d="M19 6h2v2h-2z" />
              </svg>
            </div>
          {/each}
          <div class="cat-drift">
            <div class="mascot" role="img" aria-label="Black pixel cat drifting in the ocean">
              <span class="cat-speech" aria-hidden="true">blub?</span>
              <div class="cat-body">
                <img src="/images/void-cat.png" alt="" width="1254" height="1254" />
                <span class="breath-bubbles" aria-hidden="true"><span class="bubble"></span><span class="bubble"></span><span class="bubble"></span></span>
              </div>
            </div>
          </div>
        </div>
        <div class="intro-note">
          <h2>Your automatic bot.</h2>
          <p>For you and under your<br class="desktop-break" /> complete control.</p>
          <div class="free-label"><span aria-hidden="true"></span> Free 24/7</div>
          <a class="dive-link" href="#how-to-use"><span class="pixel-arrow" aria-hidden="true">↓</span> A LITTLE BELOW THE SURFACE</a>
          <div class="friend pop-cat" role="img" aria-label="Pop Cat peeking above the pink panel">
            <span class="friend-speech" aria-hidden="true">pop!</span>
            <img src="/images/pop-cat.png" alt="" loading="lazy" />
            <span class="pop-pixels" aria-hidden="true"></span>
          </div>
        </div>
      </div>
    </section>

    <section class="about" id="how-to-use" aria-labelledby="about-title" use:revealIdea>
      <div class="about-heading">
        <span class="section-index">01 / THE IDEA</span>
        <h2 id="about-title">A little<br /> about Sonar.</h2>
        <div class="friend alien-cat" role="img" aria-label="Curious green pixel cat peeking out">
          <span class="friend-speech" aria-hidden="true">looking closer.</span>
          <span class="scout-window"><img src="/images/alien-cat.png" alt="" loading="lazy" /></span>
        </div>
      </div>
      <div class="about-copy">
        <p>Sonar is being built to discover new Solana tokens, check their risks and rank the candidates worth a closer look.</p>
        <p><strong>Manual</strong> will give you recommendations, without placing trades. <strong>Automatic</strong> is being built around fixed safety and spending limits. You stay in control.</p>
        <span class="development-note"><span aria-hidden="true"></span> A personal project, currently in development.</span>
      </div>
    </section>
  </main>
  <footer>
    <span>SONAR<span class="footer-slash">/</span></span>
    <a class="surface-link" href="#main">
      <span>BACK TO THE SURFACE <span aria-hidden="true">↑</span></span>
    </a>
  </footer>
</div>

<style>
  @font-face { font-family: 'Press Start'; src: url('/fonts/press-start-2p.ttf') format('truetype'); font-weight: 400; font-display: swap; }
  @font-face { font-family: 'VT323'; src: url('/fonts/vt323.ttf') format('truetype'); font-weight: 400; font-display: swap; }

  :global(*) { box-sizing: border-box; }
  :global(html) { scroll-behavior: smooth; scroll-padding-top: 20px; }
  :global(body) { margin: 0; background: #1d1921; color: #f5edf4; font-family: 'VT323', monospace; -webkit-font-smoothing: none; }
  :global(button), :global(a) { -webkit-tap-highlight-color: transparent; }
  :global(button) { font: inherit; }
  :global(a) { color: inherit; text-decoration: none; }
  :global(button:not(:disabled)), :global(a) { cursor: pointer; }
  :global(button:focus-visible), :global(a:focus-visible) { outline: 3px solid #51d9fa; outline-offset: 6px; }
  :global(::selection) { color: #211525; background: #ff70c4; }

  .site-frame { --pixel-wave: polygon(0 50%, 6% 50%, 6% 25%, 13% 25%, 13% 0, 21% 0, 21% 25%, 27% 25%, 27% 75%, 35% 75%, 35% 50%, 43% 50%, 43% 25%, 51% 25%, 51% 0, 58% 0, 58% 50%, 66% 50%, 66% 75%, 74% 75%, 74% 25%, 82% 25%, 82% 0, 88% 0, 88% 50%, 94% 50%, 94% 75%, 100% 75%, 100% 100%, 0 100%); --pink: #ff209f; --muted: #b8acbb; width: 100%; min-height: 100svh; background-color: #1d1921; background-image: linear-gradient(#c4b4cc0b 1px, transparent 1px), linear-gradient(90deg, #c4b4cc0b 1px, transparent 1px); background-size: 32px 32px; }
  .skip-link { position: absolute; z-index: 10; left: 24px; top: -70px; background: #ff70c4; color: #211525; padding: 12px; font-size: 22px; }
  .skip-link:focus { top: 24px; }
  .site-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 17px clamp(24px, 4vw, 80px); }
  .wordmark { display: flex; align-items: center; gap: 12px; font-family: 'Press Start', monospace; font-size: 10px; }
  .wordmark img { object-fit: contain; image-rendering: pixelated; transition: transform 160ms steps(3); }
  .wordmark:hover img { transform: translateY(-4px) rotate(-8deg); }
  .wordmark-slash { margin-left: 5px; color: var(--pink); }
  nav { display: flex; align-items: center; gap: 30px; font-size: 21px; }
  .socials { display: flex; align-items: center; gap: 8px; padding-right: 20px; }
  .icon-link { display: grid; place-items: center; width: 40px; height: 40px; color: #e9dfea; background: none; border: 0; padding: 9px; transition: color 120ms, transform 120ms steps(2); }
  .icon-link svg { width: 22px; height: 22px; }
  .icon-link:hover:not(:disabled) { color: #51d9fa; transform: translateY(-3px); }
  .unavailable { color: #b8acbb; cursor: not-allowed; }
  .text-link { padding: 10px 0; white-space: nowrap; }
  .text-link:hover { color: #ff70c4; text-decoration: underline; text-underline-offset: 6px; }
  .start-link { display: flex; align-items: center; gap: 21px; min-height: 40px; padding: 4px 13px; background: var(--pink); color: #211525; border: 0; box-shadow: 3px 3px #92265f; cursor: not-allowed; white-space: nowrap; }
  .start-link span { font-family: monospace; font-size: 21px; }

  .masthead { padding: 23px 24px 28px; text-align: center; }
  .masthead-note { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 18px; color: var(--muted); font-size: 16px; letter-spacing: 1.4px; }
  .tiny-cross { display: inline-block; width: 9px; height: 9px; background: #51d9fa; clip-path: polygon(33% 0, 66% 0, 66% 33%, 100% 33%, 100% 66%, 66% 66%, 66% 100%, 33% 100%, 33% 66%, 0 66%, 0 33%, 33% 33%); }
  h1 { position: relative; width: fit-content; margin: 0 auto; padding-top: 10px; font: 400 clamp(70px, 17.5vw, 320px)/1.12 'Press Start', monospace; letter-spacing: -.075em; color: var(--pink); filter: drop-shadow(3px 4px 0 #642342); }
  .title-surface { display: flex; perspective: 3em; }
  .title-letter { display: block; width: .925em; background-image: repeating-linear-gradient(0deg, transparent 0 2px, #28112190 2px 3px), repeating-linear-gradient(90deg, #ff5bbd 0 2px, #e81b94 2px 3px); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .title-letter:first-child { transform: translateZ(-.15em) rotateY(-24deg) scaleY(.86); opacity: .72; }
  .title-letter:nth-child(2) { transform: translateZ(-.04em) rotateY(-12deg) scaleY(.96); opacity: .92; }
  .title-letter:nth-child(4) { transform: translateZ(-.04em) rotateY(12deg) scaleY(.96); opacity: .92; }
  .title-letter:last-child { transform: translateZ(-.15em) rotateY(24deg) scaleY(.86); opacity: .72; }
  .glitch-copy { position: absolute; top: 10px; left: 0; opacity: 0; pointer-events: none; animation: title-glitch 6.4s steps(1, end) infinite; }
  .glitch-copy .title-letter { background: none; -webkit-text-fill-color: currentColor; }
  .glitch-cyan { color: #51d9fa; }
  .glitch-yellow { color: #ffe65a; animation-delay: -0.08s; }
  .glitch-red { color: #ff554e; animation: title-tear 7.6s steps(1, end) -2.8s infinite; }

  .ocean-stage { position: relative; display: grid; grid-template-columns: minmax(0, 1.8fr) minmax(0, 1fr); min-height: clamp(460px, 38vw, 650px); }
  .ocean-stage::before { position: absolute; z-index: 3; inset-inline: 0; top: 0; height: 28px; content: ''; background: #1d1921; clip-path: var(--pixel-wave); transform: rotate(180deg); pointer-events: none; }
  .ocean { position: relative; overflow: hidden; min-height: inherit; background: #142532; }
  .reef { position: absolute; inset: 0; display: block; width: 100%; height: 100%; object-fit: cover; object-position: center 58%; image-rendering: pixelated; }
  .ocean-scanlines { position: absolute; inset: 0; opacity: .1; background: repeating-linear-gradient(0deg, #201222 0 1px, transparent 1px 4px); pointer-events: none; }
  .intro-note { position: relative; display: flex; flex-direction: column; align-items: flex-start; justify-content: center; padding: 48px clamp(28px, 4vw, 80px) 85px; background: #ff65ba; color: #271322; }
  .intro-note h2 { margin: 0 0 24px; max-width: 390px; font: 400 clamp(20px, 1.8vw, 30px)/1.55 'Press Start', monospace; letter-spacing: -.7px; }
  .intro-note p { margin: 0; font-size: clamp(27px, 2.4vw, 36px); line-height: 1.1; }
  .free-label { display: flex; align-items: center; gap: 10px; margin-top: 28px; padding: 4px 12px 5px; color: #271322; background: #ffe65a; font-size: 28px; }
  .free-label > span { width: 6px; height: 6px; background: currentColor; }
  .dive-link { display: flex; align-items: center; gap: 11px; max-width: 240px; margin-top: 43px; padding-block: 8px; font-size: 15px; letter-spacing: .8px; line-height: 1.15; }
  .pixel-arrow { display: inline-block; flex-shrink: 0; font: 28px/1 'VT323', monospace; transition: transform 150ms steps(3); }
  .dive-link:hover .pixel-arrow { transform: translateY(5px); }
  .cat-drift { position: absolute; z-index: 2; left: 48%; top: 19%; width: clamp(125px, 12vw, 195px); animation: drift 12s ease-in-out infinite alternate; }
  .mascot { position: relative; display: block; width: 100%; border: 0; background: transparent; padding: 0; }
  .cat-body { position: relative; transform: rotate(12deg); transition: transform 240ms steps(4); }
  .mascot img { display: block; width: 100%; height: auto; image-rendering: pixelated; }
  .mascot:hover .cat-body { transform: translateY(-15px) rotate(-7deg); }
  .cat-speech, .friend-speech { position: absolute; z-index: 3; top: -34px; right: -20px; padding: 4px 11px 7px; color: #241526; background: #ffe65a; font-size: 24px; line-height: 1; white-space: nowrap; opacity: 0; transform: translateY(5px); transition: opacity 120ms, transform 120ms steps(2); pointer-events: none; }
  .cat-speech::after, .friend-speech::after { position: absolute; bottom: -7px; left: 12px; width: 7px; height: 7px; content: ''; background: inherit; }
  .mascot:hover .cat-speech, .friend:hover .friend-speech { opacity: 1; transform: translateY(0); }
  .fish-path { position: absolute; pointer-events: none; }
  .fish-path svg { display: block; filter: drop-shadow(2px 2px 0 #241526); }
  .fish-tail { transform-origin: 7px 8px; animation: tail-flick .32s steps(2, end) var(--tail-delay) infinite alternate; }
  .fish-fin { transform-origin: 12px 8px; animation: fin-flick .6s steps(2, end) var(--tail-delay) infinite alternate; }
  .breath-bubbles { position: absolute; left: 39%; top: 51%; pointer-events: none; }
  .bubble { position: absolute; border: 2px solid #a0edff; width: 6px; height: 6px; opacity: 0; animation: bubble-up 7s linear infinite; }
  .bubble:nth-child(2) { width: 8px; height: 8px; animation-delay: .35s; }
  .bubble:nth-child(3) { width: 5px; height: 5px; animation-delay: .7s; }
  .ocean.motion-paused :is(.cat-drift, .bubble, .fish-tail, .fish-fin) { animation-play-state: paused; }

  .friend { border: 0; padding: 0; background: none; }
  .friend img { display: block; width: 100%; height: auto; image-rendering: pixelated; transition: transform 180ms steps(3); }
  .pop-cat { position: absolute; right: 48px; bottom: 0; width: clamp(68px, 7vw, 112px); }
  .pop-cat img { width: 160%; max-width: none; margin-left: -30%; margin-bottom: -28%; transform-origin: bottom center; }
  .pop-cat:hover img { transform: scale(1.08, 1.16); }
  .pop-cat .friend-speech { top: -42px; right: 8px; background: #51d9fa; }
  .pop-pixels { position: absolute; width: 5px; height: 5px; left: -12px; top: 5px; background: #ffe65a; box-shadow: -6px 22px #51d9fa, 26px -19px #ff554e, 93px -8px #ffe65a; opacity: 0; transition: opacity 120ms; }
  .pop-cat:hover .pop-pixels { opacity: 1; }

  .about { position: relative; display: grid; grid-template-columns: minmax(260px, .8fr) minmax(0, 1.2fr); gap: clamp(40px, 8vw, 160px); padding: 80px clamp(28px, 8vw, 160px) 72px; background: #26202c; }
  .about::before { position: absolute; z-index: 3; inset-inline: 0; top: -28px; height: 28px; content: ''; background: #26202c; clip-path: var(--pixel-wave); pointer-events: none; }
  @media (prefers-reduced-motion: no-preference) {
    .about:global(.reveal-ready) :is(.section-index, h2, .about-copy p, .development-note) { opacity: 0; transform: translateY(20px); }
    .about:global(.reveal-ready):global(.is-visible) :is(.section-index, h2, .about-copy p, .development-note) { opacity: 1; transform: translateY(0); transition: opacity 650ms ease var(--reveal-delay, 0ms), transform 650ms cubic-bezier(.2, .7, .2, 1) var(--reveal-delay, 0ms); }
    .about:global(.reveal-ready) h2 { --reveal-delay: 80ms; }
    .about:global(.reveal-ready) .about-copy p:first-child { --reveal-delay: 140ms; }
    .about:global(.reveal-ready) .about-copy p:nth-child(2) { --reveal-delay: 220ms; }
    .about:global(.reveal-ready) .development-note { --reveal-delay: 300ms; }
  }
  .about-heading { position: relative; padding-bottom: 115px; }
  .section-index { display: inline-block; color: #b8acbb; font-size: 16px; letter-spacing: 1px; }
  .about h2 { margin: 24px 0 0; color: #ff70c4; font: 400 clamp(22px, 2.2vw, 32px)/1.6 'Press Start', monospace; letter-spacing: -.6px; }
  .about-copy { align-self: center; }
  .about-copy p { margin: 0 0 20px; color: #e1d8e4; font-size: clamp(25px, 2.1vw, 32px); line-height: 1.24; }
  .about-copy strong { color: #fff2fd; font-weight: 400; text-decoration: underline; text-decoration-color: #ff209f; text-underline-offset: 5px; }
  .development-note { display: flex; align-items: center; gap: 9px; margin-top: 27px; color: #bbacc1; font-size: 19px; }
  .development-note > span { flex: 0 0 5px; width: 5px; height: 5px; background: #51d9fa; }
  .alien-cat { position: absolute; width: 97px; bottom: -4px; left: 8px; }
  .scout-window { display: block; height: 89px; overflow: hidden; border-bottom: 3px solid #ff209f; }
  .alien-cat img { transform: translateY(20px); }
  .alien-cat:hover img { transform: translateY(0); }
  .alien-cat .friend-speech { left: 108px; right: auto; top: 1px; background: #bdf27b; font-size: 22px; }
  .alien-cat .friend-speech::after { left: -7px; top: 10px; bottom: auto; }

  footer { position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; min-height: 155px; padding: 32px clamp(28px, 8vw, 160px); color: #b8acbb; font-size: 15px; letter-spacing: 1px; }
  footer > span { font: 400 10px 'Press Start', monospace; padding-bottom: 5px; }
  .footer-slash { margin-left: 6px; color: var(--pink); }
  .surface-link { padding: 13px 0; color: #ffe65a; }
  .surface-link:hover { color: #ff70c4; }
  .surface-link > span > span { margin-left: 7px; font-size: 23px; }

  @keyframes title-glitch {
    0%, 90%, 94%, 97%, 100% { opacity: 0; }
    91% { opacity: .9; clip-path: inset(14% 0 63%); transform: translate(5px, -2px); }
    92% { opacity: .9; clip-path: inset(60% 0 18%); transform: translate(-4px, 2px); }
    95% { opacity: .8; clip-path: inset(38% 0 42%); transform: translate(3px, 1px); }
    96% { opacity: .8; clip-path: inset(76% 0 8%); transform: translate(-3px, -1px); }
  }
  @keyframes title-tear {
    0%, 83%, 87%, 100% { opacity: 0; transform: none; }
    84% { opacity: .8; clip-path: inset(28% 0 57%); transform: translateX(-7px) skewX(-4deg); }
    85% { opacity: .8; clip-path: inset(52% 0 29%); transform: translateX(5px) skewX(3deg); }
    86% { opacity: .6; clip-path: inset(8% 0 82%); transform: translateX(-3px); }
  }
  @keyframes tail-flick { to { transform: scaleX(.55); } }
  @keyframes fin-flick { to { transform: scaleY(.7); } }
  @keyframes drift { 0% { transform: translate(-10px, 2px) rotate(-4deg); } 50% { transform: translate(12px, 21px) rotate(3deg); } 100% { transform: translate(-8px, 44px) rotate(-2deg); } }
  @keyframes bubble-up {
    0% { opacity: 0; transform: translate(0, 0); }
    2% { opacity: .8; }
    16% { opacity: .7; transform: translate(-10px, -65px); }
    32% { opacity: 0; transform: translate(5px, -140px); }
    33%, 100% { opacity: 0; transform: translate(5px, -140px); }
  }

  @media (max-width: 1000px) {
    nav { gap: 22px; }
    .ocean-stage { grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); }
    .intro-note { padding: 38px 27px 95px; }
    .intro-note h2 { font-size: 20px; }
    .intro-note p { font-size: 27px; }
    .dive-link { font-size: 13px; max-width: 175px; }
    .about { grid-template-columns: minmax(220px, .8fr) minmax(0, 1.2fr); padding: 60px 40px; gap: 45px; }
    .about h2 { font-size: 23px; }
    .about-copy p { font-size: 26px; }
    .development-note { font-size: 18px; line-height: 1.15; }
  }
  @media (max-width: 700px) {
    .site-header { padding: 12px 17px; gap: 12px; }
    .wordmark > span { display: none; }
    .wordmark img { width: 28px; height: 28px; }
    nav { gap: 9px; font-size: 17px; }
    .socials { gap: 0; padding-right: 6px; }
    .icon-link { width: 32px; height: 44px; padding: 6px; }
    .start-link { gap: 8px; padding: 4px 9px; }
    .start-link span { font-size: 17px; }
    .masthead { padding: 20px 12px 24px; }
    .masthead-note { font-size: 13px; letter-spacing: .9px; margin-bottom: 17px; }
    h1 { font-size: 19vw; line-height: 1.15; filter: drop-shadow(2px 3px 0 #642342); }
    .ocean-stage { grid-template-columns: 1fr; min-height: 0; }
    .ocean { min-height: clamp(350px, 92vw, 520px); }
    .ocean::after { position: absolute; z-index: 3; inset-inline: 0; bottom: -1px; height: 28px; content: ''; background: #ff65ba; clip-path: var(--pixel-wave); pointer-events: none; }
    .cat-drift { width: clamp(105px, 29vw, 160px); left: 49%; top: 17%; }
    .intro-note { padding: 34px 26px 36px; min-height: 300px; }
    .intro-note h2 { max-width: 350px; font-size: 20px; margin-bottom: 18px; }
    .intro-note p { font-size: 28px; max-width: 290px; }
    .free-label { font-size: 26px; margin-top: 22px; }
    .dive-link { font-size: 13px; margin-top: 28px; max-width: calc(100% - 95px); }
    .pop-cat { width: 82px; right: 36px; }
    .desktop-break { display: none; }
    .about { grid-template-columns: 1fr; padding: 42px 26px; gap: 30px; }
    .about-heading { padding-bottom: 0; min-height: 115px; padding-right: 92px; }
    .about h2 { font-size: 22px; margin-top: 17px; }
    .about h2 br { display: none; }
    .alien-cat { left: auto; right: 0; bottom: 0; width: 78px; }
    .scout-window { height: 73px; }
    .alien-cat .friend-speech { top: -30px; left: auto; right: 0; font-size: 20px; }
    .alien-cat .friend-speech::after { left: auto; right: 15px; top: auto; bottom: -7px; }
    .about-copy p { font-size: 26px; }
    .development-note { margin-top: 23px; font-size: 18px; }
    footer { padding: 32px 24px; min-height: 170px; font-size: 12px; letter-spacing: .3px; }
    footer > span { font-size: 8px; }
    .surface-link { max-width: 145px; line-height: 1.1; }
    .surface-link > span > span { margin-left: 0; font-size: 20px; }
  }
  @media (max-width: 360px) {
    .wordmark { display: none; }
    nav { width: 100%; justify-content: space-between; gap: 6px; font-size: 16px; }
    .socials { padding-right: 4px; }
    .icon-link { width: 28px; }
    .site-header { padding-inline: 14px; }
    .masthead-note { font-size: 12px; }
    .about h2 { font-size: 20px; }
    .intro-note { padding-inline: 22px; }
  }
  @media (prefers-reduced-motion: reduce) {
    :global(html) { scroll-behavior: auto; }
    .glitch-copy, .cat-drift, .bubble, .fish-tail, .fish-fin { animation: none; }
    .bubble { display: none; }
    .cat-body, .cat-speech, .friend-speech, .friend img, .pop-pixels, .wordmark img, .icon-link, .pixel-arrow { transition: none; }
  }
</style>
