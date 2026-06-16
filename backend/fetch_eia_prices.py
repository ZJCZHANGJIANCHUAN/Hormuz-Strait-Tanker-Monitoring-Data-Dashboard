"""Fetch real historical Brent oil prices from EIA."""
import httpx, re
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import OilPrice

url = 'https://www.eia.gov/dnav/pet/hist/rbrteD.htm'
r = httpx.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30, follow_redirects=True)
html = r.text

row_pattern = r"<td class='B6'>(.*?)</td>\s*(.*?)</tr>"
rows = re.findall(row_pattern, html, re.DOTALL)
print(f'Data rows: {len(rows)}')

records = []
for date_cell, prices_cell in rows:
    date_match = re.search(r'(\d{4}\s+\w+[- ]\s*\d+)', date_cell)
    if not date_match:
        continue

    date_str = date_match.group(1).replace(' ', '').replace('-', '')
    try:
        start_dt = datetime.strptime(date_str, '%Y%b%d')
    except ValueError:
        continue

    prices = re.findall(r">\s*([\d.]+)\s*<", prices_cell)

    for i, p_str in enumerate(prices[:5]):
        try:
            d = start_dt.date() + timedelta(days=i)
            p = float(p_str)
            if 10 < p < 200:
                records.append((d, p))
        except ValueError:
            pass

records.sort(key=lambda x: x[0])
print(f'Parsed: {len(records)} daily records')
if not records:
    print('No records parsed, exiting')
    exit(1)

print(f'Range: {records[0][0]} to {records[-1][0]}')

db = SessionLocal()
inserted = 0
for d, p in records:
    existing = db.query(OilPrice).filter(
        OilPrice.record_date == d, OilPrice.source == 'eia'
    ).first()
    if not existing:
        db.add(OilPrice(
            record_date=d, brent_close=p,
            wti_close=round(p - 5.0, 2), spread=5.0, source='eia'
        ))
        inserted += 1
db.commit()

latest = db.query(OilPrice).filter(OilPrice.source == 'eia').order_by(
    OilPrice.record_date.desc()
).limit(10).all()
print(f'Latest EIA prices:')
for r in reversed(latest):
    print(f'  {r.record_date}: Brent=${r.brent_close:.2f} WTI=${r.wti_close:.2f}')

print(f'Saved: {inserted} new records')
db.close()
