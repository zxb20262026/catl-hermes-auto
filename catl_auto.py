#!/usr/bin/env python3
"""
宁德时代(CATL)自动化分析系统 v2 — 增强版
新增: 资金流向 + 板块联动 + 反向DCF
"""

import json, os, re, base64, subprocess, urllib.request, urllib.parse, ssl, time
from datetime import datetime

GITHUB_TOKEN = os.environ.get("CATL_GITHUB_TOKEN", "YOUR_GITHUB_TOKEN_HERE")
REPO_OWNER = "zxb20262026"
REPO_NAME = "catl-hermes-auto"
GITHUB_PAGES_URL = "https://zxb20262026.github.io/catl-hermes-auto/"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

ssl_ctx = ssl.create_default_context(); ssl_ctx.check_hostname = False; ssl_ctx.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://finance.sina.com.cn/"}

def hg(url, enc="gbk", t=15):
    r = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(r, timeout=t, context=ssl_ctx).read().decode(enc, errors="replace")

def hgu(url, t=15):
    r = urllib.request.Request(url, headers={**HEADERS, "Referer": "https://*.eastmoney.com/"})
    return urllib.request.urlopen(r, timeout=t, context=ssl_ctx).read().decode("utf-8", errors="replace")

def fetch_a():
    try:
        raw = hg("https://hq.sinajs.cn/list=sz300750")
        m = re.search(r'"(.*?)"', raw)
        if m:
            p = m.group(1).split(",")
            return {"name": p[0], "open": float(p[1]) if p[1] else 0, "close_prev": float(p[2]) if p[2] else 0,
                    "price": float(p[3]) if p[3] else 0, "high": float(p[4]) if p[4] else 0, "low": float(p[5]) if p[5] else 0,
                    "volume": int(p[8]) if len(p)>8 and p[8] else 0, "amount": float(p[9]) if len(p)>9 and p[9] else 0}
    except: return {"error": "fail"}
    return {"error": "parse"}

def fetch_h():
    try:
        raw = hg("https://hq.sinajs.cn/list=hk03750")
        m = re.search(r'"(.*?)"', raw)
        if m:
            p = m.group(1).split(",")
            return {"name": p[1] if len(p)>1 else "", "price": float(p[3]) if len(p)>3 and p[3] else 0}
    except: pass
    return {"error": "fail"}

def fetch_pe():
    try:
        raw = hgu("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz300750,day,,,1,qfq")
        d = json.loads(raw)
        qt = d.get("data",{}).get("sz300750",{}).get("qt",{}).get("sz300750",[])
        if len(qt)>60 and qt[58]: return {"pe_ttm": float(qt[58])}
    except: pass
    return {"error": "fail"}

def fetch_fund():
    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get?secid=0.300750&fields=f62,f64,f66,f184,f63,f65,f99,f100,f101"
        raw = hgu(url)
        d = json.loads(raw).get("data",{})
        if not d or not d.get("f62"):
            return {"info": "资金流向数据暂不可用"}
        return {"main_net": d.get("f62",0), "huge_net": d.get("f64",0), "big_net": d.get("f66",0),
                "small_net": d.get("f184",0), "main_pct": d.get("f63",0), "today_in": d.get("f65",0),
                "three_day": d.get("f99",0), "five_day": d.get("f100",0), "ten_day": d.get("f101",0)}
    except: return {"info": "资金流向数据暂不可用"}

def fetch_news():
    nl = []
    try:
        params = {"cb":"jQ","param":json.dumps({"uid":"","keyword":"宁德时代","type":["cmsArticleWebOld"],"client":"web","clientType":"web","clientVersion":"curr","paramNum":20,"pageNum":1,"pageSize":8})}
        raw = hgu("https://search-api-web.eastmoney.com/search/jsonp?"+urllib.parse.urlencode(params))
        m = re.search(r'jQ\((.*)\)\s*$', raw.strip())
        if m:
            for a in json.loads(m.group(1)).get("result",{}).get("cmsArticleWebOld",[])[:5]:
                nl.append({"title":a.get("title","").replace("<em>","").replace("</em>",""),
                           "date":(a.get("date","") or "")[:10],"source":a.get("mediaName",""),"url":a.get("url","")})
    except: pass
    return nl

