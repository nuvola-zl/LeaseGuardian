from __future__ import annotations

from .repair_rag import retrieve_repair_clauses

EVAL_SET = [
    ("人为损坏谁承担维修费", "repair_policy", ["人为损坏由租客承担"]),
    ("我把东西弄坏了谁出钱", "repair_policy", ["人为损坏由租客承担"]),
    ("自然老化归谁负责", "repair_policy", ["自然老化由房东承担"]),
    ("房东需要承担什么维修", "repair_policy", ["自然老化由房东承担"]),
    ("水龙头维修多少钱", "price_table", ["水龙头维修参考价100元"]),
    ("水龙头漏水修一下价格", "price_table", ["100元"]),
    ("浴缸维修参考价", "price_table", ["浴缸维修参考价500元"]),
    ("浴缸裂了维修费多少", "price_table", ["500元"]),
    ("维修费用有争议怎么办", "repair_policy", ["入住登记", "维修记录"]),
    ("维修责任怎么判断", "repair_policy", ["人为损坏", "自然老化"]),
    ("其他维修项目价格", "price_table", ["人工核定"]),
]


def main() -> None:
    passed = 0
    for query, expected_doc_id, expected_contains in EVAL_SET:
        hits = retrieve_repair_clauses(query, top_k=1)
        top = hits[0] if hits else None
        ok = bool(
            top
            and top.get("doc_id") == expected_doc_id
            and any(text in top.get("text", "") for text in expected_contains)
        )
        passed += int(ok)
        print(f"[{'OK' if ok else 'MISS'}] q={query!r} top={top and top.get('clause_no')} doc={top and top.get('doc_id')}")

    print(f"\nrepair eval: {passed}/{len(EVAL_SET)} passed")


if __name__ == "__main__":
    main()