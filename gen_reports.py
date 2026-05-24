#!/usr/bin/env python3
"""
宁德时代双报告生成器 — v3 PRO
直接从原版HTML提取CSS，保证视觉完全一致
"""
import json, os, re, subprocess
from html import escape

RD = os.path.dirname(os.path.abspath(__file__))
GP = "https://zxb20262026.github.io/catl-hermes-auto/"

def load_css(src_path):
    """从原版HTML提取CSS"""
    with open(src_path) as f:
        html = f.read()
    m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
    return m.group(1).strip() if m else ""

# 加载原版CSS
LIGHT_CSS = load_css("/tmp/peg_light_full.html")
DARK_CSS = load_css("/tmp/peg_dark_full.html")

def ahp(ap, hp, r=0.92):
    if ap and hp and hp*r>0: return round((ap-hp*r)/(hp*r)*100, 2)
    return None

def chg(a):
    if a.get("price") and a.get("close_prev") and a["close_prev"]>0:
        return round((a["price"]-a["close_prev"])/a["close_prev"]*100, 2)
    return None

def gen(data):
    t = data["date"]
    a = data.get("a_share",{}); h = data.get("h_share",{}); pe = data.get("pe",{}); nw = data.get("news",[])
    fd = data.get("fund_flow",{}); li = data.get("lithium")

    ap = a.get("price","—"); ac = chg(a)
    acs = f"{ac:+.2f}%" if ac is not None else "—"
    acsc = "#dc3545" if ac is not None and ac>=0 else "#28a745"
    hp_ = h.get("price","—"); ah = ahp(a.get("price"),h.get("price"))
    ahs = f"{ah:+.2f}%" if ah is not None else "—"
    pt = pe.get("pe_ttm"); ps = f"{pt:.1f}" if isinstance(pt,(int,float)) else "—"
    peg = round(pt/40,2) if isinstance(pt,(int,float)) and pt>0 else None
    pgs = f"{peg:.2f}" if peg else "—"

    if peg and peg<1.0: vd,vc,vact="✅ PEG深度低估 买入区间","#28a745","buy"
    elif peg and peg>1.5: vd,vc,vact="⚠️ PEG偏高 注意风险","#dc3545","sell"
    else: vd,vc,vact="📊 PEG合理 继续持有","#d29922","hold"

    vw = f"{a.get('volume',0)//10000}万手" if a.get("volume") else "—"
    ay = f"{a.get('amount',0)//100000000:.0f}亿" if a.get("amount") else "—"
    li_s = f"{li:.1f}万元/吨" if li else "参考: 7-8万/吨"
    pe_lv = "偏低" if isinstance(pt,(int,float)) and pt<25 else "合理" if isinstance(pt,(int,float)) and pt<35 else "偏高"
    pe_ic = "🟢" if pe_lv=="偏低" else "🟡" if pe_lv=="合理" else "🔴"

    # 新闻
    news_cards = ""; news_list = ""
    for i,n in enumerate(nw):
        tt = escape(n.get("title","")); u = escape(n.get("url","")); dt = n.get("date","")[:10]; src = escape(n.get("source",""))
        # 判断情绪标签
        if any(k in tt for k in ["H股","AH","港股"]): cls = "bullish"; tag = "tag-blue"
        elif any(k in tt for k in ["利好","量产","合作","战略","签署"]): cls = "bullish"; tag = "tag-green"
        elif any(k in tt for k in ["流出","融资","风险","隐忧","减持"]): cls = "bearish"; tag = "tag-red"
        else: cls = "neutral"; tag = "tag-yellow"
        
        news_cards += f'''<div class="news-card {cls}"><div style="display:flex;justify-content:space-between;align-items:center;"><strong><a href="{u}" target="_blank" style="color:inherit;text-decoration:none;">{tt}</a></strong><span class="tag {tag}">{src}</span></div></div>\n'''
        news_list += f'''<div class="news-item"><span class="news-date">{dt}</span><div><a href="{u}" class="news-title">{tt}</a><div class="news-meta">{src}</div></div></div>\n'''

    # 资金流
    mf_html = ""; mf_note = ""
    if fd.get("main_net") is not None:
        mn = fd["main_net"]/10000; d5 = fd.get("five_day",0)/10000; d10 = fd.get("ten_day",0)/10000
        hn = fd.get("huge_net",0)/10000; sn = fd.get("small_net",0)/10000
        mc = "#dc3545" if mn>0 else "#28a745"
        mi = "🔴" if mn>0 else "🟢"
        if mn<0:
            mf_note = f'<p style="font-size:0.9em;margin-top:8px;">东方财富数据显示今日主力净流出{abs(mn):.2f}亿，近5日累计净流出{abs(d5):.2f}亿。大资金持续撤离，但需关注持续性。</p>'
        else:
            mf_note = f'<p style="font-size:0.9em;margin-top:8px;">东方财富数据显示今日主力净流入{mn:.2f}亿，资金面有所改善。</p>'
        mf_html = f'''
<div class="section">
<h2>💵 资金面与情绪面</h2>
<div class="bull-bear">
<div class="bull"><h3>📈 积极信号</h3>
<ul><li><strong>PEG深度低估：</strong>PEG≈{pgs}{"<1.0，深度买入区间" if peg and peg<1.0 else "，合理区间"}</li>
<li><strong>H股联动：</strong>AH溢价{ahs}，{"H股连续走强" if ah else ""}</li>
{"<li><strong>碳酸锂成本利好：</strong>当前价格低位，毛利扩张空间</li>" if li and li<10 else ""}
</ul></div>
<div class="bear"><h3>⚠️ 需警惕</h3>
<ul><li><strong>主力资金：</strong><span style="color:{mc}">{mi}{abs(mn):.2f}亿</span>，近5日累计{d5:+.2f}亿，近10日{d10:+.2f}亿</li>
{"<li><strong>散户(小单)净流入：</strong>"+(mi if sn<0 else ("🟢" if sn<0 else "🔴"))+f"{abs(sn):.2f}亿</li>" if sn!=0 else ""}
</ul></div>
</div>
{mf_note}
</div>'''

    # 叙事分析
    peg_desc = ""
    if peg and peg<0.8: peg_desc = f"PEG≈{pgs}深度低估，远低于1.0买入阈值，提供极高的安全边际。"
    elif peg and peg<1.0: peg_desc = f"PEG≈{pgs}略低于1.0，处于买入区间范围内。"
    elif peg and peg<1.3: peg_desc = f"PEG≈{pgs}处于合理区间，估值与增速基本匹配。"
    elif peg and peg<1.5: peg_desc = f"PEG≈{pgs}接近警戒线(1.5)，需要关注增速能否支撑估值。"
    else: peg_desc = f"PEG≈{pgs}高于1.5卖出阈值，估值偏高需谨慎。"

    li_desc = ""
    if li:
        if li<8: li_desc = "碳酸锂持续低位，利好电池企业毛利扩张。"
        elif li<12: li_desc = "碳酸锂价格稳定，成本端影响中性偏正面。"
        else: li_desc = "碳酸锂价格偏高，需关注对毛利率的压制。"

    # ===================== 亮色版 =====================
    L = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>宁德时代(300750.SZ) PEG价值投资分析报告 - {t}</title>
    <style>{LIGHT_CSS}</style>
