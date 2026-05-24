from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"
COMPANY_INFO_DIR = ROOT / "data" / "company_info"
INDUSTRY_INFO_DIR = ROOT / "data" / "industry_info"

COMPANIES = [
    ("600519", "贵州茅台", "白酒"),
    ("300750", "宁德时代", "动力电池"),
    ("002594", "比亚迪", "新能源汽车"),
    ("000001", "平安银行", "银行"),
    ("600036", "招商银行", "银行"),
    ("000002", "万科A", "地产"),
    ("000651", "格力电器", "家电"),
    ("600089", "特变电工", "电力设备"),
    ("002415", "海康威视", "安防"),
    ("002236", "大华股份", "安防"),
    ("688981", "中芯国际", "半导体"),
    ("688347", "华虹公司", "半导体"),
    ("000333", "美的集团", "家电"),
    ("601012", "隆基绿能", "光伏"),
    ("600438", "通威股份", "光伏"),
    ("601318", "中国平安", "保险"),
    ("601628", "中国人寿", "保险"),
    ("601919", "中远海控", "航运"),
    ("601872", "招商轮船", "航运"),
    ("603288", "海天味业", "调味品"),
    ("603027", "千禾味业", "调味品"),
    ("603259", "药明康德", "CXO"),
    ("300759", "康龙化成", "CXO"),
    ("002475", "立讯精密", "消费电子"),
    ("002241", "歌尔股份", "消费电子"),
    ("600900", "长江电力", "电力"),
    ("600011", "华能国际", "电力"),
    ("002714", "牧原股份", "养殖"),
    ("300498", "温氏股份", "养殖"),
    ("601888", "中国中免", "免税"),
    ("000063", "中兴通讯", "通信设备"),
]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def build_company_docs(code: str, name: str, industry: str) -> None:
    annual = f"""
# {name}年报摘要（2025Q4）

## 主营业务
{name}（{code}）属于{industry}行业，核心业务围绕主营产品、渠道与客户结构展开。

## 经营表现
公司收入、利润与经营现金流是判断经营质量的三条主线。对{name}的分析需重点观察收入增速是否可持续、利润质量是否稳定、现金流是否与利润匹配。

## 管理层观点
管理层强调业务结构优化、成本控制和中长期竞争力建设。判断经营改善应结合财报指标与管理层策略执行进展。

## 风险提示
1. 行业竞争与价格波动影响盈利能力。
2. 下游需求波动影响收入增长节奏。
3. 费用投入变化可能影响短期利润表现。
4. 现金流与利润背离时需关注回款和库存。
"""
    report = f"""
{name}（{code}）研报观点摘录（2026-03）

核心观点：
1) 公司经营质量应从收入、利润、现金流一致性判断，而非单看利润增速。
2) 若经营现金流持续改善且与净利润匹配，增长质量通常更稳健。
3) 行业景气与竞争格局变化会影响估值与业绩预期，需要持续跟踪。

关注指标：
- 营收增速、净利润增速、经营现金流
- 毛利率、费用率、ROE
- 行业景气度、订单与渠道变化

风险提示：
- 需求不及预期
- 成本端波动
- 竞争加剧
"""
    profile = f"""
{name}（{code}）公司资料卡

公司所属行业：{industry}
研究重点：业务结构、盈利质量、现金流质量、风险暴露。
建议跟踪：季度收入、净利润、经营现金流、费用率与管理层指引一致性。
"""
    _write(REPORT_DIR / f"{code}_{name}_年报摘要_2025Q4.md", annual)
    _write(REPORT_DIR / f"{code}_{name}_研报观点_2026-03.txt", report)
    _write(COMPANY_INFO_DIR / f"{code}_{name}_公司资料卡.md", profile)


def build_industry_docs() -> None:
    industry_notes = {
        "银行": "银行研究重点是净息差、资产质量、不良率与拨备覆盖率，以及资本充足水平。",
        "新能源": "新能源研究重点是需求增速、价格竞争、产能利用率和海外政策变化。",
        "消费": "消费研究重点是终端动销、渠道库存、品牌力与费用投放效率。",
        "半导体": "半导体研究重点是景气周期、产能利用率、产品结构和客户验证进展。",
    }
    for name, text in industry_notes.items():
        _write(
            INDUSTRY_INFO_DIR / f"{name}_行业跟踪_2026Q1.md",
            f"{name}行业跟踪（2026Q1）\n\n{text}\n\n风险：景气波动、政策扰动、竞争加剧。",
        )


def main() -> int:
    created = 0
    for code, name, industry in COMPANIES:
        build_company_docs(code, name, industry)
        created += 3
    build_industry_docs()
    print(f"seeded_company_docs={created}")
    print(f"report_dir={REPORT_DIR}")
    print(f"company_info_dir={COMPANY_INFO_DIR}")
    print(f"industry_info_dir={INDUSTRY_INFO_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
