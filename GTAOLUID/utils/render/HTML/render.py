import math
import asyncio
from typing import Any, Dict, List
from pathlib import Path

import jinja2

from gsuid_core.logger import logger

from ...helpers.static_assets import get_bg_url, get_font_url, get_icon_url

CURRENT_HTML_DIR = Path(__file__).parent
STYLE_DIR = CURRENT_HTML_DIR / "style"
TEMPLATE_DIR = CURRENT_HTML_DIR / "templates"

_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)

# 详情列布局参数：列宽、列间距、外边距与每列叶子上限
_DETAIL_COL_WIDTH = 320
_DETAIL_COL_GAP = 12
_DETAIL_SIDE_PADDING = 20
_DETAIL_ROWS_PER_COL = 50


def _read_style(*names: str) -> str:
    """按顺序拼接样式文件内容，缺失的文件跳过。"""
    parts = []
    for name in names:
        path = STYLE_DIR / name
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _format_money(val: float) -> str:
    """格式化金额缩写显示。"""
    if abs(val) >= 1_000_000_000:
        return f"{val / 1_000_000_000:.2f}B"
    if abs(val) >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"{val / 1_000:.1f}K"
    return f"{val:,.0f}"


def _calculate_donut_staggered(
    items: List[Dict[str, Any]],
    cx: float = 190,
    cy: float = 135,
    r_in: float = 48,
    r_out: float = 76,
    min_gap: float = 24,
) -> List[Dict[str, Any]]:
    """计算带文字碰撞避让的环形扇区与标签引线几何坐标。"""
    total = sum(i["value"] for i in items if i["value"] > 0)
    if total <= 0:
        return []
    slices = []
    angle = -math.pi / 2
    for it in items:
        val = it["value"]
        if val <= 0:
            continue
        slice_angle = (val / total) * (2 * math.pi)
        start_a = angle
        end_a = angle + slice_angle
        mid_a = (start_a + end_a) / 2

        x1 = cx + r_out * math.cos(start_a)
        y1 = cy + r_out * math.sin(start_a)
        x2 = cx + r_out * math.cos(end_a)
        y2 = cy + r_out * math.sin(end_a)

        x3 = cx + r_in * math.cos(end_a)
        y3 = cy + r_in * math.sin(end_a)
        x4 = cx + r_in * math.cos(start_a)
        y4 = cy + r_in * math.sin(start_a)

        large = 1 if slice_angle > math.pi else 0
        path_d = (
            f"M {x1:.1f} {y1:.1f} A {r_out} {r_out} 0 {large} 1 {x2:.1f} {y2:.1f} "
            f"L {x3:.1f} {y3:.1f} A {r_in} {r_in} 0 {large} 0 {x4:.1f} {y4:.1f} Z"
        )

        is_right = math.cos(mid_a) >= 0
        p_start_x = cx + r_out * math.cos(mid_a)
        p_start_y = cy + r_out * math.sin(mid_a)

        r_mid = r_out + 14
        p_mid_x = cx + r_mid * math.cos(mid_a)
        p_mid_y = cy + r_mid * math.sin(mid_a)
        p_end_x = (cx + r_out + 65) if is_right else (cx - r_out - 65)

        slices.append(
            {
                "name": it["name"],
                "amount_str": it["amount_str"],
                "color": it["color"],
                "pct": (val / total) * 100,
                "path_d": path_d,
                "p_start": (p_start_x, p_start_y),
                "p_mid_x": p_mid_x,
                "p_mid_y": p_mid_y,
                "p_end_x": p_end_x,
                "initial_y": p_mid_y,
                "adjusted_y": p_mid_y,
                "is_right": is_right,
            }
        )
        angle = end_a

    for side in [True, False]:
        side_slices = [s for s in slices if s["is_right"] == side]
        if not side_slices:
            continue
        side_slices.sort(key=lambda s: s["initial_y"])

        for _ in range(30):
            adjusted = False
            for i in range(len(side_slices) - 1):
                s1 = side_slices[i]
                s2 = side_slices[i + 1]
                gap = s2["adjusted_y"] - s1["adjusted_y"]
                if gap < min_gap:
                    shift = (min_gap - gap) / 2
                    s1["adjusted_y"] = max(20.0, s1["adjusted_y"] - shift)
                    s2["adjusted_y"] = min(250.0, s2["adjusted_y"] + shift)
                    adjusted = True
            if not adjusted:
                break

    return slices