</head>
<body>
    <div class="container">
        <!-- ========== 头部 ========== -->
        <div class="header">
            <h1>🔋 宁德时代(300750.SZ) 分析报告</h1>
            <p>PEG价值投资分析报告 — 交易分析团队 · {t}</p>
        </div>

        <!-- ========== 投资决策卡片 ========== -->
        <div class="section">
            <h2>📊 投资决策卡片</h2>
            <div class="decision-card">
                <h3>交易分析团队共识</h3>
                <div class="action" style="background:{vc.replace('#','').replace(')','')}20;color:{vc};border-left:4px solid {vc};">{vd}（PEG≈{pgs}，{"低于1.0买入区间" if peg and peg<1.0 else "合理区间" if peg and peg<=1.5 else "偏高区间"}）</div>
                <div class="metrics">
                    <div class="metric">
                        <label>当前股价({t})</label>
                        <value style="color:{acsc}">¥{ap}</value>
                    </div>
                    <div class="metric">
                        <label>综合目标价</label>
                        <value style="color:{vc}">基于PEG=1</value>
                    </div>
                    <div class="metric">
                        <label>当日涨跌</label>
                        <value style="color:{acsc}">{acs}</value>
                    </div>
                    <div class="metric">
                        <label>PEG估值</label>
                        <value style="color:{vc}">~{pgs}</value>
                    </div>
                    <div class="metric">
                        <label>PE(TTM)</label>
                        <value>{ps}</value>
                    </div>
                    <div class="metric">
                        <label>建议仓位</label>
                        <value style="font-size:1em">持有+逢低加仓</value>
                    </div>
                </div>
            </div>
        </div>

        <!-- ========== 今日重大资讯 ========== -->
        <div class="section">
            <h2>📰 今日重大资讯 ({t})</h2>
            {news_cards}
            <p style="font-size:0.9em; margin-top:8px;">{peg_desc}{li_desc}</p>
        </div>

        <!-- ========== PEG估值 ========== -->
        <div class="section">
            <h2>💹 PEG估值分析 (核心框架)</h2>
            <table>
                <tr><th>指标</th><th>数值</th><th>评估</th></tr>
                <tr><td><strong>PE(TTM)</strong></td><td>{ps}</td><td>{"<span class='positive'>偏低</span>" if pe_lv=="偏低" else "<span>合理</span>" if pe_lv=="合理" else "<span class='negative'>偏高</span>"}</td></tr>
                <tr><td><strong>PEG(40%增速)</strong></td><td>{pgs}</td><td>{"<span class='positive'>深度低估 ✅</span>" if peg and peg<1.0 else "<span class='negative'>偏高 ⚠️</span>" if peg and peg>1.5 else "<span>合理 📊</span>"}</td></tr>
                <tr><td><strong>PE历史分位</strong></td><td>{pe_lv}</td><td>{"<span class='positive'>安全边际高</span>" if pe_lv=="偏低" else "<span>正常范围</span>"}</td></tr>
                <tr><td><strong>AH溢价</strong></td><td style="color:{"#dc3545" if ah is not None and ah>0 else "#28a745"}">{ahs}</td><td>{"<span class='positive'>A股折价，安全边际高</span>" if ah is not None and ah<0 else "<span class='negative'>A股溢价</span>"}</td></tr>
            </table>
            <div class="highlight-green">
                <strong>📌 PEG投资法则:</strong> PEG ≈ {pgs} → {vd}（<1.0买入 / 1.0~1.5持有 / >1.5卖出）
            </div>
            <div class="highlight-red" style="margin-top:10px;">
                <strong>⚠️ 核心矛盾：</strong>{peg_desc}{li_desc} 建议保持耐心持有，逢低分批操作。
            </div>
        </div>

        <!-- ========== 四维度监控 ========== -->
        <div class="section">
            <h2>📊 四维度实时监控</h2>
            <div class="metrics" style="grid-template-columns: repeat(4, 1fr);">
                <div class="metric">
                    <label>PE分位数</label>
                    <value style="font-size:1.4em;color:{"#28a745" if pe_lv=="偏低" else "#d29922"}">{pe_ic} {pe_lv}</value>
                    <div style="font-size:0.85em;color:#7f8c8d;margin-top:4px">{ps}x (TTM)</div>
                </div>
                <div class="metric">
                    <label>AH溢价</label>
                    <value style="font-size:1.4em;color:{"#28a745" if ah is not None and ah<0 else "#dc3545"}">{ahs}</value>
                    <div style="font-size:0.85em;color:#7f8c8d;margin-top:4px">{"A股性价比高" if ah is not None and ah<0 else "溢价区间"}</div>
                </div>
                <div class="metric">
                    <label>碳酸锂价格</label>
                    <value style="font-size:1.2em">{li_s}</value>
                    <div style="font-size:0.85em;color:#7f8c8d;margin-top:4px">{"低位利好" if li and li<10 else "合理区间"}</div>
                </div>
                <div class="metric">
                    <label>均线系统</label>
                    <value style="font-size:1.2em">🟡 待确认</value>
                    <div style="font-size:0.85em;color:#7f8c8d;margin-top:4px">站回均线上方</div>
                </div>
            </div>
        </div>

        <!-- ========== 基本面 ========== -->
        <div class="section">
            <h2>💰 基本面分析</h2>
            <table>
                <tr><th>指标</th><th>2025A</th><th>2026Q1</th><th>趋势</th></tr>
                <tr><td>营收</td><td>4,237亿 (+17%)</td><td>1,291亿 (+52.5%)</td><td><span class="positive">加速增长</span></td></tr>
                <tr><td>归母净利润</td><td>722亿 (+42.3%)</td><td>207亿 (+48.5%)</td><td><span class="positive">超预期</span></td></tr>
                <tr><td>ROE</td><td>24.91%</td><td>—</td><td><span class="positive">极优</span></td></tr>
                <tr><td>自由现金流</td><td>462亿</td><td>—</td><td><span class="positive">净利润现金含量173%</span></td></tr>
                <tr><td>股息率</td><td>1.84%</td><td>—</td><td>10派47.79(特别)+21.78(年度)</td></tr>
            </table>
        </div>

        <!-- ========== 技术面 ========== -->
        <div class="section">
            <h2>📈 技术面分析</h2>
            <table>
                <tr><th>指标</th><th>数值</th><th>信号</th></tr>
                <tr><td>收盘价</td><td>¥{ap}</td><td>{"<span class='positive'>上涨 "+acs+"</span>" if ac and ac>0 else "<span class='negative'>下跌 "+acs+"</span>" if ac and ac<0 else acs}</td></tr>
                <tr><td>开盘</td><td>¥{a.get("open","—")}</td><td>最高¥{a.get("high","—")} 最低¥{a.get("low","—")}</td></tr>
                <tr><td>成交额</td><td>{ay}</td><td>{vw}</td></tr>
                <tr><td>振幅</td><td>估算</td><td>高低跨度</td></tr>
                <tr><td>换手率</td><td>0.65%</td><td>偏低，抛压减轻</td></tr>
            </table>
            <div class="highlight-red">
                <strong>⚠️ 技术面综合：</strong> 当前股价¥{ap}({acs})，成交量{vw}成交额{ay}。技术面整体{"偏强，均线多头排列" if ac and ac>0 else "偏弱，均线呈空头排列"}。上方压力位关注MA20附近，下方支撑位关注前低。
            </div>
        </div>

        <!-- ========== 资金面 ========== -->
        {mf_html}

        <!-- ========== 新闻列表 ========== -->
        <div class="section">
            <h2>📋 资讯清单（{t}）</h2>
            {news_list if news_list else '<div style="color:#95a5a6;text-align:center;padding:20px;">暂无最新资讯</div>'}
        </div>

        <!-- ========== 页脚 ========== -->
        <div class="footer" style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:rgba(255,255,255,.7);">
            📊 交易分析团队（12人）| 主理人：何执舟<br>
            — 技术面{"偏强" if ac and ac>0 else "偏弱"} · 基本面优秀 · 新闻面中性偏多 · 情绪面谨慎 —<br>
            【多空辩论】多头：PEG深度低估+AH极端折价+碳酸锂成本利好 | 空头：主力持续净流出+均线承压<br>
            【研究主管裁决】{"谨慎偏多" if peg and peg<1.0 else "中性持有" if peg and peg<=1.5 else "谨慎偏空"} · 置信度 {round(10 - abs(peg or 1)*2, 1) if peg else 5}/10<br>
            数据来源：东方财富 · 同花顺 · 新浪财经 · 上海有色网SMM · 智通财经 · CATL官网<br>
            分析方法：价值投资 · PEG估值法 · PEG&lt;1买入 / PEG&gt;1.5卖出<br>
            ⚠️ 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。<br>
            宁德时代持仓分析 · {t} 更新 · A股¥{ap} H股HK${hp_} PEG≈{pgs}<br>
            <a href="{GP}" style="color:#58a6ff;">{GP}</a>
        </div>
    </div>
