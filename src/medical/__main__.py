"""在 src 下执行 uv run python -m medical；加 --demo 运行固定示例。"""

import sys

from . import estimate_medical_cost


def main() -> int:
    try:
        if "--demo" in sys.argv:
            age, city, insurance = 35, "上海", "职工医保"
        else:
            age = int(input("请输入年龄：").strip())
            city = input("请输入居住城市，例如上海：").strip()
            options = {"1": "职工医保", "2": "居民医保", "3": "无医保"}
            choice = input("医保类型（1 职工医保 / 2 居民医保 / 3 无医保）：").strip()
            insurance = options.get(choice, choice)
        result = estimate_medical_cost(age, city, insurance)
    except (ValueError, EOFError) as exc:
        print(f"输入有误：{exc}")
        return 1
    print(f"所属年龄段：{result['age_group']}")
    print(f"年度医疗消费预算：{result['annual_medical_cost']:,.2f} 元/年")
    print(f"月均医疗消费预算：{result['monthly_medical_cost']:,.2f} 元/月")
    print(result["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