def _render_donut_svg_staggered(slices: List[Dict[str, Any]], title: str, total_str: str) -> str:
    """根据扇区几何数据渲染纯内联 SVG 环形图字符串。"""
    paths = []
    lines = []
    labels = []
    for s in slices:
        paths.append(f'<path d="{s["path_d"]}" fill="{s["color"]}" opacity="0.9"/>')
        if s["pct"] >= 1.5:
            x1, y1 = s["p_start"]
            x2 = s["p_mid_x"]
            y2 = s["adjusted_y"]
            x3 = s["p_end_x"]
            y3 = s["adjusted_y"]
            points = f"{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} {x3:.1f},{y3:.1f}"
            lines.append(
                f'<polyline points="{points}" fill="none" stroke="{s["color"]}" stroke-width="1.2" opacity="0.85"/>'
            )
            anchor = "start" if s["is_right"] else "end"
            lx = x3 + (4 if s["is_right"] else -4)
            labels.append(
                f'<text x="{lx:.1f}" y="{y3 - 2:.1f}" fill="{s["color"]}" font-size="11" font-weight="600" text-anchor="{anchor}" font-family="youyuan, sans-serif">{s["name"]}</text>'
                f'<text x="{lx:.1f}" y="{y3 + 10:.1f}" fill="#f1f5f9" font-size="10" font-weight="700" text-anchor="{anchor}" font-family="youyuan, sans-serif">${s["amount_str"]}</text>'
            )
    return f"""
    <svg viewBox="0 0 380 270" width="100%" height="auto">
      <circle cx="190" cy="135" r="62" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="28"/>
      <g>{"".join(paths)}</g>
      <circle cx="190" cy="135" r="44" fill="rgba(14, 14, 14, 0.62)" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
      <text x="190" y="130" fill="#cbd5e1" font-size="12" font-weight="600" text-anchor="middle" font-family="youyuan, sans-serif">{title}</text>
      <text x="190" y="148" fill="#ffffff" font-size="15" font-weight="800" text-anchor="middle" font-family="youyuan, sans-serif">{total_str}</text>
      <g>{"".join(lines)}</g>
      <g>{"".join(labels)}</g>
    </svg>
    """