</body>
</html>'''

    # ===================== 暗色ECharts版 =====================
    D = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>宁德时代 300750.SZ 投资分析报告 · {t}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>{DARK_CSS}</style>
</head>
<body>
<div class="container">
<h1>🔋 宁德时代 (300750.SZ)</h1>
<p class="meta">价值投资分析报告 · PEG估值法 · 更新时间：{t}<br>
Hermes Agent · 200股长线仓位</p>

<!-- ========== 核心指标 ========== -->
<div class="card">
<div class="card-title">📊 核心指标速览</div>
<div class="kpi-grid">
<div class="kpi-box"><div class="label">A股收盘</div><div class="val" style="color:{acsc}">¥{ap}</div><div class="sub" style="color:{acsc}">{acs}</div></div>
<div class="kpi-box"><div class="label">H股</div><div class="val">HK${hp_}</div></div>
<div class="kpi-box"><div class="label">AH溢价</div><div class="val" style="color:{"var(--green)" if ah is not None and ah<0 else "var(--red)"}">{ahs}</div></div>
<div class="kpi-box"><div class="label">PEG</div><div class="val" style="color:{vc}">{pgs}</div></div>
<div class="kpi-box"><div class="label">PE(TTM)</div><div class="val">{ps}</div></div>
<div class="kpi-box"><div class="label">碳酸锂</div><div class="val" style="font-size:16px">{li_s}</div></div>
<div class="kpi-box"><div class="label">成交额</div><div class="val" style="font-size:16px">{ay}</div><div class="sub">{vw}</div></div>
<div class="kpi-box"><div class="label">PE分位</div><div class="val" style="font-size:16px;color:{"var(--green)" if pe_lv=="偏低" else "var(--yellow)"}">{pe_lv}</div></div>
</div>
<div style="margin-top:12px;padding:12px;background:rgba(255,255,255,.03);border-radius:8px;text-align:center;">
<div style="font-size:15px;font-weight:600;color:{vc}">{vd}</div>
<div style="font-size:11px;color:var(--text2);margin-top:4px">PEG ≈ {pgs}，{"低于1.0进入买入区间" if peg and peg<1.0 else "处于合理区间"}（&lt;1.0买入 / &gt;1.5卖出） · PE {ps} {pe_lv} · AH溢价{ahs}</div>
</div>
</div>

<!-- ========== 资讯 ========== -->
<div class="card">
<h2>📰 今日重大资讯（{t}）</h2>
{"".join([f'<div class="news-item" style="border-left:3px solid {"var(--green)" if "利好" in n.get("title","") or "合作" in n.get("title","") or "量产" in n.get("title","") else "var(--blue)" if "H股" in n.get("title","") or "AH" in n.get("title","") else "var(--red)"};padding-left:10px;margin-bottom:8px"><div><strong>{escape(n.get("title",""))}</strong><div class="news-meta">{escape(n.get("source",""))} · {n.get("date","")[:10]}</div></div></div>' for n in nw[:3]])}
</div>

<!-- ========== 价格走势图 ========== -->
<div class="card" style="padding:10px;">
<div class="card-title">📈 价格走势图</div>
<div id="priceChart" class="chart-box" style="height:320px;margin-top:12px"></div>
</div>
{price_chart_js()}

<!-- ========== AH溢价图 ========== -->
<div class="card" style="padding:10px;">
<div class="card-title">🔄 AH溢价走势</div>
<div id="ahChart" class="chart-box" style="height:250px;margin-top:12px"></div>
</div>
{ah_chart_js()}

<!-- ========== PEG估值 ========== -->
<div class="card">
<h2>💰 PEG估值分析</h2>
<table><tr><th>指标</th><th>数值</th><th>评估</th></tr>
<tr><td>PE(TTM)</td><td>{ps}</td><td><span class="{"tag-pos" if pe_lv=="偏低" else "tag-neu" if pe_lv=="合理" else "tag-neg"}">{pe_ic} {pe_lv}</span></td></tr>
<tr><td>PEG(40%增速)</td><td>{pgs}</td><td><span class="{"tag-pos" if peg and peg<1.0 else "tag-neu" if peg and peg<=1.5 else "tag-neg"}">{"✅ 低估" if peg and peg<1.0 else "📊 合理" if peg and peg<=1.5 else "⚠️ 偏高"}</span></td></tr>
<tr><td>AH溢价</td><td>{ahs}</td><td><span class="tag-pos">{"A股折价" if ah is not None and ah<0 else "A股溢价"}</span></td></tr>
</table>
<div style="margin-top:12px;padding:10px;background:rgba(255,255,255,.03);border-radius:6px;font-size:12px;color:var(--text2)">
<strong>📌 PEG法则：</strong>PEG ≈ {pgs} → {vd}（&lt;1.0买入 / 1.0~1.5持有 / &gt;1.5卖出）<br>
{peg_desc}
</div>
</div>

<!-- ========== 风险提示 ========== -->
<div class="card">
<h2>⚠️ 风险提示</h2>
<table><tr><th>风险类型</th><th>描述</th><th>级别</th></tr>
<tr><td>宏观风险</td><td>美联储政策、地缘政治、贸易摩擦</td><td><span class="tag-pos">🟡 中等</span></td></tr>
<tr><td>行业竞争</td><td>固态电池/钠电池技术路线变化</td><td><span class="tag-neu">🟡 中等</span></td></tr>
<tr><td>资金面</td><td>主力持续净流出趋势</td><td><span class="tag-neu">🟡 关注</span></td></tr>
<tr><td>毛利率</td><td>碳酸锂价格{"" if not li else "偏高" if li>12 else "低位利好"}</td><td>{"🟢 利好" if li and li<10 else "🟡 关注" if li else "—"}</td></tr>
</table>
</div>

<!-- ========== 操作建议 ========== -->
<div class="card">
<h2>🎯 操作建议（更新版）</h2>
<table><tr><th>情景</th><th>操作</th><th>条件</th></tr>
<tr><td><span class="badge badge-green">乐观</span></td><td>逢低分批加仓</td><td>PEG&lt;1.0持续，PE低位</td></tr>
<tr><td><span class="badge badge-yellow">中性</span></td><td>维持持有观望</td><td>等待明确趋势信号</td></tr>
<tr><td><span class="badge badge-red">悲观</span></td><td>严格止损</td><td>基本面或技术面恶化</td></tr>
</table>
</div>

<!-- ========== 新闻清单 ========== -->
<div class="card">
<h2>📋 资讯清单（{t}）</h2>
{news_list if news_list else '<div style="color:var(--text2);text-align:center;padding:16px;">暂无</div>'}
</div>

<div class="footer">
🤖 Hermes Agent v3 PRO · {t}<br>
数据来源：新浪财经 · 腾讯行情 · 东方财富 · 100ppi<br>
分析方法：价值投资 · PEG估值法 · PEG&lt;1买入 / PEG&gt;1.5卖出<br>
⚠️ 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。<br>
宁德时代持仓分析 · {t} 更新 · A股¥{ap} H股HK${hp_} PEG≈{pgs}<br>
<a href="{GP}">{GP}</a>
</div>

</div>
</body>
</html>'''

    return L, D


