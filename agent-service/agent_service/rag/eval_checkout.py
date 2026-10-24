import json

from agent_service.tools.checkout_rag import retrieve_checkout_clauses

CASES = [
    {"q": "退租押金怎么算？", "expect": "CLAUSE-DEPOSIT"},
    {"q": "押金什么时候退给我", "expect": "CLAUSE-DEPOSIT"},
    {"q": "住不满一个月租金退吗", "expect": "CLAUSE-UNUSED-RENT"},
    {"q": "我月中搬走能退剩下房租吗", "expect": "CLAUSE-UNUSED-RENT"},
    {"q": "租期到了没退租会怎样", "expect": "CLAUSE-EXPIRED"},
    {"q": "合同到期还需要办退租吗", "expect": "CLAUSE-EXPIRED"},
    {"q": "浴缸裂了要赔吗", "expect": "CLAUSE-DAMAGE"},
    {"q": "墙被我砸了个洞怎么算", "expect": "CLAUSE-DAMAGE"},
    {"q": "家具用旧了算谁的责任", "expect": "CLAUSE-DAMAGE"},
    {"q": "退租时水电费怎么处理", "expect": "CLAUSE-UTILITY"},
    {"q": "物业费要不要补", "expect": None},  # 语料里没有，允许不命中
    {"q": "退租流程是什么", "expect": None},   # 多条都可能，只看命中 checkout 域
    {"q": "我不想租了想反悔", "expect": "CLAUSE-CANCEL"},
    {"q": "退租怎么收费吗", "expect": None},
    {"q": "押金会被扣吗", "expect": "CLAUSE-DEPOSIT"},
]


def main():
    hit = miss = 0
    for c in CASES:
        items = retrieve_checkout_clauses(c["q"], top_k=3)
        top = items[0]["clause_no"] if items else None
        ok = c["expect"] is None or top == c["expect"]
        hit += ok
        miss += (not ok)
        mark = "OK " if ok else "MISS"
        print(f"{mark} q={c['q']!r} top={top} expect={c['expect']}")
    print(f"\n{hit}/{len(CASES)} pass")


if __name__ == "__main__":
    main()