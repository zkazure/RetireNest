import assert from 'node:assert/strict';
import fs from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

const page = JSON.parse(
  fs.readFileSync(new URL('../../src/tests/fixtures/lifecycle-page.json', import.meta.url), 'utf8'),
);

async function loadTs(file) {
  const source = fs.readFileSync(new URL('../src/' + file, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  return import(
    'data:text/javascript;base64,' + Buffer.from(outputText).toString('base64')
  );
}

const { pageToTemplate } = await loadTs('page-to-template.ts');
const { buildInputs, enabledExecutions } = await loadTs('page-values.ts');
const { validateTemplate, defaultValues, collectValues, activeFieldNames } =
  await loadTs('form-data.ts');

const template = pageToTemplate(page);
validateTemplate(template);

function complete(overrides = {}) {
  return {
    ...defaultValues(template),
    sex: '男',
    city: '上海',
    birth_date: '1991-01-01',
    income: '20k30k',
    expense: '10k15k',
    assets: '100w200w',
    debt: 'none',
    retirement_expense: '6k10k',
    entertainment: 'mid',
    travel: 'once',
    children: 'none',
    ...overrides,
  };
}

test('page manifest converts into a valid template', () => {
  assert.equal(template.id, page.id);
  assert.equal(template.version, page.version);
  assert.equal(template.sections.length, 4);
  assert.equal(template.sections.reduce((count, section) => count + section.fields.length, 0), 13);
  assert.equal(template.sections.filter(section => section.toggle).length, 0);
});

test('labels come from the page manifest, not local strings', () => {
  for (const section of page.sections) {
    const converted = template.sections.find(item => item.id === section.id);
    section.fields.forEach((field, index) => {
      assert.equal(converted.fields[index].label, field.label);
      assert.equal(converted.fields[index].name, field.name);
      assert.equal(converted.fields[index].type, field.type);
    });
  }

  const directory = new URL('../src/', import.meta.url);
  const labels = [...new Set(page.sections.flatMap(section => section.fields.map(f => f.label)))];
  const sources = fs
    .readdirSync(directory)
    .filter(file => file.endsWith('.ts'))
    .map(file => fs.readFileSync(new URL(file, directory), 'utf8'))
    .join('\n');
  for (const label of labels) {
    assert.ok(!sources.includes(label), `前端源码不应包含问题文案：${label}`);
  }
});

test('defaults and required checks follow the manifest', () => {
  const { errors } = collectValues(template, defaultValues(template));
  for (const field of ['sex', 'city', 'birth_date', 'income']) {
    assert.ok(errors.some(error => error.field === field), `${field} 应该报必填`);
  }
  assert.ok(!errors.some(error => error.field === 'retirement_age'));
  assert.ok(!errors.some(error => error.field === 'category'));
});

test('tier values pass through and unknown values are rejected', () => {
  const ok = collectValues(template, complete());
  assert.deepEqual(ok.errors, []);
  assert.equal(ok.values.income, '20k30k');
  assert.equal(ok.values.travel, 'once');
  assert.equal(ok.values.birth_date, '1991-01-01');

  const bad = collectValues(template, complete({ income: '不存在' }));
  assert.ok(bad.errors.some(error => error.field === 'income'));
});

test('optional fields stay optional but are still active', () => {
  const active = activeFieldNames(template, complete());
  assert.ok(active.has('retirement_age'));
  assert.ok(active.has('category'));
  assert.ok(active.has('retirement_expense'));
  const { values, errors } = collectValues(template, complete());
  assert.deepEqual(errors, []);
  assert.equal(values.retirement_age, null);
});

test('retirement expense may be left blank and is omitted from command inputs', () => {
  const { values, errors } = collectValues(template, complete({ retirement_expense: '' }));
  assert.deepEqual(errors, []);
  assert.equal(values.retirement_expense, null);

  const executions = enabledExecutions(page, values);
  const inputs = buildInputs(values, executions[0]);
  assert.ok(!('retirement_expense' in inputs));
});

test('executions map fields to command arguments', () => {
  const { values } = collectValues(template, complete());
  const executions = enabledExecutions(page, values);
  assert.deepEqual(
    executions.map(execution => execution.command),
    ['lifecycle.project', 'lifecycle.simulate', 'strategy.compare'],
  );

  const inputs = buildInputs(values, executions[0]);
  assert.equal(inputs.income, '20k30k');
  assert.equal(inputs.city, '上海');
  assert.equal(inputs.birth_date, '1991-01-01');
  assert.ok(!('retirement_age' in inputs));
  assert.ok(!('age' in inputs));
});

test('tier fields expose a custom option with range checks', () => {
  const fields = template.sections.flatMap(section => section.fields);
  const income = fields.find(field => field.name === 'income');
  assert.equal(income.allowCustom, true);
  assert.equal(income.min, 0);
  assert.equal(income.max, 10_000_000);

  const custom = collectValues(template, complete({ income: '17000' }));
  assert.deepEqual(custom.errors, []);
  assert.equal(custom.values.income, '17000');
  const inputs = buildInputs(custom.values, enabledExecutions(page, custom.values)[0]);
  assert.equal(inputs.income, '17000');

  const tooBig = collectValues(template, complete({ income: '99999999' }));
  assert.ok(tooBig.errors.some(error => error.field === 'income'));
  const notNumber = collectValues(template, complete({ income: '一万七' }));
  assert.ok(notNumber.errors.some(error => error.field === 'income'));
});

test('integer tier fields reject decimals in the custom option', () => {
  const fractional = collectValues(template, complete({ retirement_age: '58.5' }));
  assert.ok(fractional.errors.some(error => error.field === 'retirement_age' && error.message.includes('整数')));

  const whole = collectValues(template, complete({ retirement_age: '58' }));
  assert.deepEqual(whole.errors, []);
  assert.equal(whole.values.retirement_age, '58');
});

test('select fields stay choice only', () => {
  const city = template.sections.flatMap(section => section.fields).find(field => field.name === 'city');
  assert.notEqual(city.allowCustom, true);
  const custom = collectValues(template, complete({ city: '某个不存在的城市' }));
  assert.ok(custom.errors.some(error => error.field === 'city'));
});

test('presets come through the manifest and fill every required field', () => {
  assert.deepEqual(template.presets, page.presets.map(preset => ({
    id: preset.id,
    label: preset.label,
    values: preset.values,
    ...(preset.description ? { description: preset.description } : {}),
  })));

  const nailong = template.presets.find(preset => preset.id === 'nailong');
  assert.equal(nailong.label, '奶龙');
  assert.deepEqual(nailong.values, page.presets[0].values);

  const { values, errors } = collectValues(template, { ...defaultValues(template), ...nailong.values });
  assert.deepEqual(errors, []);
  assert.equal(values.retirement_age, '60');
  assert.equal(values.category, null);
});

test('preset description is optional', () => {
  const converted = pageToTemplate({ ...page, presets: [{ id: 'probe', label: '探针', values: { sex: '男' } }] });
  assert.equal('description' in converted.presets[0], false);
});
