"""衣食住行模块的 pytest 用例：参数自洽、各项支出、逐年序列与 JSON 入口。"""

from living import (
    AVG_HOUSEHOLD_SIZE,
    CHILD_EQUIV,
    EDU_INFLATION,
    EDU_RATE,
    EXPECTED_CHILDREN,
    HOLDING_COST,
    INFLATION,
    LOAN_YEARS,
    PARTNER_BASE,
    RENT_BASE,
    RENTER_UTILITY,
    LivingProfile,
    calculate,
    child_birth_user_age,
    clothing_cost,
    education_cost,
    food_cost,
    house_buy_year,
    house_type,
    housing_cost,
    to_real,
    total_living_cost,
    transport_cost,
)

PROFILE = {"age": 22, "city": "珠海", "monthly_expense": 5000}


def _expect_error(fn) -> None:
    """断言 fn() 必须抛 ValueError。"""
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("应该抛 ValueError，但没有抛")


# ---------------- 参数自洽 ----------------

def test_家庭规模与统计局口径自洽():
    n = PARTNER_BASE["还没想好"] + CHILD_EQUIV * EXPECTED_CHILDREN["还没想好"]
    assert abs(n - AVG_HOUSEHOLD_SIZE) < 0.05, f"家庭规模不自洽: {n:.3f}"


def test_教育基准合计约等于CIEFR的23_3万():
    total = sum((hi - lo) * rate for lo, hi, rate in EDU_RATE)
    assert abs(total - 235_500) < 10_000, f"教育基准合计异常: {total}"


def test_教育通胀高于整体通胀():
    assert EDU_INFLATION > INFLATION


# ---------------- 各项目的行为 ----------------

def test_教育窗口起止():
    """22 岁用户、30 岁生育：孩子 3 岁是第 11 年，22 岁是第 30 年。"""
    e = education_cost(LivingProfile(**PROFILE), 60)
    assert e[10] == 0 and e[11] > 0, "教育窗口起点错误"
    assert e[29] > 0 and e[30] == 0, "教育窗口终点错误"


def test_已有子女按真实年龄推算教育窗口():
    """40 岁用户、孩子已经 10 岁：教育支出从今年就开始，不是等到 12 年后。"""
    p = LivingProfile(age=40, city="珠海", monthly_expense=8000, child_age_now=10)
    assert child_birth_user_age(p) == 30, "生育年龄应由 40-10 反推为 30"
    e = education_cost(p, 40)
    assert e[0] > 0, "孩子已经上小学，今年就该有教育支出"
    assert e[12] == 0, "孩子 22 岁后教育支出应归零"


def test_没有孩子时教育支出恒为零():
    p = LivingProfile(age=30, city="珠海", monthly_expense=8000,
                      children="不想要", child_age_now=None)
    assert sum(education_cost(p, 40)) == 0


def test_买房前租房_买房年首付尖峰_贷款期满房贷归零():
    p = LivingProfile(**PROFILE, housing_plan="买房自住")
    h = housing_cost(p, 60)
    bt = house_buy_year(p)
    assert bt == 6, f"买房时点异常: {bt}"
    assert h[bt] > h[bt + 1] * 5, f"首付尖峰缺失: {h[bt]:.0f} vs {h[bt + 1]:.0f}"
    assert h[bt + LOAN_YEARS] < h[bt + LOAN_YEARS - 1], "房贷未在贷款年限后归零"


def test_房产持有成本与是否刚买无关():
    """同一套房，买了 5 年还是 20 年，物业水电都该是同一个数。"""
    p = LivingProfile(**PROFILE, housing_plan="买房自住")
    h = housing_cost(p, 60)
    bt = house_buy_year(p)
    # 首付在第 0 年，房贷 30 年；第 40 年只剩持有成本
    assert abs(h[bt + 40] - HOLDING_COST["二线"] * (1 + INFLATION) ** (bt + 40)) < 1


