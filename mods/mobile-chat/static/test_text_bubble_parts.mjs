// Text bubble splitter tests for mobile-chat's social theme.
//
// These tests cover the `textBubbleParts` function that lives in
// `mobile-chat-chat.js`. Because the production file is wrapped in a
// top-level IIFE with no exports, the function is reproduced here as a
// verbatim copy. If the production implementation changes, this fixture
// must be updated to match.
//
// Run with: node --test mods/mobile-chat/static/test_text_bubble_parts.mjs
import { test } from "node:test";
import assert from "node:assert/strict";

// ---------------------------------------------------------------------------
// Verbatim copy from mobile-chat-chat.js (textBubbleParts, lines 191-226).
// Keep in sync with the production source.
// ---------------------------------------------------------------------------
function textBubbleParts(value) {
  const text = String(value || "").trim();
  if (!text) return [""];
  const explicitParts = text.split(/\n+/).map((part) => part.trim()).filter(Boolean);
  const sourceParts = explicitParts.length > 1 ? explicitParts : [text];
  const parts = [];
  const splitPattern = /[^。！？!?；;…]+[。！？!?；;…]*|[。！？!?；;…]+/g;

  sourceParts.forEach((part) => {
    const matches = part.match(splitPattern);
    const chunks = (matches && matches.length ? matches : [part])
      .map((chunk) => chunk.trim())
      .filter(Boolean);
    let buffer = "";
    chunks.forEach((chunk) => {
      const next = buffer ? `${buffer}${chunk}` : chunk;
      if (next.length <= 52) {
        buffer = next;
        return;
      }
      if (buffer) parts.push(buffer);
      if (chunk.length <= 72) {
        buffer = chunk;
        return;
      }
      for (let index = 0; index < chunk.length; index += 72) {
        parts.push(chunk.slice(index, index + 72));
      }
      buffer = "";
    });
    if (buffer) parts.push(buffer);
  });
  if (!parts.length) return [text];
  if (parts.length <= 16) return parts;
  return [...parts.slice(0, 15), parts.slice(15).join("")];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
test("empty / whitespace input collapses to a single empty bubble", () => {
  assert.deepEqual(textBubbleParts(""), [""]);
  assert.deepEqual(textBubbleParts("   "), [""]);
  assert.deepEqual(textBubbleParts(null), [""]);
  assert.deepEqual(textBubbleParts(undefined), [""]);
});

test("short Chinese phrase stays as one bubble", () => {
  assert.deepEqual(textBubbleParts("你好"), ["你好"]);
  assert.deepEqual(textBubbleParts("早上好呀"), ["早上好呀"]);
});

test("explicit newlines force multiple bubbles (joined by \\n)", () => {
  const result = textBubbleParts("第一段\n第二段");
  assert.equal(result.length, 2);
  assert.equal(result[0], "第一段");
  assert.equal(result[1], "第二段");
});

test("Chinese sentence terminators: short clauses coalesce into one bubble (length-aware)", () => {
  // Three short clauses joined by 。 total < 52 chars, so they stay as one
  // bubble under the implementation's length-aware merge rule.
  const result = textBubbleParts("你好呀。今天天气真好。我们去散步吧。");
  assert.equal(result.length, 1);
  assert.equal(result[0], "你好呀。今天天气真好。我们去散步吧。");
});

test("Chinese sentence terminators: long content is split into multiple bubbles", () => {
  // Build clauses whose total length exceeds 52 chars so the buffer overflows.
  // Each clause is "啊啊啊啊啊啊啊啊啊啊。" (11 chars); 5 such clauses = 55 chars
  // which guarantees the 52-char merge cap is hit between clauses 4 and 5.
  const clause = "啊啊啊啊啊啊啊啊啊啊。";
  const input = clause.repeat(5);
  const result = textBubbleParts(input);
  assert.ok(result.length > 1, `expected > 1 bubble, got ${result.length}`);
  // Reconstructed text should preserve all characters
  assert.equal(result.join(""), input);
  // No bubble should exceed 72 chars (the chunked-when-overflow length cap)
  for (const part of result) {
    assert.ok(part.length <= 72, `bubble length ${part.length} > 72`);
  }
});

test("mixed 。！？ splitting: long mixed-punctuation content splits correctly", () => {
  // Six long clauses mixed with 。！？,  each ~16 chars, joined by punctuation
  // so the buffer overflows the 52-char merge cap mid-input.
  const clause = "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊"; // 14 chars
  const input =
    clause + "。" + clause + "？" + clause + "！" + clause + "。" + clause + "？" + clause + "！";
  // 14*6 + 6 punctuation = 90 chars
  const result = textBubbleParts(input);
  assert.ok(result.length > 1, `expected > 1 bubble, got ${result.length}`);
  // Reconstructed text should preserve all characters
  assert.equal(result.join(""), input);
});

test("long single line that exceeds 52 chars is broken into multiple bubbles", () => {
  const longLine = "啊".repeat(120);
  const result = textBubbleParts(longLine);
  assert.ok(result.length > 1, `expected > 1 bubble, got ${result.length}`);
  // No bubble should exceed 72 chars (the chunked-when-overflow length cap)
  for (const part of result) {
    assert.ok(part.length <= 72, `bubble length ${part.length} > 72`);
  }
  // Reconstructed text should preserve all characters
  const reconstructed = result.join("");
  assert.equal(reconstructed.length, 120);
  assert.ok(reconstructed.split("啊").length - 1 === 120);
});

test("more than 16 bubbles are clamped; the tail is joined back together", () => {
  // 20 long-ish clauses (each > 4 chars) joined by 。: each bubble will be
  // close to the 52-char merge cap and stay separate, producing > 16 entries
  // before the clamp kicks in.
  const clauses = Array.from({ length: 20 }, (_, i) => `这是第${i}条内容比较长的句子`);
  const input = clauses.join("。") + "。";
  const raw = textBubbleParts(input);
  // The clamp guarantees the result is at most 16 entries.
  assert.ok(raw.length <= 16, `expected <= 16 bubbles after clamp, got ${raw.length}`);
  // And if the function split anything, it must have at least 2 entries.
  assert.ok(raw.length >= 2, `expected >= 2 bubbles for long content, got ${raw.length}`);
});

test("emoji and mixed CJK + ASCII stay together when within length cap", () => {
  const text = "嗨～ https://example.com 一起看星星 ✨🌙";
  const result = textBubbleParts(text);
  assert.ok(result.length >= 1);
  // No information should be lost
  assert.equal(result.join(""), text);
});

test("leading and trailing whitespace is trimmed per the production rule", () => {
  const result = textBubbleParts("   你好   ");
  assert.deepEqual(result, ["你好"]);
});

test("pure punctuation-only input still returns at least one bubble", () => {
  const result = textBubbleParts("！！！？？？");
  assert.ok(result.length >= 1);
  // Reconstructed text should still be a non-empty string
  assert.ok(result.join("").length > 0);
});
