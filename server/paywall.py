"""付费墙判定与正文完整度评估。

起点（以及同内容库的 QQ 阅读）对未购买的 VIP 章节只下发试读片段：
    vipStatus=1, isBuy=0, price>0  ->  content 只有百来字，wordsCount 却是几千字

这里的函数只做纯判定，不发请求，供 qidian / 源回落层共用。
"""
from __future__ import annotations


def paywalled(detail: dict) -> bool:
    """是否被付费墙挡住：VIP 章 + 未购买 + 不在限免。"""
    if not detail.get("is_vip"):
        return False
    if detail.get("is_buy"):
        return False
    if detail.get("limit_free"):
        return False
    return True


def ratio(detail: dict) -> float:
    """已下发正文占全章字数的比例，0~1。"""
    words = detail.get("words") or 0
    body = detail.get("chars") or 0
    if words <= 0:
        return 1.0 if body else 0.0
    return round(min(body / float(words), 1.0), 3)


def incomplete(detail: dict, floor: float = 0.4) -> bool:
    """正文是否残缺：试读标记命中，或明显短于全章字数。"""
    if detail.get("teaser"):
        return True
    return ratio(detail) < floor


def verdict(detail: dict) -> dict:
    """给调用方一份完整体检结果。"""
    return {
        "paid": paywalled(detail),
        "ratio": ratio(detail),
        "incomplete": incomplete(detail),
        "words": detail.get("words") or 0,
        "chars": detail.get("chars") or 0,
        "price": detail.get("price") or 0,
    }
