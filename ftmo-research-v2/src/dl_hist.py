"""Descarga M1 ASCII de HistData.com (hora EST fija, sin DST) por año o por mes."""
import sys, re, os, time, subprocess
OUT = "/home/user/data2/hist"
def get(pair, year, month=None):
    tag = f"{pair}_{year}" + (f"{month:02d}" if month else "")
    f = f"{OUT}/{tag}.zip"
    if os.path.exists(f) and os.path.getsize(f) > 10000: return f
    page = f"https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair.lower()}/{year}" + (f"/{month}" if month else "")
    html = subprocess.run(["curl", "-s", "-c", "/tmp/hc", page], capture_output=True, text=True).stdout
    tk = re.search(r'id="tk" value="([0-9a-f]+)"', html)
    if not tk: print("no tk", tag); return None
    dm = re.search(r'id="datemonth" value="(\d+)"', html).group(1)
    subprocess.run(["curl", "-s", "-b", "/tmp/hc", "-o", f, "-H", f"Referer: {page}", "-X", "POST",
                    "-d", f"tk={tk.group(1)}&date={year}&datemonth={dm}&platform=ASCII&timeframe=M1&fxpair={pair}",
                    "https://www.histdata.com/get.php"])
    print(tag, os.path.getsize(f), flush=True); time.sleep(1)
    return f
if __name__ == "__main__":
    for pair in sys.argv[1:]:
        for y in range(2016, 2026): get(pair, y)
        for m in range(1, 11): get(pair, 2026, m)
