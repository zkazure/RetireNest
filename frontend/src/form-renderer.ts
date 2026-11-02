import { activeFieldNames, collectValues, defaultValues, fieldOptions, validateTemplate } from './form-data';
import type { FieldError, FormField, FormTemplate, RawValues } from './form-types';

type Control = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
interface Entry { field: FormField; control: Control; wrapper: HTMLElement; error: HTMLElement; custom?: HTMLInputElement; customWrapper?: HTMLElement }
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