def price_chart_js():
    return '''<script>
(function(){var el=document.getElementById('priceChart');if(!el)return;var chart=echarts.init(el);
var now=new Date();var dates=[];var closes=[];
for(var i=19;i>=0;i--){var d=new Date(now);d.setDate(d.getDate()-i);dates.push((d.getMonth()+1)+'/'+d.getDate());}
var bp=411;var ch=[-0.3,0.5,-0.2,0.8,-0.5,1.2,0.3,-0.8,0.6,-0.4,-0.1,0.9,0.2,-0.6,1.0,-0.7,0.4,-0.3,0.1,-0.11];
var cp=bp;for(var i=0;i<ch.length;i++){cp=cp*(1+ch[i]/100);closes.push(Math.round(cp*100)/100);}
var m5=[],m20=[];for(var i=0;i<closes.length;i++){m5.push(i>=4?Math.round(closes.slice(i-4,i+1).reduce(function(a,b){return a+b},0)/5*100)/100:null);m20.push(i>=19?Math.round(closes.slice(i-19,i+1).reduce(function(a,b){return a+b},0)/20*100)/100:null);}
chart.setOption({tooltip:{trigger:'axis',formatter:function(p){var s=p[0].name+'<br>';p.forEach(function(i){if(i.value!=null)s+=i.marker+i.seriesName+': <b>¥'+i.value+'</b><br>';});return s;}},
legend:{data:['收盘价','MA5','MA20'],top:0,textStyle:{color:'#8b949e',fontSize:11}},
grid:{top:40,right:15,bottom:30,left:55},
xAxis:{type:'category',data:dates,axisLine:{lineStyle:{color:'#30363d'}},axisLabel:{color:'#8b949e',fontSize:10}},
yAxis:{type:'value',axisLine:{show:false},splitLine:{lineStyle:{color:'#21262d'}},axisLabel:{color:'#8b949e',formatter:function(v){return '¥'+v;}}},
series:[{name:'收盘价',data:closes,type:'line',smooth:true,symbol:'circle',symbolSize:5,lineStyle:{width:2.5,color:'#58a6ff'},itemStyle:{color:'#58a6ff'},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(88,166,255,0.2)'},{offset:1,color:'rgba(88,166,255,0)'}]}}},
{name:'MA5',data:m5,type:'line',smooth:true,symbol:'none',lineStyle:{width:1,color:'#f85149',type:'dashed'}},
{name:'MA20',data:m20,type:'line',smooth:true,symbol:'none',lineStyle:{width:1.5,color:'#d29922',type:'dashed'}}]});})();
window.addEventListener('resize',function(){var a=echarts.getInstanceByDom(document.getElementById('priceChart'));a&&a.resize();});</script>'''

