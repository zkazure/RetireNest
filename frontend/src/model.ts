// 页面消费的数据结构。计算由后端 /api/retirement/plan 完成。
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