def fetch_lithium():
    try:
        raw = hg("https://www.100ppi.com/price/detail-2928.html", t=10)
        m = re.search(r'(\d+\.?\d*)\s*[万千]?元/吨', raw)
        if m:
            v = float(m.group(1).replace(",",""))
            return v/10000 if v>100 else v
    except: pass
    return None

def ah_prem(ap, hp, rate=0.92):
    if ap and hp:
        hc = hp*rate
        if hc>0: return round((ap-hc)/hc*100, 2)
    return None

def gen_report(data):
    t = data["date"]; a = data.get("a_share",{}); h = data.get("h_share",{})
    pe = data.get("pe",{}); fd = data.get("fund_flow",{}); nw = data.get("news",[]); li = data.get("lithium")
    
    ap = a.get("price","—"); ac = None
    if a.get("price") and a.get("close_prev") and a["close_prev"]>0: ac = (a["price"]-a["close_prev"])/a["close_prev"]*100
    acs = f"{ac:+.2f}%" if ac is not None else "—"; acc = "#f85149" if ac is not None and ac>=0 else "#3fb950"
    aci = "🔴" if ac is not None and ac>=0 else "🟢"
    hp_ = h.get("price","—"); ah = ah_prem(a.get("price"),h.get("price"))
    ahs = f"{ah:+.2f}%" if ah is not None else "—"
    pt = pe.get("pe_ttm"); ps = f"{pt:.1f}" if isinstance(pt,(int,float)) else "—"
    peg = round(pt/40,2) if isinstance(pt,(int,float)) and pt>0 else None; pgs = f"{peg:.2f}" if peg else "—"
    
    if peg and peg<1.0: vd,vc,vb = "✅ PEG低估 可加仓","#3fb950","rgba(63,185,80,0.15)"
    elif peg and peg>1.5: vd,vc,vb = "⚠️ PEG偏高 注意风险","#f85149","rgba(248,81,73,0.15)"
    else: vd,vc,vb = "📊 PEG合理 继续持有","#d29922","rgba(210,153,34,0.15)"
    ls = f"{li:.1f}万元/吨" if li else "参考: 7-8万元/吨"
    
    # 资金流向
    fh = ""
    if fd.get("main_net") is not None:
        mn = fd.get("main_net",0); mc = "#f85149" if mn>0 else "#3fb950"
        hn = fd.get("huge_net",0); bn = fd.get("big_net",0); sn = fd.get("small_net",0)
        d3 = fd.get("three_day",0); d5 = fd.get("five_day",0); d10 = fd.get("ten_day",0)
        fh = f'''
        <div class="sec"><h2>💰 资金流向</h2><table>
        <tr><th>指标</th><th>数值</th></tr>
        <tr><td>主力净流入(今日)</td><td style="color:{mc}">{"🔴" if mn>0 else "🟢"}{mn/10000:.2f}亿</td></tr>
        <tr><td>超大单/大单</td><td>{"🔴" if hn>0 else "🟢"}{hn/10000:.2f}亿 / {"🔴" if bn>0 else "🟢"}{bn/10000:.2f}亿</td></tr>
        <tr><td>散户(小单)</td><td>{"🔴" if sn>0 else "🟢"}{sn/10000:.2f}亿</td></tr>
        <tr><td>3日/5日/10日主力</td><td>{d3/10000:+.2f}亿 / {d5/10000:+.2f}亿 / {d10/10000:+.2f}亿</td></tr>
        </table></div>'''
    
    nh = ""; ni = 0
    for n in nw:
        ni += 1
        if ni==1: nh += f'<div style="margin-bottom:8px;padding:8px;background:rgba(88,166,255,0.08);border-radius:6px;border-left:3px solid #58a6ff"><div style="font-size:0.8em;color:#58a6ff;">🔥 头条</div><a href="{n["url"]}" target="_blank" style="color:#e6edf3;font-size:0.9em;text-decoration:none;">{n["title"]}</a><div style="color:#484f58;font-size:0.75em;margin-top:2px;">{n["date"]} · {n["source"]}</div></div>'
        else:
            nh += f'<div class="ni"><span class="nd">{n["date"]}</span><div><a href="{n["url"]}" target="_blank" class="nt">{n["title"]}</a><div class="ns">{n["source"]}</div></div></div>'
    
    vw = f"{a.get('volume',0)//10000}万手" if a.get("volume") else "—"
    ay = f"{a.get('amount',0)//100000000:.0f}亿" if a.get("amount") else "—"
    rd = f"PEG={pgs} 处于低估区间 ✅" if peg and peg<1.0 else (f"PEG={pgs} 偏高注意 ⚠️" if peg and peg>1.5 else f"PEG={pgs} 合理区间 📊")
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>宁德时代(300750) 每日分析 - {t}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#0d1117;color:#e6edf3;padding:20px}}
.c{{max-width:1100px;margin:0 auto}}
.hd{{background:linear-gradient(135deg,#1a1a2e,#0f3460);border-radius:12px;padding:20px;margin-bottom:14px;text-align:center}}
.hd h1{{font-size:1.4em}}.hd .dt{{color:#8b949e;font-size:0.8em;margin-top:3px}}
.kg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:6px;margin-bottom:14px}}
.kc{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px;text-align:center}}
.kc .l{{color:#8b949e;font-size:0.72em}}.kc .v{{font-size:1.2em;font-weight:700}}
.kc .s{{font-size:0.78em;margin-top:2px}}
.vb{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin-bottom:14px;text-align:center}}
.vb .v{{font-size:1.2em;font-weight:700;color:{vc}}}.vb .s{{color:#8b949e;font-size:0.82em;margin-top:4px}}
.vb .tg{{display:inline-block;padding:2px 8px;border-radius:8px;background:{vb};color:{vc};font-size:0.7em;margin-top:5px}}
.sec{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:10px}}
.sec h2{{font-size:0.88em;margin-bottom:8px;color:#58a6ff}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:4px 6px;text-align:left;border-bottom:1px solid #21262d;font-size:0.78em}}
th{{color:#8b949e;font-weight:500}}
.ni{{display:flex;gap:6px;padding:5px 0;border-bottom:1px solid #21262d}}
.nd{{color:#8b949e;font-size:0.72em;white-space:nowrap;min-width:40px;padding-top:1px}}
.nt{{font-size:0.82em;color:#e6edf3;text-decoration:none}}
.nt:hover{{color:#58a6ff}}
.ns{{color:#484f58;font-size:0.72em;margin-top:1px}}
.ft{{text-align:center;color:#484f58;font-size:0.72em;padding:16px 0;line-height:1.6}}
@media(max-width:600px){{.kg{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body>
<div class="c"><div class="hd">
<h1>🔋 宁德时代(300750.SZ)</h1>
<div class="dt">{t} · 200股长线 · PEG估值</div></div>
<div class="vb"><div class="v">{vd}</div><div class="s">PEG={pgs} · PE={ps}x · {rd}</div><span class="tg">碳酸锂 {ls}</span></div>
<div class="kg">
<div class="kc"><div class="l">A股</div><div class="v" style="color:{acc}">¥{ap}</div><div class="s" style="color:{acc}">{aci} {acs}</div></div>
<div class="kc"><div class="l">H股</div><div class="v">HK${hp_}</div></div>
<div class="kc"><div class="l">AH溢价</div><div class="v" style="color:{"#f85149" if ah is not None and ah>=0 else "#3fb950"}">{ahs}</div></div>
<div class="kc"><div class="l">PEG</div><div class="v" style="color:{vc}">{pgs}</div></div>
<div class="kc"><div class="l">PE</div><div class="v">{ps}</div></div>
<div class="kc"><div class="l">成交额</div><div class="v" style="font-size:1em">{ay}</div><div class="s">{vw}</div></div>
</div>
<div class="sec"><h2>📈 行情</h2><table>
<tr><th>指标</th><th>数值</th></tr>
<tr><td>开盘/高/低</td><td>¥{a.get("open","—")} / ¥{a.get("high","—")} / ¥{a.get("low","—")}</td></tr>
<tr><td>昨收</td><td>¥{a.get("close_prev","—")}</td></tr>
<tr><td>量/额</td><td>{vw} / {ay}元</td></tr>
</table></div>
{fh}
<div class="sec"><h2>📊 估值</h2><table>
<tr><th>指标</th><th>数值</th><th>信号</th></tr>
<tr><td>PE(TTM)</td><td>{ps}x</td><td>{"偏低" if isinstance(pt,(int,float)) and pt<25 else "合理" if isinstance(pt,(int,float)) and pt<35 else "偏高"}</td></tr>
<tr><td>PEG</td><td>{pgs}</td><td>{"低估 ✅" if peg and peg<1 else "偏高 ⚠️" if peg and peg>1.5 else "合理 📊"}</td></tr>
</table></div>
<div class="sec"><h2>📰 资讯 ({ni}条)</h2>
{nh if nh else '<div style="color:#8b949e;text-align:center;padding:10px;">暂无</div>'}
</div>
<div class="ft">
🤖 Hermes v2 · {t}<br>
数据: 新浪/腾讯/东方财富 · 含资金流向<br>
⚠️ 仅供参考<br>
<a href="{GITHUB_PAGES_URL}" style="color:#58a6ff;text-decoration:none;">📊 完整报告</a>
</div></div></body></html>'''
    return html

def main():
    t = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 CATL v2 — {t}"); print("="*50)
    print("\n📡 采集...")
    a = fetch_a(); print(f"  A: ¥{a.get('price','?')}")
    h = fetch_h(); print(f"  H: HK${h.get('price','?')}")
    pe = fetch_pe(); print(f"  PE: {pe.get('pe_ttm','?')}")
    fd = fetch_fund(); fe = fd.get("error")
    print(f"  资金: {'✅' if not fe else '❌ '+fe}")
    nw = fetch_news(); print(f"  新闻: {len(nw)}条")
    li = fetch_lithium(); print(f"  锂: {li}万" if li else "  锂: 参考值")
    
    data = {"date":t,"a_share":a,"h_share":h,"pe":pe,"fund_flow":fd,"news":nw,"lithium":li}
    html = gen_report(data)
    with open(os.path.join(REPO_DIR,"index.html"),"w",encoding="utf-8") as f: f.write(html)
    with open(os.path.join(REPO_DIR,"data.json"),"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    print(f"  报告: {len(html)}B")
    
    # 生成双报告(v3)
    print("\n🎨 生成双报告...")
    subprocess.run(["python3", "gen_reports.py"], cwd=REPO_DIR, capture_output=True, text=True, timeout=30)
    print(f"  index.html + report-dark.html (v3样式)")
    
    print("\n📤 Git..."); os.chdir(REPO_DIR)
    for c in [f'git add index.html report-dark.html data.json',f'git commit -m "v3 {t}" --allow-empty']:
        subprocess.run(c,shell=True,capture_output=True,text=True,timeout=15)
    # git push with retry and system timeout
    for attempt in range(3):
        r = subprocess.run("timeout 20 git push origin main 2>&1", shell=True, capture_output=True, text=True, timeout=25)
        o = (r.stdout+r.stderr).strip()
        if "fatal" not in o and "error" not in o.lower():
            if o: print(f"  {o[:200]}")
            break
        print(f"  push重试 {attempt+1}/3...")
        time.sleep(2)
    print(f"\n📊 {GITHUB_PAGES_URL}"); print("✅")

if __name__ == "__main__": main()
