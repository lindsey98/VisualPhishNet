
from selenium import webdriver
import requests
import os
from urllib.parse import urlparse
from shutil import rmtree
from selenium.common.exceptions import *
import re
from bs4 import BeautifulSoup


def write_file(path, contents):
    with open(path, "w+", encoding='utf-8') as f:
        f.write(contents)
    f.close()


# Function to recursively remove a particular path (folder)
def remove_folder(path):
    if len(os.listdir(path)) == 0:
        rmtree(path)

# Sanitizing domain to remove unwanted characters that are cannot be used to create file path
def clean_domain(domain, deletechars):
    for c in deletechars:
        domain = domain.replace(c, '')
    return domain


# Add more rules to check for redirect?
def check_redirect(url):
    try:
        resp = requests.get(url, timeout=30)
        status_code = resp.history
        # Even if successful, check if theres a redirect by checking javascript injects
        if "200" in str(resp):
            if status_code == []:
                # The website coder shouldn't modify the window.location.href unless its an inject?
                if "window.location.href" in resp.text:
                    find_url = re.findall(
                        'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', resp.text)
                    if find_url:
                        print("[*] WARNING: Redirection via JS inject from " + url + " to " + "".join(find_url))
                        return "".join(find_url)
                else:
                    print("[*] No Redirection")
                    return url

            elif "200" in str(status_code):
                # No redirection
                print("[*] No Redirection")
                return url

        # Check for normal redirection with resp.history
        if ("301" in str(status_code) or "302" in str(status_code)):
            print("[*] Redirected from " + url + " to " + resp.url)
            return resp.url
    except Exception:
        print("[*] Failed to check redirect")
        print("[*] Website might be dead!")
        return None

############################################################################################
# MAIN CODE #
############################################################################################

def main(url, output):
    # Check if domain re-directs
    # TO DO: Perhaps change to a status code instead
    url_to_check = check_redirect(url)

    if url_to_check is None:
        return (None, None, None)

    # Instantiating folder paths to save documents to
    domain = clean_domain(urlparse(url_to_check).netloc, '\/:*?"<>|')
    output_folder = os.path.join(output, domain)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)

    # Initializing chrome driver settings to run headless, windows resolution etc.
    chromedriver = "./code/train/chromedriver.exe"
    chrome_driver_options = initialize_chrome_settings()

    try:
        driver = webdriver.Chrome(chromedriver, options=chrome_driver_options)
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        print("Session is created!")
    except SessionNotCreatedException as snce:
        remove_folder(output_folder)
        driver.quit()
        print("Session not Created!")
        return (None, None, None)

    screenshot_path = os.path.join(output_folder, "shot.png")
    info_path = os.path.join(output_folder, "info.txt")
    html_path = os.path.join(output_folder, "html.txt")

    try:
        req = requests.get(url_to_check, verify=False, timeout=30)
        req.raise_for_status()
        status_code = req.status_code
        if status_code != 200:
            remove_folder(output_folder)
            driver.quit()
            return (None, None, None)
    except Exception:
        print("Error!, removing folder: " + output_folder)
        remove_folder(output_folder)
        driver.quit()
        return (None, None, None)

    # If webpage is alive, get selenium to load the webpage!
    try:
        driver.get(url_to_check)
    except Exception:
        print("Unable to get website, cant save_screenshot")
        remove_folder(output_folder)
        driver.quit()
        return (None, None, None)

    # Extracting information that is required for SIFT
    # Screenshot, HTML code and URL
    try:
        driver.save_screenshot(screenshot_path)
        content = driver.page_source
        url_landed = driver.current_url
        write_file(html_path, content)
        write_file(info_path, url_landed)

    except Exception:
        remove_folder(output_folder)
        driver.quit()
        return (None, None, None)

    return url, url_to_check, output_folder


# --start-maximized may not work so well because headless does not recognize resolution size
# therefore, windowsize has to be explicitly specified
def initialize_chrome_settings():
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument("--start-maximized")
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--enable-javascript")
    options.add_argument("--disable-gpu")

    return options

def getLinks(soup):
    links = []

    for link in soup.findAll('a', attrs={'href': re.compile("^http")}):
        links.append(link.get('href'))

    links = list(set(links))
    return links

# Only uncomment this for individual script testing!
if __name__ == "__main__":
    for brand in os.listdir('./targetlist_fit'):
        if os.path.exists(os.path.join('./targetlist_fit', brand, 'login_html.txt')):
            content = open(os.path.join('./targetlist_fit', brand, 'login_html.txt'), encoding='utf-8').read()
            soup = BeautifulSoup(content, "lxml")
            urls = getLinks(soup)
            for url in urls:
                main(url, os.path.join('./targetlist_fit', brand, 'screenshots'))

        elif os.path.exists(os.path.join('./targetlist_fit', brand, 'homepage_html.txt')):
            content = open(os.path.join('./targetlist_fit', brand, 'homepage_html.txt'), encoding='utf-8').read()
            soup = BeautifulSoup(content, "lxml")
            urls = getLinks(soup)
            for url in urls:
                main(url, os.path.join('./targetlist_fit', brand, 'screenshots'))

        else:
            print('No html has found for brand %s'%brand)
