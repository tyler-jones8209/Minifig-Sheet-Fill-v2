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
collection_url = "https://www.bricklink.com/v3/myCollection/main.page"

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

    # return True is url contains myCollection and does NOT contain identity.lego.com
    return "myCollection" in driver.current_url and "identity.lego.com" not in driver.current_url

# function for making the driver
def make_driver():

    # configure driver to use user data directory with login shit idrk
    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--headless")
    return webdriver.Chrome(options=options)


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

    time.sleep(0.5)
    my_minifigures_btn = driver.find_element(By.ID, "MPI-nav-myMinifigures")
    driver.execute_script("arguments[0].click();", my_minifigures_btn)

    time.sleep(1)
    minifigure_item_list = driver.find_elements(By.XPATH, "//*[starts-with(@id, 'listItemView-')]")

    for figure in minifigure_item_list:
        figure_number = figure.find_element(By.XPATH, "//*[@class='text--small text--center l-margin-top--sm text--break-word l-cursor-pointer']")
        print(figure_number.text)

    time.sleep(10)
    driver.quit()

main()