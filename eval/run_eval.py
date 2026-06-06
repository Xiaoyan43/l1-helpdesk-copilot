"""分类评测：对 data/sample_tickets.csv 的 gold_* 标注算准确率。

用法（在项目根目录、激活 venv 后）：
    python -m eval.run_eval --engine baseline      # 规则基线（无需 key）
    python -m eval.run_eval --engine claude        # Claude（需 .env 里有 key）
    python -m eval.run_eval --engine both          # 两者对比（默认）
    python -m eval.run_eval --engine both --show-errors

诚实声明：测试集 60 条、单人标注，数字仅供作品演示，非生产评测。
gold_kb_hit 规则：有文章 L1 步骤可直接处理 → 填 KB id；离boarding/HR/LOB  outage 等无文章 → 空（评测时归一化为 NONE）。
"""
import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from app.classifier import llm_classify, rule_based_classify
from app.config import get_settings
from app.data_io import load_labeled_rows
from app.models import Ticket

FIELDS = ["category", "priority", "ticket_type", "kb_hit"]
RESULTS_PATH = Path(__file__).resolve().parent / "last_results.json"


def _norm_kb(v: str | None) -> str:
    v = (v or "").strip().upper()
    return v if v.startswith("KB") else "NONE"


def evaluate(engine: str) -> dict:
    rows = load_labeled_rows()
    classify_fn = rule_based_classify if engine == "baseline" else llm_classify
    hits = {f: 0 for f in FIELDS}
    per_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    field_errors: dict[str, list] = {f: [] for f in FIELDS}
    records = []
    t0 = time.time()

    for r in rows:
        t = Ticket(id=r["id"], subject=r["subject"], body=r["body"],
                   requester=r.get("requester"))
        c = classify_fn(t)
        pred = {"category": c.category.value, "priority": c.priority.value,
                "ticket_type": c.ticket_type.value, "kb_hit": _norm_kb(c.kb_hit)}
        gold = {"category": r["gold_category"].strip(),
                "priority": r["gold_priority"].strip(),
                "ticket_type": r["gold_ticket_type"].strip(),
                "kb_hit": _norm_kb(r["gold_kb_hit"])}
        records.append({"id": r["id"], "subject": r["subject"], "pred": pred,
                        "gold": gold, "reasoning": getattr(c, "reasoning", "")})
        for f in FIELDS:
            if pred[f] == gold[f]:
                hits[f] += 1
            else:
                field_errors[f].append({"id": r["id"], "subject": r["subject"],
                                        "pred": pred[f], "gold": gold[f]})
        if pred["category"] == gold["category"]:
            per_cat[gold["category"]]["tp"] += 1
        else:
            per_cat[pred["category"]]["fp"] += 1
            per_cat[gold["category"]]["fn"] += 1

    dt = time.time() - t0
    n = len(rows)
    f1s = []
    for d in per_cat.values():
        p = d["tp"] / (d["tp"] + d["fp"]) if d["tp"] + d["fp"] else 0.0
        rec = d["tp"] / (d["tp"] + d["fn"]) if d["tp"] + d["fn"] else 0.0
        f1s.append(2 * p * rec / (p + rec) if p + rec else 0.0)
    return {
        "engine": engine,
        "n": n,
        "seconds": round(dt, 1),
        "accuracy": {f: round(hits[f] / n, 3) for f in FIELDS},
        "category_macro_f1": round(sum(f1s) / len(f1s), 3) if f1s else 0.0,
        "field_errors": field_errors,
        "records": records,
    }


def _print_report(res: dict, show_errors: bool, fields: list[str] | None = None) -> None:
    print(f"\n=== engine={res['engine']}  n={res['n']}  用时={res['seconds']}s ===")
    for f in FIELDS:
        print(f"  {f:12} {res['accuracy'][f]:.0%}")
    print(f"  {'category-F1':12} {res['category_macro_f1']:.0%} (macro)")
    if show_errors:
        for f in (fields or FIELDS):
            errs = res["field_errors"].get(f, [])
            if not errs:
                continue
            print(f"  {f} 错误（{len(errs)}）：")
            for e in errs:
                print(f"    {e['id']} 预测 {str(e['pred']):14} 应为 {str(e['gold']):14} | {e['subject']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["baseline", "claude", "both"], default="both")
    ap.add_argument("--show-errors", action="store_true")
    ap.add_argument("--fields", default=None,
                    help="逗号分隔，仅显示这些字段的错误（如 priority）；默认全部")
    args = ap.parse_args()
    fields = args.fields.split(",") if args.fields else None

    engines = ["baseline", "claude"] if args.engine == "both" else [args.engine]
    out = {}
    for eng in engines:
        if eng == "claude" and not get_settings().anthropic_api_key:
            print("\n[跳过 claude] .env 里没有 ANTHROPIC_API_KEY；先填 key 再测真实分类。")
            continue
        res = evaluate(eng)
        out[eng] = res
        _print_report(res, args.show_errors, fields)

    if "baseline" in out and "claude" in out:
        def metric(res: dict, f: str) -> float:
            return res["category_macro_f1"] if f == "category_macro_f1" else res["accuracy"][f]

        print("\n=== 对比（Claude − 基线）===")
        for f in FIELDS + ["category_macro_f1"]:
            a, b = metric(out["baseline"], f), metric(out["claude"], f)
            print(f"  {f:16} {a:.0%} -> {b:.0%}  ({b - a:+.0%})")

    RESULTS_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入 {RESULTS_PATH}")


if __name__ == "__main__":
    main()
