// auto-saga mod — willSpeak 单元测试（与生产源同步的 verbatim 副本）
//
// 生产代码位于 mods/auto-saga/static/auto-saga-chat.js 的 IIFE 内无法直接 import，
// 故本测试文件以 verbatim 副本形式固定实现，顶部注明「与生产源同步」。
// 参考 mods/mobile-chat 的 textBubbleParts 单测风格。
// 跑测：node --test mods/auto-saga/static/test_will_speak.mjs

import test from 'node:test';
import assert from 'node:assert/strict';

// === 与生产源同步：speakProbability / willSpeak ===
function speakProbability(persona, opts) {
  const o = opts || {};
  let p = 0.55;
  const text = String(persona || '');
  if (/沉默|寡言|高冷|冷淡|内向/.test(text)) p -= 0.25;
  if (/健谈|热情|话痨|外向|活泼/.test(text)) p += 0.25;
  if (/多疑|谨慎|警惕/.test(text)) p -= 0.1;
  if (o.addressed) p += 0.4;
  if (typeof o.trust === 'number') p += (o.trust - 50) / 200;
  return Math.max(0.05, Math.min(0.95, p));
}

function willSpeak(persona, opts, rng) {
  const r = typeof rng === 'function' ? rng : Math.random;
  return r() < speakProbability(persona, opts);
}
// === 同步块结束 ===

test('基线概率为 0.55', () => {
  assert.equal(speakProbability(''), 0.55);
});

test('沉默型性格降低发言概率', () => {
  assert.ok(speakProbability('沉默寡言') < 0.55);
});

test('健谈型性格提高发言概率', () => {
  assert.ok(speakProbability('健谈热情') > 0.55);
});

test('被点名显著提高概率', () => {
  assert.ok(speakProbability('沉默', { addressed: true }) > speakProbability('沉默'));
});

test('信任值影响概率', () => {
  assert.ok(speakProbability('', { trust: 100 }) > speakProbability('', { trust: 0 }));
});

test('概率被限制在 [0.05, 0.95]', () => {
  assert.ok(speakProbability('沉默寡言高冷冷淡内向', { trust: -999 }) >= 0.05);
  assert.ok(speakProbability('健谈热情话痨外向活泼', { addressed: true, trust: 999 }) <= 0.95);
});

test('willSpeak 使用注入 rng 是确定性的', () => {
  assert.equal(willSpeak('', {}, () => 0.0), true);
  assert.equal(willSpeak('', {}, () => 0.99), false);
});

test('null / undefined persona 不报错且走基线', () => {
  assert.equal(speakProbability(null), 0.55);
  assert.equal(speakProbability(undefined), 0.55);
});
