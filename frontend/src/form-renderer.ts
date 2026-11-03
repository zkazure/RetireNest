import { activeFieldNames, collectValues, defaultValues, fieldOptions, validateTemplate } from './form-data';
import type { FieldError, FormField, FormTemplate, RawValues } from './form-types';

type Control = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
interface Entry {
  field: FormField; control: Control; wrapper: HTMLElement; error: HTMLElement;
  custom?: HTMLInputElement; customWrapper?: HTMLElement;
  radios?: HTMLInputElement[]; echo?: HTMLElement; sync?: () => void;
}
const amountText = (value: number, unit?: string) => {
  const text = value >= 10000 ? `${(value / 10000).toFixed(value >= 100000 ? 0 : 2).replace(/\.?0+$/, '')} 万` : String(Math.round(value));
  return unit ? `${text}${unit}` : text;
};
const el = <K extends keyof HTMLElementTagNameMap>(tag: K, className = '', text = '') => {
  const node = document.createElement(tag); node.className = className; node.textContent = text; return node;
};

export class FormRenderer {
  private readonly entries = new Map<string,Entry>();
  private readonly bodies = new Map<string,HTMLElement>();
  private attempted = false;
  constructor(host: HTMLElement, readonly template: FormTemplate) {
    validateTemplate(template);
    const defaults = defaultValues(template);
    host.replaceChildren();
    template.sections.forEach((section,index) => {
      const group = el(section.collapsible ? 'details' : 'section', 'form-group template-group');
      group.dataset.section = section.id;
      const heading = el(section.collapsible ? 'summary' : 'div', 'template-section-heading');
      const title = el('h3'); title.append(el('span','',String(index+1).padStart(2,'0')),document.createTextNode(section.title));
      heading.append(title);
      group.append(heading);
      if (section.toggle) {
        const field: FormField = {...section.toggle,type:'checkbox'};
        const entry = this.createEntry(field,defaults);
        entry.wrapper.classList.add('module-toggle');
        group.append(entry.wrapper);
      }
      const body = el('div','template-section-body');
      if (section.description) body.append(el('p','field-hint section-hint',section.description));
      const fields = el('div','fields two-cols template-fields');
      section.fields.forEach(field => fields.append(this.createEntry(field,defaults).wrapper));
      body.append(fields); group.append(body); this.bodies.set(section.id,body);
      host.append(group);
    });
    host.addEventListener('input',()=>this.refresh());
    host.addEventListener('change',()=>this.refresh());
    this.refresh();
  }
  private createEntry(field: FormField, defaults: RawValues): Entry {
    const wrapper = el('div','field template-field');
    wrapper.dataset.field = field.name;
    const id = 'field-'+field.name;
    const label = el('label','field-label',field.label); label.htmlFor = id;
    if (field.required && field.type !== 'checkbox') label.append(el('span','required-mark',' *'));
    const inputWrap = el('div','input-wrap');
    let control: Control;
    if (field.type === 'tier') {
      const hidden = el('input'); hidden.type = 'hidden';
      const group = el('div', 'tier-group'); group.setAttribute('role', 'radiogroup');
      const echo = el('small', 'tier-echo');
      const radios: HTMLInputElement[] = [];
      const amountEcho = (amount: number) => `按 ${amountText(amount, field.unit)} 计算`;
      const echoFor = (value: string) => {
        const tier = (field.tiers ?? []).find(item => item.value === value);
        return tier ? amountEcho(tier.amount) : '';
      };
      const customWrap = el('div', 'tier-custom'); customWrap.hidden = true;
      const custom = el('input'); custom.type = 'number'; custom.id = id + '-custom';
      custom.step = field.integer ? '1' : 'any'; custom.placeholder = '填具体数值';
      custom.setAttribute('aria-label', `${field.label}（自定义）`);
      if (field.min !== undefined) custom.min = String(field.min);
      if (field.max !== undefined) custom.max = String(field.max);
      const customEcho = () => {
        const number = Number(custom.value);
        return custom.value.trim() && Number.isFinite(number) && number >= 0
          ? amountEcho(number) : '填具体数值，提交时按它计算';
      };
      const sync = () => {
        const checked = radios.find(item => item.checked) ?? null;
        radios.forEach(item => item.closest('.tier-option')?.classList.toggle('selected', item.checked));
        const isCustom = checked?.value === '__custom__';
        customWrap.hidden = !isCustom;
        custom.disabled = !isCustom;
        hidden.value = checked?.value ?? '';
        echo.textContent = !checked ? '' : isCustom ? customEcho() : echoFor(checked.value);
      };
      (field.tiers ?? []).forEach(tier => {
        const option = el('label', 'tier-option');
        const radio = el('input'); radio.type = 'radio'; radio.name = field.name; radio.value = tier.value;
        option.append(radio, document.createTextNode(tier.label));
        group.append(option); radios.push(radio);
        radio.addEventListener('change', () => { if (radio.checked) sync(); });
      });
      if (field.allowCustom) {
        const option = el('label', 'tier-option');
        const radio = el('input'); radio.type = 'radio'; radio.name = field.name; radio.value = '__custom__';
        option.append(radio, document.createTextNode('其他（自己填）'));
        group.append(option); radios.push(radio);
        radio.addEventListener('change', () => { if (radio.checked) { sync(); custom.focus(); } });
        custom.addEventListener('input', () => { if (hidden.value === '__custom__') echo.textContent = customEcho(); });
        customWrap.append(custom);
        if (field.unit) customWrap.append(el('span', 'unit', field.unit));
      }
      control = hidden;
      // 自定义输入放在 radiogroup 之外，避免把文本控件塞进单选组。
      if (field.allowCustom) inputWrap.append(group, customWrap, echo);
      else inputWrap.append(group, echo);
      wrapper.append(label, inputWrap);
      if (field.hint) { const hint = el('p', 'field-hint', field.hint); hint.id = id + '-hint'; wrapper.append(hint); }
      const entry: Entry = { field, control, wrapper, radios, echo, sync, error: el('small', 'field-error') };
      if (field.allowCustom) { entry.custom = custom; entry.customWrapper = customWrap; }
      entry.error.id = id + '-error'; entry.error.hidden = true;
      const initial = defaults[field.name];
      if (typeof initial === 'string' && initial) {
        const known = radios.find(radio => radio.value === initial);
        if (known) known.checked = true;
        else if (field.allowCustom) {
          const other = radios.find(radio => radio.value === '__custom__');
          if (other) { other.checked = true; custom.value = initial; }
        }
      }
      sync();
      wrapper.append(entry.error); this.entries.set(field.name, entry);
      return entry;
    }
    if (field.type === 'select') {
      const select = el('select');
      const placeholder = el('option','',field.required ? '请选择' : '请选择（可留空）'); placeholder.value = ''; select.append(placeholder);
      fieldOptions(this.template,field).forEach(item => {const option = el('option','',item.label); option.value=item.value; select.append(option);});
      if (field.allowCustom) { const option=el('option','','其他（自行填写）'); option.value='__custom__'; select.append(option); }
      control = select;
    } else if (field.type === 'textarea') {
      control = el('textarea'); wrapper.classList.add('wide-field');
    } else {
      control = el('input');
      control.type = field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : field.type === 'checkbox' ? 'checkbox' : 'text';
      if (field.type === 'decimal') control.inputMode = 'decimal';
      if (field.type === 'number') {
        control.step=String(field.step ?? (field.integer ? 1 : 'any'));
        if (field.min !== undefined) control.min=String(field.min);
        if (field.max !== undefined) control.max=String(field.max);
      }
    }
    control.id=id; control.name=field.name; control.required=field.required ?? false;
    if ('placeholder' in control) control.placeholder=field.placeholder ?? '';
    if ('maxLength' in control && field.maxLength !== undefined) control.maxLength=field.maxLength;
    if (field.type === 'checkbox') {
      (control as HTMLInputElement).checked=defaults[field.name] === true;
      const checkLabel=el('label','checkbox-label'); checkLabel.htmlFor=id; checkLabel.append(control,document.createTextNode(field.label)); wrapper.append(checkLabel);
    } else {
      control.value=String(defaults[field.name] ?? '');
      inputWrap.append(control);
      if (field.unit) inputWrap.append(el('span','unit',field.unit));
      wrapper.append(label,inputWrap);
    }
    const error=el('small','field-error'); error.id=id+'-error'; error.hidden=true;
    const entry: Entry = {field,control,wrapper,error};
    if (field.type === 'select' && field.allowCustom) {
      const customWrapper=el('div','custom-option');
      const custom=el('input'); custom.type='text'; custom.id=id+'-custom'; custom.placeholder='请输入'+field.label;
      custom.maxLength=field.maxLength ?? 100;
      const customLabel=el('label','field-label','自定义'+field.label); customLabel.htmlFor=custom.id;
      const customWrap=el('div','input-wrap'); customWrap.append(custom); customWrapper.append(customLabel,customWrap); wrapper.append(customWrapper);
      entry.custom=custom; entry.customWrapper=customWrapper;
      const initial=String(defaults[field.name] ?? '');
      if (initial && !fieldOptions(this.template,field).some(option=>option.value===initial)) {control.value='__custom__';custom.value=initial;}
    }
    if (field.hint) { const hint=el('p','field-hint',field.hint); hint.id=id+'-hint'; wrapper.append(hint); }
    const describedBy=[error.id,...(field.hint ? [id+'-hint'] : [])].join(' ');
    control.setAttribute('aria-describedby',describedBy); entry.custom?.setAttribute('aria-describedby',describedBy);
    wrapper.append(error); this.entries.set(field.name,entry); return entry;
  }
  readRaw(): RawValues {
    return Object.fromEntries([...this.entries].map(([name,entry])=>[name,
      entry.field.type === 'checkbox' ? (entry.control as HTMLInputElement).checked
      : entry.control.value === '__custom__' && entry.custom ? entry.custom.value : entry.control.value]));
  }
  // 示例画像一键填入：后端已校验过取值，这里只负责写进控件并把回显刷新同步。
  // values 里没有的字段保持原样，用户可以只填一部分。
  applyPreset(values: Record<string, string | boolean>): void {
    for (const [name, value] of Object.entries(values)) {
      const entry = this.entries.get(name);
      if (!entry) continue;
      if (entry.field.type === 'tier') {
        const radios = entry.radios ?? [];
        const matched = radios.find(radio => radio.value === value);
        if (matched) matched.checked = true;
        else if (entry.custom) {
          const other = radios.find(radio => radio.value === '__custom__');
          if (other) other.checked = true;
          entry.custom.value = String(value);
        }
        entry.sync?.();
        continue;
      }
      if (entry.field.type === 'checkbox') {
        (entry.control as HTMLInputElement).checked = value === true;
        continue;
      }
      if (entry.field.type === 'select') {
        const select = entry.control as HTMLSelectElement;
        const known = [...select.options].some(option => option.value === value);
        if (known) select.value = String(value);
        else if (entry.custom) { select.value = '__custom__'; entry.custom.value = String(value); }
        continue;
      }
      entry.control.value = String(value);
    }
    this.refresh();
  }
  private refresh() {
    const raw=this.readRaw(), active=activeFieldNames(this.template,raw);
    for (const section of this.template.sections) {
      this.bodies.get(section.id)!.hidden=!!section.toggle && raw[section.toggle.name] !== true;
    }
    for (const [name,entry] of this.entries) {
      const enabled=active.has(name);
      entry.wrapper.hidden=!enabled;
      entry.control.disabled=!enabled;
      entry.control.required=enabled && (entry.field.required ?? false);
      entry.radios?.forEach(radio => { radio.disabled = !enabled; radio.required = enabled && (entry.field.required ?? false); });
      if (entry.custom && entry.customWrapper) {
        const custom=entry.control.value==='__custom__';
        entry.customWrapper.hidden=!custom;
        entry.custom.disabled=!enabled || !custom;
        entry.custom.required=enabled && custom && (entry.field.required ?? false);
      }
    }
    if (this.attempted) this.showErrors(collectValues(this.template,raw).errors);
  }
  private showErrors(errors: FieldError[]) {
    for (const [name,entry] of this.entries) {
      const error=errors.find(item=>item.field===name);
      entry.error.textContent=error?.message ?? ''; entry.error.hidden=!error;
      entry.control.setAttribute('aria-invalid',String(!!error)); entry.custom?.setAttribute('aria-invalid',String(!!error));
    }
  }
  setFieldErrors(errors: FieldError[]) {
    this.showErrors(errors);
    const first = errors[0];
    if (!first) return;
    const entry = this.entries.get(first.field);
    if (!entry) return;
    const details = entry.wrapper.closest('details'); if (details) details.open = true;
    const target = entry.custom && entry.control.value === '__custom__' ? entry.custom : entry.control;
    target.focus();
  }
  collect() {
    this.attempted=true; this.refresh();
    const result=collectValues(this.template,this.readRaw()); this.setFieldErrors(result.errors);
    return result;
  }
}
