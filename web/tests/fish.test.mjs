import assert from 'node:assert/strict';
import test from 'node:test';
import { stepFish } from '../src/lib/fish.ts';

const bounds = { width: 600, height: 400 };
const swimmer = () => ({ x: 300, y: 200, vx: -20, vy: 0, angle: Math.PI, speed: 24, turnIn: 2, size: 40 });

test('a nearby pointer makes a fish swim away, while distant fish keep their course', () => {
  const close = swimmer();
  const far = swimmer();
  for (let frame = 0; frame < 30; frame++) {
    stepFish(close, 1 / 30, bounds, { x: 270, y: 200 });
    stepFish(far, 1 / 30, bounds, { x: 20, y: 20 });
  }
  assert.ok(close.x > 310 && close.vx > 0);
  assert.ok(far.x < 290 && far.vx < 0);
});

test('fish remain finite and within the reef at walls, corners and exact pointer overlap', () => {
  for (const point of [{ x: 0, y: 0 }, { x: 600, y: 400 }, { x: 300, y: 200 }]) {
    const fish = { ...swimmer(), ...point, turnIn: 0 };
    for (let frame = 0; frame < 180; frame++) {
      stepFish(fish, frame === 0 ? 10 : 1 / 30, bounds, point, () => .25);
      assert.ok(Number.isFinite(fish.x + fish.y + fish.vx + fish.vy));
      assert.ok(fish.x >= 26 && fish.x <= 574 && fish.y >= 26 && fish.y <= 374);
    }
  }
});

test('random turns give fish different paths', () => {
  const left = { ...swimmer(), turnIn: 0 };
  const right = { ...left };
  for (let frame = 0; frame < 60; frame++) {
    stepFish(left, 1 / 30, bounds, null, () => .1);
    stepFish(right, 1 / 30, bounds, null, () => .9);
  }
  assert.ok(Math.abs(left.y - right.y) > 20);
});

test('fish turn back into open water instead of lingering against a wall', () => {
  const fish = { ...swimmer(), x: 27, turnIn: 20 };
  for (let frame = 0; frame < 150; frame++) stepFish(fish, 1 / 30, bounds, null);
  assert.ok(fish.x > 100 && fish.vx > 0);
});
