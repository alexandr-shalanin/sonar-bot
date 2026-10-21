export type Point = { x: number; y: number };
export type FishMotion = Point & {
  vx: number; vy: number; angle: number; speed: number; turnIn: number; size: number;
};

export function stepFish(fish: FishMotion, elapsed: number, bounds: { width: number; height: number }, pointer: Point | null, random = Math.random) {
  const dt = Math.min(elapsed, .05);
  fish.turnIn -= dt;
  if (fish.turnIn <= 0) {
    fish.angle += (random() - .5) * 2.4;
    fish.turnIn = 1.5 + random() * 3;
  }
  let vx = Math.cos(fish.angle) * fish.speed;
  let vy = Math.sin(fish.angle) * fish.speed * .65;
  if (pointer) {
    const dx = fish.x - pointer.x;
    const dy = fish.y - pointer.y;
    const distance = Math.hypot(dx, dy);
    if (distance < 150) {
      const angle = distance < 1 ? fish.angle : Math.atan2(dy, dx);
      const speed = fish.speed + 80 * (1 - distance / 150);
      vx = Math.cos(angle) * speed;
      vy = Math.sin(angle) * speed;
      fish.angle = angle;
    }
  }
  const pad = fish.size / 2 + 6;
  const courseX = vx;
  const courseY = vy;
  if (fish.x < pad + 25) vx = Math.abs(vx) + 12;
  if (fish.x > bounds.width - pad - 25) vx = -Math.abs(vx) - 12;
  if (fish.y < pad + 20) vy = Math.abs(vy) + 10;
  if (fish.y > bounds.height - pad - 20) vy = -Math.abs(vy) - 10;
  if (vx !== courseX || vy !== courseY) fish.angle = Math.atan2(vy / .65, vx);
  const turn = 1 - Math.exp(-dt * 4);
  fish.vx += (vx - fish.vx) * turn;
  fish.vy += (vy - fish.vy) * turn;
  fish.x = Math.max(pad, Math.min(bounds.width - pad, fish.x + fish.vx * dt));
  fish.y = Math.max(pad, Math.min(bounds.height - pad, fish.y + fish.vy * dt));
}

export function animateOcean(ocean: HTMLElement, seeds: (Point & { size: number })[]) {
  const nodes = Array.from(ocean.querySelectorAll<HTMLElement>('.fish-path'));
  const bounds = { width: ocean.clientWidth, height: ocean.clientHeight };
  const fish = seeds.map(seed => {
    const angle = Math.random() * Math.PI * 2;
    const speed = 18 + Math.random() * 15;
    return { x: seed.x / 100 * bounds.width, y: seed.y / 100 * bounds.height,
      vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed * .65,
      angle, speed, turnIn: Math.random() * 3, size: seed.size };
  });
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  let pointer: Point | null = null;
  let inView = false;
  let frame = 0;
  let last = 0;

  function draw() {
    fish.forEach((swimmer, index) => {
      const facing = swimmer.vx < 0 ? -1 : 1;
      const tilt = Math.max(-25, Math.min(25, Math.atan2(swimmer.vy, Math.abs(swimmer.vx)) * 180 / Math.PI));
      nodes[index].style.transform = `translate(${Math.round(swimmer.x - swimmer.size / 2)}px, ${Math.round(swimmer.y - swimmer.size / 3)}px) rotate(${tilt * facing}deg) scaleX(${facing})`;
    });
  }
  nodes.forEach(node => { node.style.left = '0'; node.style.top = '0'; });
  draw();

  function tick(now: number) {
    if (!last) last = now;
    const elapsed = (now - last) / 1000;
    if (elapsed >= 1 / 30) {
      fish.forEach(swimmer => stepFish(swimmer, elapsed, bounds, pointer));
      draw();
      last = now;
    }
    frame = requestAnimationFrame(tick);
  }
  function syncMotion() {
    cancelAnimationFrame(frame);
    last = 0;
    const active = inView && !document.hidden && !reducedMotion.matches;
    ocean.classList.toggle('motion-paused', !active);
    if (!active) pointer = null;
    if (active) frame = requestAnimationFrame(tick);
  }
  function movePointer(event: PointerEvent) {
    if (event.pointerType === 'touch') return;
    const rect = ocean.getBoundingClientRect();
    pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }
  function clearPointer() { pointer = null; }
  const visibility = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; syncMotion(); });
  visibility.observe(ocean);
  const resize = new ResizeObserver(() => {
    const width = ocean.clientWidth;
    const height = ocean.clientHeight;
    fish.forEach(swimmer => { swimmer.x *= width / bounds.width; swimmer.y *= height / bounds.height; });
    bounds.width = width;
    bounds.height = height;
    fish.forEach(swimmer => stepFish(swimmer, 0, bounds, null));
    pointer = null;
    draw();
  });
  resize.observe(ocean);
  ocean.addEventListener('pointermove', movePointer);
  ocean.addEventListener('pointerleave', clearPointer);
  document.addEventListener('visibilitychange', syncMotion);
  reducedMotion.addEventListener('change', syncMotion);
  return { destroy() {
    cancelAnimationFrame(frame);
    visibility.disconnect();
    resize.disconnect();
    ocean.removeEventListener('pointermove', movePointer);
    ocean.removeEventListener('pointerleave', clearPointer);
    document.removeEventListener('visibilitychange', syncMotion);
    reducedMotion.removeEventListener('change', syncMotion);
  } };
}
