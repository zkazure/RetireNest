import assert from 'node:assert/strict';
import fs from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

const page = JSON.parse(
  fs.readFileSync(new URL('../../src/tests/fixtures/retirement-page.json', import.meta.url), 'utf8'),
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
    city: '珠海',
    age: '30',
    retire_age: '55',
    life_expectancy: '90',
    monthly_income: '20000',
    monthly_expense: '12000',
    assets: '500000',
    debt: '0',
    retirement_expense: '8000',
    monthly_pension: '3000',
    nominal_return: '5',
    inflation: '2',
    ...overrides,
  };
}

test('page manifest converts into a valid template', () => {
  assert.equal(template.id, page.id);
  assert.equal(template.version, page.version);
  assert.equal(template.sections.length, 8);
  assert.equal(template.sections.reduce((count, section) => count + section.fields.length, 0), 39);
  assert.equal(template.sections.filter(section => section.toggle).length, 3);
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
  assert.equal(fs.existsSync(new URL('../src/form-template.json', import.meta.url)), false);
});

test('defaults and required checks follow the manifest', () => {
  const { values, errors } = collectValues(template, defaultValues(template));
  assert.ok(errors.some(error => error.field === 'age'));
  assert.ok(errors.some(error => error.field === 'city'));
  assert.ok(!errors.some(error => error.field === 'planning_notes'));
  assert.equal(values.extra_food, false);
  assert.equal(values.partner, '还没想好');
  assert.equal(values.pension_enabled, false);
});

test('toggles gate their sections and conditional fields stay hidden', () => {
  const male = complete({ pension_enabled: true, gender: '男' });
  assert.ok(!activeFieldNames(template, male).has('category'));
  assert.ok(collectValues(template, complete({ pension_enabled: false })).values.pension_enabled === false);
  assert.ok(!('birth_date' in collectValues(template, complete()).values));

  const female = complete({ pension_enabled: true, gender: '女' });
  assert.ok(activeFieldNames(template, female).has('category'));
  assert.ok(collectValues(template, female).errors.some(error => error.field === 'category'));
});

test('cross-field rules locate the failing field', () => {
  const { errors } = collectValues(template, complete({ retire_age: '30' }));
  assert.ok(errors.some(error => error.field === 'retire_age'));

  const dates = collectValues(
    template,
    complete({
      deposit_enabled: true,
      principal: '100000.20',
      annual_rate: '0.0005',
      start_date: '2026-01-01',
      end_date: '2027-01-01',
    }),
  );
  assert.deepEqual(dates.errors, []);
  assert.equal(dates.values.principal, '100000.20');
  assert.equal(dates.values.annual_rate, '0.0005');
});

test('executions map fields to command arguments and skip empty values', () => {
  const { values } = collectValues(template, complete());
  const [plan, living] = enabledExecutions(page, values);
  assert.equal(plan.command, 'plan.retirement');
  assert.equal(living.command, 'living.calculate');

  const inputs = buildInputs(values, living);
  assert.equal(inputs.age, 30);
  assert.equal(inputs.city, '珠海');
  assert.equal(inputs.monthly_expense, 12000);
  assert.equal(inputs.partner, '还没想好');
  assert.ok(!('birth_date' in inputs));
  assert.ok(!('medical_enabled' in inputs));
  assert.ok(!('child_age_now' in inputs));
});

test('module executions only run when their toggle is on', () => {
  const { values } = collectValues(template, complete());
  assert.deepEqual(
    enabledExecutions(page, values).map(execution => execution.command),
    ['plan.retirement', 'living.calculate'],
  );

  const all = { ...values, medical_enabled: true, pension_enabled: true, deposit_enabled: true };
  assert.equal(enabledExecutions(page, all).length, 5);
});