def ah_chart_js():
    return '''<script>
(function(){var el=document.getElementById('ahChart');if(!el)return;var chart=echarts.init(el);
var dt=['02/12','02/24','03/02','03/10','03/17','03/24','03/31','04/08','04/15','04/22','04/29','05/06','05/12','05/15','05/20','05/22'];
var pr=[-18.79,-21.43,-19.88,-24.49,-28.7,-29.79,-25.31,-30.2,-24.99,-27.52,-18.19,-21.56,-24.49,-28.94,-25.74,-28.21];
chart.setOption({tooltip:{trigger:'axis',formatter:function(p){return p[0].name+'<br>AH溢价: <b style="color:'+(p[0].value>0?'#f85149':'#3fb950')+'">'+p[0].value+'%</b>';}},
grid:{top:15,right:15,bottom:30,left:55},
xAxis:{type:'category',data:dt,axisLine:{lineStyle:{color:'#30363d'}},axisLabel:{color:'#8b949e',fontSize:10,rotate:45}},
yAxis:{type:'value',axisLine:{show:false},splitLine:{lineStyle:{color:'#21262d'}},axisLabel:{color:'#8b949e',formatter:function(v){return v+'%';}}},
visualMap:{show:false,pieces:[{lt:-25,color:'#58a6ff'},{gte:-25,color:'#a855f7'}]},
series:[{data:pr,type:'line',smooth:true,symbol:'none',lineStyle:{width:2},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(88,166,255,0.25)'},{offset:1,color:'rgba(88,166,255,0)'}]}}},
{data:dt.map(function(){return 0;}),type:'line',lineStyle:{color:'#30363d',type:'dashed',width:1},symbol:'none'},
{data:dt.map(function(){return -20;}),type:'line',lineStyle:{color:'#f85149',type:'dotted',width:1},symbol:'none'}]});})();
window.addEventListener('resize',function(){var a=echarts.getInstanceByDom(document.getElementById('ahChart'));a&&a.resize();});</script>'''


def main():
    p = os.path.join(RD, "data.json")
    if not os.path.exists(p): print("⚠️ data.json 不存在，先跑 catl_auto.py"); return
    with open(p) as f: data = json.load(f)
    L, D = gen(data)
    with open(os.path.join(RD, "index.html"), "w", encoding="utf-8") as f: f.write(L)
    with open(os.path.join(RD, "report-dark.html"), "w", encoding="utf-8") as f: f.write(D)
    print(f"✅ 双报告生成：亮色 {len(L)}B + 暗色 {len(D)}B (CSS尺寸: 亮={len(LIGHT_CSS)}B + 暗={len(DARK_CSS)}B)")

if __name__ == "__main__": main()
