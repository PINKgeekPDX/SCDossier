import requests
from bs4 import BeautifulSoup

def debug():
    headers = {"User-Agent": "SCDossier/1.0"}
    resp = requests.get("https://robertsspaceindustries.com/en/citizens/PINKgeekPDX/organizations", headers=headers)
    soup = BeautifulSoup(resp.text, "lxml")
    
    for org in soup.select(".orgs-content .org"):
        print(f"Org block classes: {org.get('class')}")
        print(org.prettify()[:200])

if __name__ == "__main__":
    debug()
