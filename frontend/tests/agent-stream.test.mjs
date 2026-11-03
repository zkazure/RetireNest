import assert from 'node:assert/strict';
import fs from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

async function loadTs(file) {
  const source = fs.readFileSync(new URL('../src/' + file, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  return import(
    'data:text/javascript;base64,' + Buffer.from(outputText).toString('base64')
  );
}

const { SseParser, replyText } = await loadTs('agent-stream.ts');

test('解析一个完整事件', () => {
  const parser = new SseParser();
  const events = parser.push('event: reply\ndata: {"reply":"hi"}\n\n');
  assert.deepEqual(events, [{ event: 'reply', data: '{"reply":"hi"}' }]);
});

test('跨 chunk 的事件只在完整后返回', () => {
  const parser = new SseParser();
  assert.deepEqual(parser.push('event: tool_call\ndata: {"type"'), []);
  assert.deepEqual(parser.push(':"tool_call"}\n\n'), [
    { event: 'tool_call', data: '{"type":"tool_call"}' },
  ]);
});

test('一次 chunk 包含多个事件', () => {
  const parser = new SseParser();
  const events = parser.push('event: a\ndata: 1\n\nevent: b\ndata: 2\n\n');
  assert.deepEqual(events, [
    { event: 'a', data: '1' },
    { event: 'b', data: '2' },
  ]);
});

test('兼容 CRLF', () => {
  const parser = new SseParser();
  const events = parser.push('event: reply\r\ndata: 你好\r\n\r\n');
  assert.deepEqual(events, [{ event: 'reply', data: '你好' }]);
});

test('忽略注释行并合并多行 data', () => {
  const parser = new SseParser();
  const events = parser.push(': ping\nevent: x\ndata: line1\ndata: line2\n\n');
  assert.deepEqual(events, [{ event: 'x', data: 'line1\nline2' }]);
});

test('没有 data 的块不产生事件', () => {
  const parser = new SseParser();
  assert.deepEqual(parser.push('event: ping\n\n'), []);
});

test('未完成的事件留在缓冲区', () => {
  const parser = new SseParser();
  assert.deepEqual(parser.push('data: 1\n'), []);
  assert.deepEqual(parser.push('\n'), [{ event: 'message', data: '1' }]);
});

test('reply 事件取 reply 字段', () => {
  const data = JSON.parse('{"session_id":"s1","reply":"你好","warnings":[]}');
  assert.equal(replyText(data), '你好');
});

test('兼容旧版的 text 字段', () => {
  assert.equal(replyText({ text: '旧格式' }), '旧格式');
});

test('两个字段都没有时返回空串', () => {
  assert.equal(replyText({}), '');
  assert.equal(replyText({ reply: null }), '');
});
