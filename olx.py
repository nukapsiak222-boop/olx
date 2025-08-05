import requests
from bs4 import BeautifulSoup
import time
import re
import threading

SZUKANE_WYRAZENIA = [
    "gtx 1050 ti",
    "gtx1050 ti",
    "gtx 1050ti",
    "gtx 1060",
    "gtx1060",
    "rx 580",
    "rx580",
    "rx 570",
    "rx570",
    "1050ti"
]

CENA_MAX = 110
CZAS_ODSWIEZANIA = 30
widziane_oferty = set()

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1402424311129833504/vXJzzJOhbWpzmOlXDMWmwzA3nEEksGVVjLubzj3kCtaemlKTsH8MdF8msobBuGPG7AVV"
DISCORD_USER_ID = "692071922761990165"

WYLACZENIA = [
    "uszkodz", "niedział", "na części", "na czesci", "nie działa", "nie dziala",
    "zepsut", "spalona", "nie sprawdzona", "niesprawna", "nieznan", "przerobion"
]

def oferta_jest_ok(tytul, opis, cena):
    tekst = f"{tytul.lower()} {opis.lower()}"
    if any(w in tekst for w in WYLACZENIA):
        return False
    if cena is not None and cena > CENA_MAX:
        return False
    return True

def wyciagnij_cene(z_oferty):
    tekst = z_oferty.text.lower()
    wzorzec = re.compile(r'(\d[\d\s]*)(,\d{1,2})?\s*zł')
    match = wzorzec.search(tekst)
    if match:
        liczba_tekst = match.group(1).replace(" ", "")
        grosze = match.group(2)
        try:
            if grosze:
                cena = float(liczba_tekst + grosze.replace(',', '.'))
                return int(round(cena))
            else:
                return int(liczba_tekst)
        except:
            return None
    return None

def wyslij_powiadomienie_discord(tytul, link, cena):
    if not DISCORD_WEBHOOK_URL or not DISCORD_USER_ID:
        return

    dane = {
        "content": f"<@{DISCORD_USER_ID}> 🚨 **Nowa oferta poniżej {CENA_MAX} zł!**\n**{tytul}**\nCena: {cena} zł\n{link}"
    }

    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=dane)
        if r.status_code not in (200, 204):
            print(f"❌ Błąd wysłania webhooka Discord: {r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ Wyjątek przy wysyłaniu webhooka Discord: {e}")

def znajdz_nowe_oferty(url):
    global widziane_oferty

    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"\n❌ Błąd pobierania: {e}")
        return []

    oferty = soup.find_all("div", class_="css-1sw7q4x")
    nowe_oferty = []

    for oferta in oferty:
        link_tag = oferta.find("a")
        if not link_tag:
            continue
        link = "https://www.olx.pl" + link_tag['href']
        tytul = link_tag.text.strip()

        if link in widziane_oferty:
            continue

        cena = wyciagnij_cene(oferta)
        opis = oferta.text

        print(f"Oferta: {tytul} | Cena: {cena}")

        if oferta_jest_ok(tytul, opis, cena):
            nowe_oferty.append((tytul, link, cena))
            widziane_oferty.add(link)

            if cena is not None and cena <= CENA_MAX:
                wyslij_powiadomienie_discord(tytul, link, cena)

    return nowe_oferty

def main_loop():
    print(f"🔍 Monitoruję OLX dla fraz: {', '.join(SZUKANE_WYRAZENIA)} (max {CENA_MAX} zł, bez uszkodzonych)")
    while True:
        znalezione = []
        for fraza in SZUKANE_WYRAZENIA:
            url = f"https://www.olx.pl/oferty/q-{fraza.replace(' ', '-')}/"
            nowe = znajdz_nowe_oferty(url)
            znalezione.extend(nowe)

        if znalezione:
            print(f"\n✅ NOWE DOPASOWANE OFERTY ({len(znalezione)}):")
            for tytul, link, cena in znalezione:
                cena_wyswietl = f"{cena} zł" if cena is not None else "brak ceny"
                print(f" - {tytul} ({cena_wyswietl})\n   {link}")
        else:
            print(".", end="", flush=True)

        time.sleep(CZAS_ODSWIEZANIA)

if __name__ == "__main__":
    main_loop()
