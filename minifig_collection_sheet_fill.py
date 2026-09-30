### 
# OKAY SO i been redoing this for v2 but i lowkey forgot about BS4 which i absolutely should be using so
# im going to stop while im ahead and reincorporate beautiful soup because selenium is pissing me off
###

# html parsing and browser surfing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import sys
import re
import time
import argparse
import os

# using .env 
from dotenv import load_dotenv
import os

# login (semi)persistence so I don't have to do 2FA every goddamn time
profile_dir = os.path.abspath("C:\\Users\\Tyler Jones\\Projects\\BrickLink\\minifig_sheet_fill_v2\\selenium_profile")

# url to collection page. will redirect to the login page if you haven't signed in recently
collection_url = "https://www.bricklink.com/v3/myCollection/main.page?q=&itemType=M&page=1"

# login function. called if -l/--login flag is present. part automatic and part manual entry
def login():

    # load .env file to access username and password
    load_dotenv()

    # create driver and load login page
    driver = make_driver()
    driver.get(collection_url)
    time.sleep(0.5)

    # find username entry field and populate it with username from .env file
    username_field = driver.find_element(By.ID, "username")
    username = os.getenv("UNAME")
    username_field.send_keys(username)

    # find continue button after entering username and click it
    time.sleep(0.5)
    continue_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
    driver.execute_script("arguments[0].click();", continue_button)
    time.sleep(0.5)

    # find password entry field and populate it with password from .enf file
    password_field = driver.find_element(By.ID, "password")
    password = os.getenv("PASSWD")
    password_field.send_keys(password)

    # find sign in button after entering the password and click it
    sign_in_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
    driver.execute_script("arguments[0].click();", sign_in_button)

    # wait until the page finishes logging in
    WebDriverWait(driver, 180).until(
        lambda d: "myCollection" in d.current_url and "identity.lego.com" not in d.current_url
    )
    time.sleep(3)

    driver.quit()

# function for checking if i'm already logged in
def is_logged_in(driver):

    # open My Collection page (or login page if not logged in)
    driver.get(collection_url)
    time.sleep(3)

    # return True if url contains myCollection and does NOT contain identity.lego.com
    return "myCollection" in driver.current_url and "identity.lego.com" not in driver.current_url

# function for making the driver
def make_driver():

    # configure driver to use user data directory with login shit idrk
    # note to self if chrome is crashing just go into task manager and kill any existing chrome tasks
    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--disable-dev-shm-usage") 
    options.add_argument("--no-sandbox") 
    #options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)

def get_minifigure_info(minifigure):

    # name of minifigure. e.g, Zane - The Golden Weapons or Zane (Jungle Robe) - Tournament of Elements or Clone Captain Vaughn, 501st Legion, 332nd Company (Phase 2) - Helmet with Holes and Togruta Markings, Orange Visor (this one is ridiculous but you get the point)
    minifigure_name = minifigure.find(class_="text--bold l-cursor-pointer").text

    # minifigure picture used on BrickLink. formatted to automatically work in sheets. e.g., default url = //img.bricklink.com/ItemImage/MN/0/njo0001.png and formatted url = "img.bricklink.com/ItemImage/MN/0/njo0001.png"
    minifigure_image_url = minifigure.find(class_="personal-inventory__list-thumb-img").get('src')
    if minifigure_image_url:
        minifigure_image_url = f'"{minifigure_image_url[2::]}"'

    # quantity of minifigure owned
    minifigure_qty_container = minifigure.find(class_="personal-inventory__list-item-list-cell--qty")
    if minifigure_qty_container:
        input_tag = minifigure_qty_container.find('input', class_='text-input text--center personal-inventory__list-qty')
        if input_tag and input_tag.has_attr('value'):
            minifigure_quantity = input_tag['value']

    # condition of minifigure. e.g, New or Used
    minifigure_condition = minifigure.find(class_="personal-inventory__list-item-list-cell--cond").text

    # theme and subtheme (if applicable) of minifigure. e.g., Theme = NINJAGO and Subtheme = The Golden Weapons or Theme = Super Heroes and Subtheme = The Batman
    minifigure_theme_container = minifigure.find(class_="personal-inventory__item-category text--small").text
    if minifigure_theme_container:
        if ":" in minifigure_theme_container:
            split_themes = minifigure_theme_container.split(":")
            minifigure_theme = split_themes[0].strip()
            minifigure_subtheme = split_themes[1].strip()
        else:
            minifigure_theme = minifigure_theme_container.strip()
            minifigure_subtheme = "None"

    # minifigure id (unique to BrickLink). e.g, njo0001, sw0527a, sh0038
    minifigure_id = minifigure.find(class_="text--small text--center l-margin-top--sm text--break-word l-cursor-pointer").text

    # any notes i added to the "Add notes" field on the collection page
    minifigure_notes = minifigure.find('div', class_="personal-inventory__cell--note l-margin-top--sm personal-inventory__note-field").text
    if minifigure_notes.strip() == "Add notes":
        minifigure_notes = ""
    else:
        minifigure_notes = minifigure_notes[:-4:]

    return minifigure_name, minifigure_image_url, minifigure_quantity, minifigure_condition, minifigure_theme, minifigure_subtheme, minifigure_id, minifigure_notes

def get_year_and_price(driver, minifigure_id):

    # url specifically selects Price Guide section
    minifigure_catalogue_url = f"https://www.bricklink.com/v2/catalog/catalogitem.page?M={minifigure_id}#T=P"

    driver.get(minifigure_catalogue_url)

    time.sleep(5)

    driver.quit()



def main():

    # argparse to allow for login flag
    parser = argparse.ArgumentParser(description="Input Arguments")
    parser.add_argument("-l", "--login", action="store_true", help="bool for manual login")
    args = parser.parse_args()
    manual_login = args.login

    # if login flag is present then run login function
    if manual_login == True:
        login()

    driver = make_driver()

    driver.get(collection_url)

    if not is_logged_in(driver):
        driver.quit()
        raise SystemExit("Not logged in. Run again with --login.")

    # time.sleep(0.5)
    # my_minifigures_btn = driver.find_element(By.ID, "MPI-nav-myMinifigures")
    # driver.execute_script("arguments[0].click();", my_minifigures_btn)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'listItemView-0'))
    )

    time.sleep(0.5)

    # source all html for the minifigure collection page
    minifig_collection_soup = BeautifulSoup(driver.page_source, 'html.parser')

    # source all minifigure list items 
    all_listItemViews = minifig_collection_soup.find_all(id=re.compile(r'^listItemView-\d+'))

    # retrieve basic minifigure information available directly from the minifigure collection page as well as price and year released from the minifigure specific catalogue page
    for minifigure in all_listItemViews:
        list_item_id = minifigure.get_attribute_list('id')

        minifigure = minifig_collection_soup.find(id=str(list_item_id[0]))

        minifigure_name, minifigure_image_url, minifigure_quantity, minifigure_condition, minifigure_theme, minifigure_subtheme, minifigure_id, minifigure_notes = get_minifigure_info(minifigure=minifigure)
        minifigure_release_year, minifigure_avg_sell_price = get_year_and_price(driver=driver, minifigure_id=minifigure_id)

        # print(minifigure_name)
        # print(minifigure_image_url)
        # print(minifigure_theme)
        # print(minifigure_subtheme)
        # print(minifigure_condition)
        # print(minifigure_quantity)
        # print(minifigure_id)
        # print(minifigure_notes)

        break

    time.sleep(3)
    driver.quit()

main()