async def render_html(
    html_content: str,
    selector: str,
    *,
    viewport_width: int = 800,
    viewport_height: int = 600,
    device_scale_factor: float = 2.0,
    quality: int = 85,
    timeout: float = 25.0,
) -> bytes:
    """将 HTML 按指定 selector 截图为 JPEG 字节。

    Args:
        html_content: 完整 HTML 文档字符串
        selector: 截图目标元素的 CSS 选择器
        viewport_width: 视口宽度
        viewport_height: 视口高度
        device_scale_factor: 设备像素比
        quality: JPEG 质量 1-100
        timeout: 单步等待超时秒数

    Returns:
        截图 JPEG 字节流
    """
    try:
        from playwright.async_api import (
            TimeoutError as PlaywrightTimeoutError,
            async_playwright,
        )
    except ImportError:
        raise RuntimeError("playwright 库未安装，此功能无法使用")

    timeout_ms = int(timeout * 1000)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    viewport={"width": viewport_width, "height": viewport_height},
                    device_scale_factor=device_scale_factor,
                )
                page = await context.new_page()
                page.set_default_timeout(timeout_ms)
                page.set_default_navigation_timeout(timeout_ms)

                await page.set_content(html_content, wait_until="load", timeout=timeout_ms)
                await page.wait_for_function(
                    "() => Array.from(document.querySelectorAll('img')).every(img => img.complete)",
                    timeout=timeout_ms,
                )
                await page.wait_for_timeout(100)

                element = page.locator(selector)
                await element.wait_for(state="visible")
                bbox = await element.bounding_box()
                if bbox is None:
                    raise RuntimeError("无法获取目标元素位置")

                needed_height = int(bbox["y"] + bbox["height"] + 50)
                if needed_height > viewport_height:
                    await page.set_viewport_size({"width": viewport_width, "height": needed_height})
                    await page.wait_for_timeout(100)
                    bbox = await element.bounding_box()
                    if bbox is None:
                        raise RuntimeError("无法获取目标元素位置")

                screenshot_bytes = await page.screenshot(
                    clip={
                        "x": bbox["x"],
                        "y": bbox["y"],
                        "width": bbox["width"],
                        "height": bbox["height"],
                    },
                    type="jpeg",
                    quality=quality,
                )
                return screenshot_bytes
            finally:
                await browser.close()
    except (PlaywrightTimeoutError, asyncio.TimeoutError, TimeoutError) as e:
        logger.warning(f"[GTAOnline · 图片渲染] Playwright 渲染超时: {e!r}")
        raise RuntimeError("渲染超时，请稍后重试") from e
    except RuntimeError:
        raise
    except Exception as e:
        logger.exception(f"[GTAOnline · 图片渲染] Playwright 渲染失败: {e!r}")
        raise RuntimeError("渲染图片时发生错误，请查看后台日志") from e


async def render_summary_card(data: Dict[str, Any]) -> bytes:
    """GTAOL 总览卡片渲染统一入口。

    Args:
        data: 业务层组装好的纯结构化数据字典。

    Returns:
        渲染产出的 JPEG 字节。
    """
    # 1. 计算 SVG 环形收支图
    income_items = data.get("income_items") or []
    income_total = float(data.get("income_total") or 0.0)
    for it in income_items:
        it["amount_str"] = _format_money(it["value"])

    expense_items = data.get("expense_items") or []
    expense_total = float(data.get("expense_total") or 0.0)
    for it in expense_items:
        it["amount_str"] = _format_money(it["value"])

    in_slices = _calculate_donut_staggered(income_items, cx=190, cy=135, r_in=48, r_out=76, min_gap=24)
    ex_slices = _calculate_donut_staggered(expense_items, cx=190, cy=135, r_in=48, r_out=76, min_gap=24)

    in_svg = _render_donut_svg_staggered(in_slices, "收入来源", f"${_format_money(income_total)}")
    ex_svg = _render_donut_svg_staggered(ex_slices, "资金去向", f"${_format_money(expense_total)}")

    # 2. 读取样式与模板
    css_content = _read_style("header.css", "summary.css")

    # 3. 组装模板渲染上下文
    context = {
        **data,
        "font_uri": get_font_url(),
        "bg_uri": get_bg_url(),
        "css_content": css_content,
        "in_svg": in_svg,
        "ex_svg": ex_svg,
    }

    template = _ENV.get_template("summary.html")
    html_content = template.render(**context)

    # 4. 产出图片
    return await render_html(
        html_content=html_content,
        selector="#capture-card",
        viewport_width=860,
        viewport_height=1400,
    )


