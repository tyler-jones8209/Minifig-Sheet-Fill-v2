### 
# OKAY SO it works sort of but two things:
# 1: when i push to the google sheet, every subsequent row after the first is one index too far to the right (cumulative)
# 2: some strings when pushed to the sheet like the image url, release year, and quantity have this annoying "'" at the beginning of the string which completely nukes the image function so gotta figure that out
###

# html parsing and browser surfing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import time
import argparse
import os

# using .env 
from dotenv import load_dotenv
import os

# sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
    options.add_argument("--headless=new")
    #options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)

def get_year_and_price(driver, minifigure_id, minifigure_condition):

    # url specifically selects Price Guide section
    minifigure_catalogue_url = f"https://www.bricklink.com/v2/catalog/catalogitem.page?M={minifigure_id}#T=P"

    # open url. short wait before scraping 
    driver.get(minifigure_catalogue_url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'pcipgSummaryTable'))
    )

    # source all html for the minifigure catalogue page
    minifigure_soup = BeautifulSoup(driver.page_source, 'html.parser')

    # scrape release year of minifigure using convenient id directly on the year
    year_released = None
    year_released_text = minifigure_soup.find(id="yearReleasedSec")
    year_released = year_released_text.text.strip()

    # fallback if year placeholder is not overwritten
    if not year_released:
        year_released = "Not Found"

    # create list of all tables matching the class. should be 4 tables: New and Used for Last 6 Months Sales and New and Used for Current Items for Sale
    price_tables = minifigure_soup.find_all('table', class_="pcipgSummaryTable")

    # configure which table index to use based on the minifigure condition which is passed to the function
    use_table = None
    if minifigure_condition.lower() == "used":
        use_table = price_tables[1]
    else:
        use_table = price_tables[0]

    # scrape minifigure price from specifc table chosen. available prices for each table include: Min Price, Avg Price (one i want), Qty Avg Price, and Max Price
    minifigure_price = None
    if use_table:
        for row in use_table.find('tbody').find_all('tr'):
            if "avg price:" in row.text.lower() and "qty" not in row.text.lower(): # filter out Qty Avg Price (you can use indexing instead of text matching, probably better tbh)
                price_text = row.find('b').text.split('$')[1]
                minifigure_price = f"{float(price_text):.2f}"

    # fallback for minifigure price
    if not minifigure_price:
        minifigure_price = float(0.00)

    return year_released, minifigure_price

def get_minifigure_info(driver):

    full_minifigure_info = []

    # source all html for the minifigure collection page
    minifig_collection_soup = BeautifulSoup(driver.page_source, 'html.parser')

    # source all minifigure list items 
    all_listItemViews = minifig_collection_soup.find_all(id=re.compile(r'^listItemView-\d+'))

    # retrieve basic minifigure information available directly from the minifigure collection page as well as price and year released from the minifigure specific catalogue page
    for minifigure in all_listItemViews:
        list_item_id = minifigure.get_attribute_list('id')

        minifigure = minifig_collection_soup.find(id=str(list_item_id[0]))

        # name of minifigure. e.g, Zane - The Golden Weapons or Zane (Jungle Robe) - Tournament of Elements or Clone Captain Vaughn, 501st Legion, 332nd Company (Phase 2) - Helmet with Holes and Togruta Markings, Orange Visor (this one is ridiculous but you get the point)
        minifigure_name = minifigure.find(class_="text--bold l-cursor-pointer").text

        # minifigure picture used on BrickLink. formatted to automatically work in sheets. e.g., default url = //img.bricklink.com/ItemImage/MN/0/njo0001.png and formatted url = "img.bricklink.com/ItemImage/MN/0/njo0001.png"
        minifigure_image_url = minifigure.find(class_="personal-inventory__list-thumb-img").get('src')
        if minifigure_image_url:
            minifigure_image_url = f'=IMAGE("{minifigure_image_url[2::]}")'

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

        minifigure_release_year, minifigure_avg_sell_price = get_year_and_price(driver=driver, minifigure_id=minifigure_id, minifigure_condition=minifigure_condition)

        full_minifigure_info.append([minifigure_image_url, minifigure_name, minifigure_id, minifigure_theme, minifigure_subtheme, minifigure_release_year, minifigure_condition, minifigure_avg_sell_price, minifigure_quantity, minifigure_notes])

    return full_minifigure_info

# function to populate a chosen google sheet
def fill_google_sheet(minifig_info):

    # define permissions for reading/writing Google Sheets and accessing Google Drive
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # load information stored in JSON file
    account_credentials = ServiceAccountCredentials.from_json_keyfile_name('c:/Users/Tyler Jones/Projects/Python/Finances/logical-veld-439501-v7-8119ef621faf.json', scope)
    
    client = gspread.authorize(account_credentials)

    # get first worksheet stored in 'Minifigure Collection v2'
    # NOTE TO SELF when you add a new sheet you have to go into the sheet, hit share, and add your service access account as editor
    sheet = client.open("Minifigure Collection v2").sheet1

    # clear all cells from A2:I1000 (skipping the header row A1:I1)
    range_to_clear = "A2:I1000"
    sheet.batch_clear([range_to_clear])

    # row 1 is header row; start at row 2
    start_row = 2

    # create cell range from start row and end row (number of items in minifig_info list)
    # this basically turns the range of cells into a 1-dimensional list
    cell_range = f'A{start_row}:I{start_row + len(minifig_info) - 1}'
    cell_list = sheet.range(cell_range)

    # similar to cell_list, this flattens all of the 2-dimensional minifig data into a 1-dimensional list 
    # that can be parsed through at the same time as cell_list
    flat_data = []
    for char_list in minifig_info:
        for element in char_list:
            flat_data.append(element)

    # populate each cell with the corresponding minifig element
    for i, cell in enumerate(cell_list):
        cell.value = flat_data[i]

    # push cells into sheet
    sheet.update_cells(cell_list)

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

    full_minifigure_list = get_minifigure_info(driver=driver)

    driver.quit()

    for minifigure in full_minifigure_list:
        print(minifigure)

    fill_google_sheet(full_minifigure_list)

main()