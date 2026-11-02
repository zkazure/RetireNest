import assert from 'node:assert/strict';
import fs from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';
const template = JSON.parse(fs.readFileSync(new URL('../src/form-template.json',import.meta.url),'utf8'));
async function loadTs(file) {
  const source=fs.readFileSync(new URL('../src/'+file,import.meta.url),'utf8');
  const {outputText}=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
  return import('data:text/javascript;base64,'+Buffer.from(outputText).toString('base64'));
}
const {validateTemplate,defaultValues,collectValues,buildRequest,activeFieldNames}=await loadTs('form-data.ts');
const {toDemoInput}=await loadTs('form-adapter.ts');
const fresh=()=>structuredClone(template);

test('default request keeps numeric and boolean types, omits disabled module fields',()=>{
  validateTemplate(template);
  const {values,errors}=collectValues(template,defaultValues(template));
  assert.deepEqual(errors,[]);
  assert.equal(values.age,28);
  assert.equal(values.extra_food,false);
  assert.equal(values.pension_enabled,false);
  assert.ok(!('birth_date' in values));
  assert.equal(values.child_age_now,null);
  const request=buildRequest(template,{...values,apiKey:'never-export-this',unknown:'ignore'});
  assert.ok(!('apiKey' in request.values));
  assert.ok(!('unknown' in request.values));
  assert.equal(request.schema_version,'1.0.0');
  assert.equal(toDemoInput(request).retirementAge,55);
});

test('adding a field only in the template retains it in the request',()=>{
  const next=fresh();
  next.sections[0].fields.push({name:'new_preference',label:'新增偏好',type:'text',required:true});
  validateTemplate(next);
  const raw={...defaultValues(next),new_preference:'  海边生活  '};
  const {values,errors}=collectValues(next,raw);
  assert.deepEqual(errors,[]);
  assert.equal(buildRequest(next,values).values.new_preference,'海边生活');
});

test('conditional fields are validated only when active; hidden stale values are omitted',()=>{
  const raw={...defaultValues(template),pension_enabled:true,gender:'男'};
  assert.ok(!activeFieldNames(template,raw).has('category'));
  assert.ok(collectValues(template,raw).errors.some(error=>error.field==='birth_date'));
  raw.gender='女'; raw.category='';
  assert.ok(collectValues(template,raw).errors.some(error=>error.field==='category'));
  raw.pension_enabled=false;
  const result=collectValues(template,raw);
  assert.deepEqual(result.errors,[]);
  assert.ok(!('category' in result.values));
});

test('decimal strings preserve precision, dates and date order are checked',()=>{
  const raw={...defaultValues(template),deposit_enabled:true,principal:'100000.20',annual_rate:'0.00050000',start_date:'2026-01-01',end_date:'2027-01-01'};
  const valid=collectValues(template,raw);
  assert.deepEqual(valid.errors,[]);
  assert.equal(valid.values.principal,'100000.20');
  assert.equal(valid.values.annual_rate,'0.00050000');
  assert.ok(collectValues(template,{...raw,principal:'1e5'}).errors.some(error=>error.field==='principal'));
  assert.ok(collectValues(template,{...raw,principal:'1.001'}).errors.some(error=>error.field==='principal'));
  assert.ok(collectValues(template,{...raw,end_date:'2025-01-01'}).errors.some(error=>error.field==='end_date'));
  assert.ok(collectValues(template,{...raw,start_date:'2026-02-30'}).errors.some(error=>error.field==='start_date'));
});

test('custom cities, required whitespace, age ordering and integer constraints',()=>{
  const raw=defaultValues(template);
  assert.equal(collectValues(template,{...raw,city:'清远'}).values.city,'清远');
  assert.ok(collectValues(template,{...raw,city:'  '}).errors.some(error=>error.field==='city'));
  assert.ok(collectValues(template,{...raw,retire_age:'20'}).errors.some(error=>error.field==='retire_age'));
  assert.ok(collectValues(template,{...raw,age:'28.5'}).errors.some(error=>error.field==='age'));
});

test('invalid enum, duplicate names, missing option sets, and visibility cycles fail',()=>{
  assert.ok(collectValues(template,{...defaultValues(template),housing_plan:'随便'}).errors.some(error=>error.field==='housing_plan'));
  const duplicate=fresh(); duplicate.sections[0].fields.push({...duplicate.sections[0].fields[0]});
  assert.throws(()=>validateTemplate(duplicate),/重复/);
  const missing=fresh(); missing.optionSets={}; assert.throws(()=>validateTemplate(missing),/选项集/);
  const cycle=fresh(); cycle.sections[0].fields[0].visibleWhen=[{field:'city',equals:'广州'}];
  assert.throws(()=>validateTemplate(cycle),/循环/);
});
