export interface PlanInput {
  city: string;
  age: number;
  retirementAge: number;
  lifeExpectancy: number;
  monthlyIncome: number;
  monthlyExpense: number;
  assets: number;
  debt: number;
  retirementExpense: number;
  monthlyPension: number;
  nominalReturn: number;
  inflation: number;
}

export interface ProjectionPoint { age: number; assets: number }
export interface PlanResult {
  yearsToRetirement: number;
  retirementYears: number;
  realReturn: number;
  monthlySurplus: number;
  target: number;
  projected: number;
  gap: number;
  coverage: number;
  requiredMonthlySaving: number;
  points: ProjectionPoint[];
  depletedAge: number | null;
}

export const defaultInput: PlanInput = {
  city: '广州', age: 28, retirementAge: 55, lifeExpectancy: 90,
  monthlyIncome: 15000, monthlyExpense: 10000, assets: 180000, debt: 30000,
  retirementExpense: 10000, monthlyPension: 2500, nominalReturn: 3, inflation: 2,
};

export function validateInput(input: PlanInput): string | null {
  if (Object.values(input).some(value => typeof value === 'number' && !Number.isFinite(value))) return '请完整填写有效数字。';
  if (input.age < 18 || input.age > 80) return '当前年龄需要在 18 至 80 岁之间。';
  if (input.retirementAge <= input.age || input.retirementAge > 85) return '期望退休年龄需要大于当前年龄，且不超过 85 岁。';
  if (input.lifeExpectancy <= input.retirementAge || input.lifeExpectancy > 110) return '规划至年龄需要大于退休年龄，且不超过 110 岁。';
  if ([input.monthlyIncome, input.monthlyExpense, input.assets, input.debt, input.retirementExpense, input.monthlyPension].some(value => value < 0 || value > 1000000000)) return '金额需在 0 至 10 亿元之间。';
  if (input.inflation < 0 || input.inflation > 10 || input.nominalReturn < -5 || input.nominalReturn > 15) return '请将通胀设为 0%～10%，名义年回报设为 -5%～15%。';
  return null;
}

// All values are in today's purchasing power. Annual contributions and withdrawals
// occur at year end. Pension is a user assumption, not a local policy estimate.
export function calculatePlan(input: PlanInput): PlanResult {
  const error = validateInput(input);
  if (error) throw new Error(error);
  const yearsToRetirement = input.retirementAge - input.age;
  const retirementYears = input.lifeExpectancy - input.retirementAge;
  const realReturn = (1 + input.nominalReturn / 100) / (1 + input.inflation / 100) - 1;
  const annuity = (years: number) => Math.abs(realReturn) < 1e-9 ? years : Math.expm1(years * Math.log1p(realReturn)) / realReturn;
  const annualNeed = Math.max(0, input.retirementExpense - input.monthlyPension) * 12;
  const target = annualNeed * annuity(retirementYears) / (1 + realReturn) ** retirementYears;
  const monthlySurplus = input.monthlyIncome - input.monthlyExpense;
  const netAssets = input.assets - input.debt;
  const projected = netAssets * (1 + realReturn) ** yearsToRetirement + monthlySurplus * 12 * annuity(yearsToRetirement);
  const requiredMonthlySaving = Math.max(0, (target - netAssets * (1 + realReturn) ** yearsToRetirement) / annuity(yearsToRetirement) / 12);
  const points: ProjectionPoint[] = [{ age: input.age, assets: netAssets }];
  let balance = netAssets;
  let depletedAge: number | null = null;
  for (let age = input.age + 1; age <= input.lifeExpectancy; age++) {
    balance = balance * (1 + realReturn) + (age <= input.retirementAge ? monthlySurplus * 12 : -annualNeed);
    if (age >= input.retirementAge && balance < 0 && depletedAge === null) depletedAge = age;
    points.push({ age, assets: balance });
  }
  return {
    yearsToRetirement, retirementYears, realReturn, monthlySurplus, target, projected,
    gap: Math.max(0, target - projected), coverage: target > 0 ? Math.max(0, projected / target * 100) : 100,
    requiredMonthlySaving, points, depletedAge,
  };
}
