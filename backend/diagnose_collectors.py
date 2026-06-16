"""
Diagnostic script to test each collector with real external APIs.
Run: python diagnose_collectors.py
"""
import asyncio
import logging
import httpx
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("diagnose")

# Test URLs and expected behavior per collector
TESTS = {
    "PortWatch - Strait": {
        "url": (
            "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
            "Daily_Chokepoints_Data/FeatureServer/0/query"
            "?where=portid%3D%27chokepoint_strait_of_hormuz%27"
            "&outFields=*&f=json&resultRecordCount=1&orderByFields=date+DESC"
        ),
        "expected": "features",
        "note": "IMF PortWatch 海峡数据 (免费)",
    },
    "PortWatch - Ports": {
        "url": (
            "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
            "Daily_Ports_Data/FeatureServer/0/query"
            "?where=portid%3D%27IRKHK%27"
            "&outFields=*&f=json&resultRecordCount=1&orderByFields=date+DESC"
        ),
        "expected": "features",
        "note": "IMF PortWatch 港口数据 (免费)",
    },
    "Oil Price - yfinance (Brent)": {
        "type": "yfinance",
        "symbol": "BZ=F",
        "note": "Yahoo Finance 布伦特原油期货 (免费)",
    },
    "Oil Price - yfinance (WTI)": {
        "type": "yfinance",
        "symbol": "CL=F",
        "note": "Yahoo Finance WTI 原油期货 (免费)",
    },
    "NASA FIRMS (no key)": {
        "url": (
            "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            "demo/VIIRS_SNPP_NRT/48.0,24.0,58.0,30.5/1"
        ),
        "expected": "latitude",
        "note": "NASA FIRMS 火点 (path格式, 免费key: demo或注册)",
    },
    "UKMTO Website": {
        "url": "https://www.ukmto.org/indian-ocean/recent-incidents",
        "expected_status": 200,
        "expected_keyword": "incident",
        "note": "UKMTO 安全事件 (HTML 页面)",
    },
}


async def test_http(url: str, name: str, expected: str) -> dict:
    """Generic HTTP test."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None

            if data and expected in str(data):
                count = len(data.get("features", [])) if data else 0
                return {"status": "OK", "detail": f"JSON 响应正常", "records_sample": count}
            elif data:
                return {"status": "OK", "detail": f"JSON 响应，但未找到 '{expected}' 字段", "keys": list(data.keys())[:5]}
            elif resp.status_code == 200:
                return {"status": "OK", "detail": f"HTTP 200, {len(resp.text)} 字符"}
            else:
                return {"status": "FAIL", "detail": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        return {"status": "BLOCKED", "detail": "连接失败，可能需要代理"}
    except Exception as e:
        return {"status": "ERROR", "detail": str(e)[:100]}


async def test_yfinance(symbol: str) -> dict:
    """Test yfinance data fetch."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = await asyncio.to_thread(ticker.history, period="5d")
        if hist.empty:
            return {"status": "FAIL", "detail": f"{symbol} 返回空数据"}
        last = hist.iloc[-1]
        return {
            "status": "OK",
            "detail": f"Close={last['Close']:.2f}, Vol={last['Volume']:.0f}",
            "latest_date": str(hist.index[-1].date()),
        }
    except ImportError:
        return {"status": "ERROR", "detail": "yfinance 未安装"}
    except Exception as e:
        return {"status": "ERROR", "detail": str(e)[:120]}


async def test_csv_api(url: str, keyword: str) -> dict:
    """Test CSV API (FIRMS)."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and keyword in resp.text:
                lines = resp.text.strip().split("\n")
                return {"status": "OK", "detail": f"CSV 数据正常, {len(lines)-1} 行数据"}
            elif resp.status_code == 200:
                return {"status": "WARN", "detail": f"HTTP 200 但未找到 '{keyword}'，可能缺少 API Key"}
            else:
                return {"status": "FAIL", "detail": f"HTTP {resp.status_code}: {resp.text[:100]}"}
    except Exception as e:
        return {"status": "ERROR", "detail": str(e)[:120]}


async def main():
    print("=" * 70)
    print("  霍尔木兹监测系统 — 数据采集器诊断")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {}

    # HTTP tests
    for name, cfg in TESTS.items():
        if cfg.get("type") == "yfinance":
            print(f"\n⏳ {name} ({cfg['note']})...")
            result = await test_yfinance(cfg["symbol"])
        elif "csv" in cfg.get("url", ""):
            print(f"\n⏳ {name} ({cfg['note']})...")
            result = await test_csv_api(cfg["url"], cfg.get("expected_keyword", ""))
        else:
            print(f"\n⏳ {name} ({cfg['note']})...")
            result = await test_http(cfg["url"], name, cfg.get("expected", ""))

        results[name] = result
        icon = "✅" if result["status"] == "OK" else "⚠️" if result["status"] == "WARN" else "❌"
        print(f"  {icon} [{result['status']}] {result['detail']}")

    # Summary
    ok = sum(1 for r in results.values() if r["status"] == "OK")
    warn = sum(1 for r in results.values() if r["status"] == "WARN")
    fail = sum(1 for r in results.values() if r["status"] in ("FAIL", "BLOCKED", "ERROR"))
    total = len(results)

    print("\n" + "=" * 70)
    print(f"  诊断结果: ✅ {ok} 正常 | ⚠️ {warn} 警告 | ❌ {fail} 异常 (共 {total} 项)")
    if fail:
        print("  ⚠️  存在异常采集器，需要修复后才能保证数据准确性")
    else:
        print("  ✅ 所有采集器正常，数据链路可用")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
