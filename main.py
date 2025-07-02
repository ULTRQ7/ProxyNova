import os
import sys
import ctypes
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import time

def display_banner():
    banner = """
██╗░░░██╗██╗░░░░░████████╗██████╗░░██████╗░
██║░░░██║██║░░░░░╚══██╔══╝██╔══██╗██╔═══██╗
██║░░░██║██║░░░░░░░░██║░░░██████╔╝██║██╗██║
██║░░░██║██║░░░░░░░░██║░░░██╔══██╗╚██████╔╝
╚██████╔╝███████╗░░░██║░░░██║░░██║░╚═██╔═╝░
░╚═════╝░╚══════╝░░░╚═╝░░░╚═╝░░╚═╝░░░╚═╝░░░

⚡ Proxy Tester • Multi-core • Real-time Progress

"""
    print(banner)

def set_console_title(title: str):
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    else:
        sys.stdout.write(f'\33]0;{title}\a')
        sys.stdout.flush()

def fetch_proxies():
    """
    1) Try ProxyScrape API with retry/backoff
    2) On failure, fall back to scraping free-proxy-list.net
    """
    api_url = (
        "https://api.proxyscrape.com/v2/"
        "?request=getproxies&protocol=http&timeout=10000&country=all"
    )

    # setup session with retries
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        resp = session.get(api_url, timeout=10)
        resp.raise_for_status()
        lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Empty proxy list from API")
        return [f"http://{ip}" for ip in lines]
    except Exception as e:
        print(f"⚠️ Proxy API failed ({e}), falling back to HTML scrape…")

    # fallback: scrape free-proxy-list.net
    html_url = "https://free-proxy-list.net/"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = session.get(html_url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", id="proxylisttable")
    if not table or not table.tbody:
        raise RuntimeError("Fallback scrape failed—table not found")

    proxies = []
    for row in table.tbody.find_all("tr"):
        cols = row.find_all("td")
        ip, port, https_flag = cols[0].text, cols[1].text, cols[6].text.lower()
        scheme = "https" if https_flag == "yes" else "http"
        proxies.append(f"{scheme}://{ip}:{port}")
    return proxies

def test_proxy(proxy, test_url="http://httpbin.org/ip", timeout=5):
    try:
        r = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=timeout)
        return r.status_code == 200
    except:
        return False

def check(proxy):
    return proxy, test_proxy(proxy)

def main():
    display_banner()
    print("🔍 Fetching proxies…")
    proxies = fetch_proxies()
    total = len(proxies)
    print(f"⚡ Retrieved {total} proxies. Testing now…\n")

    working = []

    main_bar = tqdm(
        total=total, unit="prx", desc="Testing",
        ncols=80, position=0, colour="red"
    )
    work_bar = tqdm(
        total=total, unit="ok", desc="Working",
        ncols=80, position=1, colour="green",
        bar_format='{desc}: {n_fmt}/{total_fmt} |{bar}|'
    )

    with Pool(processes=cpu_count() * 2) as pool:
        for proxy, ok in pool.imap_unordered(check, proxies, chunksize=1):
            main_bar.set_description(f"Testing {proxy}")
            main_bar.update(1)
            if ok:
                working.append(proxy)
                work_bar.update(1)

            title = f"Testing {main_bar.n}/{total} | Working {work_bar.n}/{total}"
            set_console_title(title)

    main_bar.close()
    work_bar.close()

    # save results
    with open("proxies.txt", "w") as f:
        for p in working:
            f.write(p + "\n")

    print(f"\n✅ {len(working)}/{total} proxies working.")
    print("📁 Saved to proxies.txt")

if __name__ == "__main__":
    start = time.time()
    main()
    print(f"\n⏱️ Finished in {time.time() - start:.1f}s")

    # force pause on exit
    try:
        input("\n🔒 Press Enter to exit…")
    except:
        pass



