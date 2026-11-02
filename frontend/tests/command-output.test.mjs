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

const { buildOutputRows, formatOutputValue } = await loadTs('command-output.ts');

const command = {
  id: 'demo',
  version: '1.0.0',
  question: '演示命令',
  inputs: [],
  outputs: [
    { name: 'target', question: '退休资金目标', type: 'number', unit: '元', precision: 0 },
    { name: 'coverage', question: '覆盖率', type: 'number', unit: '%', precision: 1 },
    { name: 'principal', question: '本金', type: 'decimal', unit: '元' },
    { name: 'inflation', question: '通胀率', type: 'number' },
    { name: 'nominal', question: '名义支出', type: 'object', unit: '元/年' },
    { name: 'warnings', question: '提示', type: 'series' },
    { name: 'flag', question: '是否包含', type: 'boolean' },
    { name: 'missing', question: '缺失字段', type: 'integer' },
    { name: 'points', question: '资产曲线', type: 'object', visible: false },
  ],
};

function spec(name) {
  return command.outputs.find(output => output.name === name);
}

test('输出表只列 visible !== false 的输出', () => {
  const rows = buildOutputRows(command, { target: 1 });
  assert.deepEqual(
    rows.map(row => row.name),
    ['target', 'coverage', 'principal', 'inflation', 'nominal', 'warnings', 'flag', 'missing'],
  );
});

test('按 precision 格式化数字，decimal 字符串原样保留', () => {
  const rows = buildOutputRows(command, {
    target: 1300376.483,
    coverage: 346.4555,
    principal: '100000.20',
    inflation: 0.025,
  });
  const value = name => rows.find(row => row.name === name).value;
  assert.equal(value('target'), '1,300,376');
  assert.equal(value('coverage'), '346.5');
  assert.equal(value('principal'), '100000.20');
  assert.equal(value('inflation'), '0.025');
});

test('数组与对象只做摘要，不铺开全部元素', () => {
  const rows = buildOutputRows(command, {
    warnings: [1, 2, 3, 4],
    nominal: { clothing: [1, 2], food: [3] },
  });
  const value = name => rows.find(row => row.name === name).value;
  assert.equal(value('warnings'), '1、2、3…（共 4 项）');
  assert.equal(value('nominal'), 'clothing[2] · food[1]');
});

test('空数组、布尔和缺失值都有可读展示', () => {
  const rows = buildOutputRows(command, { warnings: [], flag: true });
  const value = name => rows.find(row => row.name === name).value;
  assert.equal(value('warnings'), '空数组');
  assert.equal(value('flag'), '是');
  assert.equal(value('missing'), '—');
});

test('数组不超过三项时不省略', () => {
  assert.equal(formatOutputValue(spec('warnings'), [1, 2]), '共 2 项：1、2');
});