def _build_bar_rows(total_name: str, total_value: float, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把总额与分类整理成条形清单行，按金额降序并换算相对总额的占比。"""
    rows: List[Dict[str, Any]] = [
        {
            "name": total_name,
            "amount_str": _format_money(total_value),
            "pct": 100.0 if total_value > 0 else 0.0,
            "color": "#fbbf24",
        }
    ]
    for it in sorted(items, key=lambda x: x["value"], reverse=True):
        pct = (it["value"] / total_value * 100.0) if total_value > 0 else 0.0
        rows.append(
            {
                "name": it["name"],
                "amount_str": _format_money(it["value"]),
                "pct": min(pct, 100.0),
                "color": it["color"],
            }
        )
    return rows


async def render_finance_detail_card(data: Dict[str, Any]) -> bytes:
    """收入/支出明细与收支差进度条卡片渲染入口。

    Args:
        data: 业务层组装好的身份头部与收支分类数据。

    Returns:
        渲染产出的 JPEG 字节。
    """
    income_total = float(data.get("income_total") or 0.0)
    expense_total = float(data.get("expense_total") or 0.0)

    income_rows = _build_bar_rows("总收入", income_total, data.get("income_items") or [])
    expense_rows = _build_bar_rows("总消费", expense_total, data.get("expense_items") or [])

    # 顶部两个环形图沿用总览口径，分类里含「收支差距」「当前结余」对齐项
    ring_income = [dict(it) for it in data.get("ring_income_items") or []]
    ring_expense = [dict(it) for it in data.get("ring_expense_items") or []]
    for it in ring_income:
        it["amount_str"] = _format_money(it["value"])
    for it in ring_expense:
        it["amount_str"] = _format_money(it["value"])
    ring_income_total = float(data.get("ring_income_total") or 0.0)
    ring_expense_total = float(data.get("ring_expense_total") or 0.0)
    in_svg = _render_donut_svg_staggered(
        _calculate_donut_staggered(ring_income), "收入来源", f"${_format_money(ring_income_total)}"
    )
    ex_svg = _render_donut_svg_staggered(
        _calculate_donut_staggered(ring_expense), "资金去向", f"${_format_money(ring_expense_total)}"
    )

    # 收支差进度条整条以总收入为 100%：绿色为总支出占比，红色为剩余收支差占比
    balance = income_total - expense_total
    green_pct = min(expense_total / income_total * 100.0, 100.0) if income_total > 0 else 0.0
    red_pct = max(100.0 - green_pct, 0.0)
    balance_amount_str = f"-${_format_money(abs(balance))}" if balance < 0 else f"${_format_money(balance)}"
    balance_pct_str = f"{balance / income_total * 100.0:.1f}%" if income_total > 0 else "0.0%"

    css_content = _read_style("header.css", "finance_detail.css")
    context = {
        **data,
        "font_uri": get_font_url(),
        "bg_uri": get_bg_url(),
        "css_content": css_content,
        "income_rows": income_rows,
        "expense_rows": expense_rows,
        "in_svg": in_svg,
        "ex_svg": ex_svg,
        "balance_amount_str": balance_amount_str,
        "balance_pct_str": balance_pct_str,
        "red_pct": red_pct,
        "green_pct": green_pct,
    }

    template = _ENV.get_template("finance_detail.html")
    html_content = template.render(**context)

    return await render_html(
        html_content=html_content,
        selector="#capture-card",
        viewport_width=900,
        viewport_height=1400,
    )


def _build_detail_columns(
    tree: List[Dict[str, Any]],
    max_rows: int = _DETAIL_ROWS_PER_COL,
) -> List[List[Dict[str, Any]]]:
    """把详情树按每列至多 max_rows 个叶子拆成横向列。

    跨列的嵌套组在新列顶部重开，标题追加 "（续）"。
    """
    columns: List[List[Dict[str, Any]]] = []
    continued: set = set()
    state: Dict[str, Any] = {"count": 0, "blocks": [], "stack": []}

    def append_block(block: Dict[str, Any]) -> None:
        if state["stack"]:
            state["stack"][-1]["children"].append(block)
        else:
            state["blocks"].append(block)

    def group_block(node: Dict[str, Any]) -> Dict[str, Any]:
        label = node["label"]
        if id(node) in continued:
            label = f"{label}（续）"
        return {"group": True, "label": label, "children": []}

    def new_column(path: List[Dict[str, Any]]) -> None:
        columns.append(state["blocks"])
        state["blocks"] = []
        state["count"] = 0
        state["stack"] = []
        for node in path:
            continued.add(id(node))
            block = group_block(node)
            append_block(block)
            state["stack"].append(block)

    def walk(nodes: List[Dict[str, Any]], path: List[Dict[str, Any]]) -> None:
        for node in nodes:
            if "children" in node:
                block = group_block(node)
                append_block(block)
                state["stack"].append(block)
                walk(node["children"], path + [node])
                state["stack"].pop()
                continue
            if state["count"] >= max_rows:
                new_column(path)
            append_block({"group": False, "label": node["label"], "value": node["value"]})
            state["count"] += 1

    walk(tree, [])
    columns.append(state["blocks"])
    return [blocks for blocks in columns if blocks]


async def render_detail_card(header: Dict[str, Any], tree: List[Dict[str, Any]]) -> bytes:
    """玩家详情卡片渲染入口，身份头部复用总览，统计数据横向分列铺开。

    Args:
        header: 业务层组装的玩家身份头部数据。
        tree: 业务层组装的详情树。

    Returns:
        渲染产出的 JPEG 字节。
    """
    css_content = _read_style("header.css", "detail.css")
    columns = _build_detail_columns(tree)
    card_width = (
        _DETAIL_COL_WIDTH * len(columns) + _DETAIL_COL_GAP * max(len(columns) - 1, 0) + _DETAIL_SIDE_PADDING * 2
    )

    context = {
        **header,
        "font_uri": get_font_url(),
        "bg_uri": get_bg_url(),
        "css_content": css_content,
        "columns": columns,
        "card_width": card_width,
    }

    template = _ENV.get_template("detail.html")
    html_content = template.render(**context)

    return await render_html(
        html_content=html_content,
        selector="#capture-card",
        viewport_width=card_width + 40,
        viewport_height=1600,
    )


async def render_bind_list_card(data: Dict[str, Any]) -> bytes:
    """用户绑定账号列表卡片渲染入口。

    Args:
        data: 业务层组装的用户身份与账号列表数据。

    Returns:
        渲染产出的 JPEG 字节。
    """
    css_content = _read_style("header.css", "bind_list.css")
    context = {
        **data,
        "font_uri": get_font_url(),
        "bg_uri": get_bg_url(),
        "icon_uri": get_icon_url(),
        "css_content": css_content,
    }

    template = _ENV.get_template("bind_list.html")
    html_content = template.render(**context)

    return await render_html(
        html_content=html_content,
        selector="#capture-card",
        viewport_width=440,
        viewport_height=900,
    )


async def render_jobs_list_card(data: Dict[str, Any]) -> bytes:
    """差事推荐列表卡片渲染入口。

    Args:
        data: 业务层组装的差事条目与筛选回显。

    Returns:
        渲染产出的 JPEG 字节。
    """
    css_content = _read_style("header.css", "jobs_list.css")
    context = {
        **data,
        "font_uri": get_font_url(),
        "bg_uri": get_bg_url(),
        "icon_uri": get_icon_url(),
        "css_content": css_content,
    }

    template = _ENV.get_template("jobs_list.html")
    html_content = template.render(**context)

    return await render_html(
        html_content=html_content,
        selector="#capture-card",
        viewport_width=1000,
        viewport_height=2600,
    )


async def render_jobs_detail_card(data: Dict[str, Any]) -> bytes:
    """差事详情卡片渲染入口。

    Args:
        data: 业务层组装的差事详情数据。

    Returns:
        渲染产出的 JPEG 字节。
    """
    css_content = _read_style("header.css", "jobs_detail.css")
    context = {
        **data,
        "font_uri": get_font_url(),
        "bg_uri": get_bg_url(),
        "icon_uri": get_icon_url(),
        "css_content": css_content,
    }

    template = _ENV.get_template("jobs_detail.html")
    html_content = template.render(**context)

    return await render_html(
        html_content=html_content,
        selector="#capture-card",
        viewport_width=780,
        viewport_height=1600,
    )