#
#████████████████████████████████████████████████████████████████████████████████████████████████████
#█░░░░░░██░░░░░░█░░░░░░█████████░░░░░░░░░░░░░░█░░░░░░░░░░░░░░░░███░░░░░░░░░░░░░░███░░░░░░░░░░░░░░████
#█░░▄▀░░██░░▄▀░░█░░▄▀░░█████████░░▄▀▄▀▄▀▄▀▄▀░░█░░▄▀▄▀▄▀▄▀▄▀▄▀░░███░░▄▀▄▀▄▀▄▀▄▀░░███░░▄▀▄▀▄▀▄▀▄▀░░████
#█░░▄▀░░██░░▄▀░░█░░▄▀░░█████████░░░░░░▄▀░░░░░░█░░▄▀░░░░░░░░▄▀░░███░░▄▀░░░░░░▄▀░░███░░░░░░░░░░▄▀░░████
#█░░▄▀░░██░░▄▀░░█░░▄▀░░█████████████░░▄▀░░█████░░▄▀░░████░░▄▀░░███░░▄▀░░██░░▄▀░░███████████░░▄▀░░████
#█░░▄▀░░██░░▄▀░░█░░▄▀░░█████████████░░▄▀░░█████░░▄▀░░░░░░░░▄▀░░███░░▄▀░░██░░▄▀░░███████████░░▄▀░░████
#█░░▄▀░░██░░▄▀░░█░░▄▀░░█████████████░░▄▀░░█████░░▄▀▄▀▄▀▄▀▄▀▄▀░░███░░▄▀░░██░░▄▀░░███████████░░▄▀░░████
#█░░▄▀░░██░░▄▀░░█░░▄▀░░█████████████░░▄▀░░█████░░▄▀░░░░░░▄▀░░░░███░░▄▀░░██░░▄▀░░███████████░░▄▀░░████
#█░░▄▀░░██░░▄▀░░█░░▄▀░░█████████████░░▄▀░░█████░░▄▀░░██░░▄▀░░█████░░▄▀░░██░░▄▀░░███████████░░▄▀░░████
#█░░▄▀░░░░░░▄▀░░█░░▄▀░░░░░░░░░░█████░░▄▀░░█████░░▄▀░░██░░▄▀░░░░░░█░░▄▀░░░░░░▄▀░░░░█████████░░▄▀░░████
#█░░▄▀▄▀▄▀▄▀▄▀░░█░░▄▀▄▀▄▀▄▀▄▀░░█████░░▄▀░░█████░░▄▀░░██░░▄▀▄▀▄▀░░█░░▄▀▄▀▄▀▄▀▄▀▄▀░░█████████░░▄▀░░████
#█░░░░░░░░░░░░░░█░░░░░░░░░░░░░░█████░░░░░░█████░░░░░░██░░░░░░░░░░█░░░░░░░░░░░░░░░░█████████░░░░░░████
#████████████████████████████████████████████████████████████████████████████████████████████████████
#████████████████████████████████████████████████████████████████████████████
#█░░░░░░░░░░░░░░█░░░░░░░░░░░░░░█░░░░░░░░░░░░░░█░░░░░░░░░░░░░░█░░░░░░░░░░░░░░█
#█░░▄▀▄▀▄▀▄▀▄▀░░█░░▄▀▄▀▄▀▄▀▄▀░░█░░▄▀▄▀▄▀▄▀▄▀░░█░░▄▀▄▀▄▀▄▀▄▀░░█░░▄▀▄▀▄▀▄▀▄▀░░█
#█░░▄▀░░░░░░░░░░█░░░░░░▄▀░░░░░░█░░░░░░░░░░▄▀░░█░░░░░░░░░░▄▀░░█░░░░░░░░░░▄▀░░█
#█░░▄▀░░█████████████░░▄▀░░█████████████░░▄▀░░█████████░░▄▀░░█████████░░▄▀░░█
#█░░▄▀░░░░░░░░░░█████░░▄▀░░█████████████░░▄▀░░█████████░░▄▀░░█████████░░▄▀░░█
#█░░▄▀▄▀▄▀▄▀▄▀░░█████░░▄▀░░█████████████░░▄▀░░█████████░░▄▀░░█████████░░▄▀░░█
#█░░▄▀░░░░░░░░░░█████░░▄▀░░█████████████░░▄▀░░█████████░░▄▀░░█████████░░▄▀░░█
#█░░▄▀░░█████████████░░▄▀░░█████████████░░▄▀░░█████████░░▄▀░░█████████░░▄▀░░█
#█░░▄▀░░░░░░░░░░█████░░▄▀░░█████████████░░▄▀░░█████████░░▄▀░░█████████░░▄▀░░█
#█░░▄▀▄▀▄▀▄▀▄▀░░█████░░▄▀░░█████████████░░▄▀░░█████████░░▄▀░░█████████░░▄▀░░█
#█░░░░░░░░░░░░░░█████░░░░░░█████████████░░░░░░█████████░░░░░░█████████░░░░░░█
#████████████████████████████████████████████████████████████████████████████
#