def test_租房只付水电不付物业费():
    """租客不该替房东交物业费，租房成本必须低于同等条件的自有房持有成本。"""
    p = LivingProfile(**PROFILE, housing_plan="一直租房")
    h = housing_cost(p, 40)
    # 第 0 年 = 月租 × 12 + 水电燃气，不含物业费
    expected = RENT_BASE["二线"][house_type(p)] * 12 + RENTER_UTILITY["二线"]
    assert abs(h[0] - expected) < 1, f"租房成本异常: {h[0]:.0f} vs {expected}"


def test_现值换算保持平稳():
    p = LivingProfile(**PROFILE, children="不想要")
    real = to_real(food_cost(p, 60))
    assert abs(real[40] / real[10] - 1) < 0.01, "现值应保持稳定"


# ---------------- 整体一致性 ----------------

def test_合计严格等于五项之和():
    p = LivingProfile(age=22, city="珠海", monthly_expense=8000,
                      partner="独自生活", children="不想要", housing_plan="已有房")
    yrs = p.life_expectancy - p.age
    parts = [clothing_cost(p, yrs), food_cost(p, yrs), housing_cost(p, yrs),
             transport_cost(p, yrs), education_cost(p, yrs)]
    tot = total_living_cost(p, yrs)
    for i in range(yrs):
        assert abs(tot[i] - sum(part[i] for part in parts)) < 1e-6, \
            f"第 {i} 年合计与分项不一致"


def test_所有序列函数长度一致():
    p = LivingProfile(**PROFILE)
    years = 60
    for fn in (clothing_cost, food_cost, housing_cost,
               transport_cost, education_cost, total_living_cost):
        assert len(fn(p, years)) == years, f"{fn.__name__} 长度错误"


def test_支出非负():
    p = LivingProfile(**PROFILE)
    assert all(v >= 0 for v in total_living_cost(p, 60))


# ---------------- 输入校验 ----------------

def test_枚举字段写错要报错():
    _expect_error(lambda: LivingProfile(**PROFILE, housing_plan="租房"))
    _expect_error(lambda: LivingProfile(**PROFILE, lifestyle="中等"))


def test_未知城市要报错():
    _expect_error(lambda: LivingProfile(age=22, city="纽约", monthly_expense=5000))


def test_年龄顺序颠倒要报错():
    _expect_error(lambda: LivingProfile(age=60, city="珠海",
                                        monthly_expense=5000, retire_age=50))


def test_测算寿命必须晚于退休年龄():
    _expect_error(lambda: LivingProfile(age=22, city="珠海", monthly_expense=5000,
                                        retire_age=60, life_expectancy=60))


def test_现有孩子年龄与用户年龄矛盾要报错():
    _expect_error(lambda: LivingProfile(age=20, city="珠海",
                                        monthly_expense=5000, child_age_now=10))


# ---------------- JSON 接口 ----------------

def test_JSON入口_字段写错要报错():
    _expect_error(lambda: calculate({"age": 30, "city": "珠海",
                                     "monthly_expense": 9000, "montly_expense": 1}))


def test_JSON入口_返回结构完整():
    out = calculate({"age": 30, "city": "珠海", "monthly_expense": 9000})
    assert out["years"] == 85 - 30
    assert out["retire_index"] == 60 - 30
    assert set(out["nominal"]) == {"clothing", "food", "housing",
                                   "transport", "education", "total"}
    assert len(out["nominal"]["total"]) == out["years"]
    assert len(out["real"]["total"]) == out["years"]


def test_JSON入口_合计等于分项之和():
    out = calculate({"age": 30, "city": "珠海", "monthly_expense": 9000})
    names = ("clothing", "food", "housing", "transport", "education")
    for i in range(out["years"]):
        assert abs(out["nominal"]["total"][i]
                   - sum(out["nominal"][k][i] for k in names)) < 1e-6


def test_JSON入口_可以改测算寿命():
    a = calculate({"age": 30, "city": "珠海", "monthly_expense": 9000})
    b = calculate({"age": 30, "city": "珠海", "monthly_expense": 9000,
                   "life_expectancy": 95})
    assert b["years"] == a["years"] + 10


