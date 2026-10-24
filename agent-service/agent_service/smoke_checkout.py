"""
退租端到端一键冒烟：
自动完成 取消残留单 -> 退租 -> 搬离日 -> 损坏 -> 结算 -> 确认 -> 重复确认拒绝 -> 房间释放验证
运行：python -m agent_service.smoke_checkout
"""

import os
import sys
import uuid

import requests

JAVA = os.getenv("JAVA_BASE", "http://127.0.0.1:8080")
AGENT = os.getenv("AGENT_BASE", "http://127.0.0.1:8000")
USERNAME = os.getenv("SMOKE_USER", "zhangsan")
PASSWORD = os.getenv("SMOKE_PASS", "12345678")

results = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail if not cond else ''}")
    if not cond:
        print("SMOKE ABORT")
        sys.exit(1)


def j(method, path, **kw):
    return requests.request(method, f"{JAVA}{path}", timeout=15, **kw)


def pick(d: dict, *names: str, default=None):
    for name in names:
        if name in d and d[name] is not None:
            return d[name]
    return default


def login(user, pwd):
    r = j("POST", "/auth/login", json={"username": user, "password": pwd})
    assert r.status_code == 200, f"login {user} http {r.status_code}: {r.text}"
    return r.json()["data"]["token"]


def me(token):
    r = j("GET", "/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"/auth/me http {r.status_code}: {r.text}"
    return r.json()["data"]


def chat(token, msg):
    import json as _json

    r = requests.post(
        f"{AGENT}/chat",
        json={"message": msg},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
        stream=True,
    )
    assert r.status_code == 200, f"/chat http {r.status_code}: {r.text}"

    parts: list[str] = []
    fallback: list[str] = []
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = _json.loads(line[5:].strip())
        if "text" in data:
            parts.append(data["text"])
        elif "answer" in data:
            fallback.append(data["answer"])
    return "".join(parts) if parts else (fallback[0] if fallback else "")


def current_case(user_id: int):
    r = j("GET", "/checkout/cases/current", params={"tenantId": user_id})
    assert r.status_code == 200, f"current case http {r.status_code}: {r.text}"
    return r.json().get("data")


def main():
    # 0. 登录 + 获取当前用户/租约
    token = login(USERNAME, PASSWORD)
    user = me(token)

    user_id = int(user["user_id"])
    room_no = user["room_no"]
    check("0-登录并获取房号", bool(room_no), f"user={user}")

    # 0.1 清理残留退租单，保证从 ACTIVE 开始
    cur = current_case(user_id)
    if cur:
        r = j(
            "POST",
            f"/checkout/cases/{cur['id']}/cancel",
            params={"tenantId": user_id},
            json={},
        )
        assert r.status_code == 200, f"cancel old case http {r.status_code}: {r.text}"

    user = me(token)
    lease_status = user["status"]
    check("0.2-初始租约ACTIVE", lease_status == "ACTIVE", f"user={user}")

    # 动态选一个合法搬离日：到期日前一个月 15 号
    end_date = user["end_date"]
    y, m, _ = map(int, end_date.split("-"))
    m -= 1
    if m == 0:
        y, m = y - 1, 12
    move_out = f"{y:04d}-{m:02d}-15"

    # 1. 发起退租
    ans = chat(token, "我要退租")
    check("1-发起退租", ("搬离" in ans) or ("哪天" in ans), ans)

    # 2. 给搬离日
    ans = chat(token, f"搬离日是{move_out}")
    check("2-登记搬离日", "损坏" in ans, ans)

    # 3. 报损坏
    ans = chat(token, "浴缸裂了")
    check("3-出结算明细", ("押金" in ans and "结算" in ans) or ("应退" in ans), ans)

    # 4. 用 API 核对结算数字
    cur = current_case(user_id)
    check("4-单进入待确认", cur and cur.get("status") == "AWAITING_CONFIRM", f"case={cur}")

    r = j("GET", f"/checkout/cases/{cur['id']}/settlement-detail", params={"tenantId": user_id})
    assert r.status_code == 200, f"settlement-detail http {r.status_code}: {r.text}"
    detail = r.json()["data"]

    bill = detail["bill"]
    bill_items = pick(detail, "billItems", "bill_items", default=[])
    items = {}
    for i in bill_items:
        code = pick(i, "itemCode", "item_code")
        direction = pick(i, "direction")
        amount = float(pick(i, "amount", default=0))
        months = pick(i, "months", default=0)
        monthly_rent = pick(i, "monthlyRent", "monthly_rent", default=0)
        items[(code, direction)] = {
            "amount": amount,
            "months": months,
            "monthly_rent": monthly_rent,
        }

    deposit = items.get(("DEPOSIT_REFUND", "REFUND"), {}).get("amount", 0.0)
    unused = items.get(("UNUSED_RENT", "REFUND"), {}).get("amount", 0.0)
    utility = items.get(("UTILITY_DEBT", "RECEIVABLE"), {}).get("amount", 0.0)
    damage = items.get(("DAMAGE_COMPENSATION", "RECEIVABLE"), {}).get("amount", 0.0)

    expected = round(deposit + unused - utility - damage, 2)
    actual = round(float(bill["amount"]), 2)
    check(
        "5-结算公式正确",
        expected == actual,
        f"deposit={deposit} unused={unused} utility={utility} damage={damage} expected={expected} actual={actual}",
    )

    damage_items = pick(detail, "damageItems", "damage_items", default=[])
    check(
        "6-损坏项已挂条款依据",
        all(pick(i, "basisClauseNo", "basis_clause_no") for i in damage_items),
        str(damage_items),
    )

    # 5. 确认
    ans = chat(token, "确认")
    check("7-确认成功", ("退租完成" in ans) or ("已释放" in ans), ans)

    # 6. 重复确认必须被拒
    ans = chat(token, "确认")
    check(
        "8-重复确认被拒",
        ("已结束" in ans) or ("无法" in ans) or ("没有" in ans),
        ans,
    )

    # 7. 房间释放验证：新房客可注册该房号
    new_user = f"smoke_{uuid.uuid4().hex[:8]}"
    r = j(
        "POST",
        "/auth/register",
        json={
            "username": new_user,
            "password": "12345678",
            "roomNo": room_no,
        },
    )
    check("9-房间已释放可再注册", r.status_code == 200, f"http={r.status_code} body={r.text}")

    print("\n===== SMOKE SUMMARY =====")
    for name, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\nALL {len(results)} CHECKS PASSED")


if __name__ == "__main__":
    main()