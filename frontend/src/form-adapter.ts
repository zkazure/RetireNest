import type { PlanRequest } from './form-types';
import type { PlanInput } from './model';

// Temporary adapter: extended values are retained in PlanRequest, but only
// these core fields participate in the existing local demonstration engine.
export function toDemoInput(request: PlanRequest): PlanInput {
  const values = request.values;
  const numeric = (name: string) => {
    if (typeof values[name] !== 'number') throw new Error(`本地演示缺少数值字段：${name}`);
    return values[name] as number;
  };
  if (typeof values.city !== 'string') throw new Error('请填写城市。');
  return {
    city:values.city, age:numeric('age'), retirementAge:numeric('retire_age'),
    lifeExpectancy:numeric('life_expectancy'), monthlyIncome:numeric('monthly_income'),
    monthlyExpense:numeric('monthly_expense'), assets:numeric('assets'), debt:numeric('debt'),
    retirementExpense:numeric('retirement_expense'), monthlyPension:numeric('monthly_pension'),
    nominalReturn:numeric('nominal_return'), inflation:numeric('inflation'),
  };
}
