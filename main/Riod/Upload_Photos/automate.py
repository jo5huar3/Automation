import csv
from pathlib import Path
import sys
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

RETRY = 1

success_set = []

def Automate(input_set: list[tuple], driver: webdriver.Firefox, url_start: str):
    fail_set = []
    for emplid, photo in input_set:
        try:
            driver.get(url_start)
            driver.switch_to.frame(driver.find_element(By.ID, "ptifrmtgtframe"))
            driver.find_element(By.ID, "PEOPLE_SRCH_EMPLID").send_keys(emplid)
            driver.find_element(By.ID, "#ICSearch").click()
            driver.find_element(By.ID, "DERIVED_CC_ADD_PHOTO_BTN$0").click()
            driver.switch_to.default_content()
            driver.switch_to.frame(driver.find_element(By.ID, "ptModFrame_0"))
            driver.find_element(By.NAME, "#ICOrigFileName").send_keys(str(photo))
            driver.find_element(By.ID, "Upload").click()
            driver.switch_to.default_content()
            driver.switch_to.frame(driver.find_element(By.ID, "ptifrmtgtframe"))
            driver.find_element(By.ID, "#ICSave")
            driver.execute_script(f'document.getElementById("#ICSave").click()')
            driver.find_element(By.ID, "win0div$ICField4")
            confirmation_msg = driver.execute_script(f'return document.getElementById("win0div$ICField4").children[0].innerText')
            if(confirmation_msg == "Save Confirmation"):
                success_set.append(emplid)
            else:
                fail_set.append((emplid, photo)) 
        except:
            fail_set.append((emplid, photo))
    try:
        driver.get(url_start)
    except:
        pass
    return fail_set


def Start(input_set: list[tuple]):
    fail_set = []
    driver = webdriver.Firefox(service=Service(
        service_args=['--marionette-port', '2828', '--connect-existing']))
    driver.implicitly_wait(5)
    url_start = driver.current_url
    i = 1
    fail_set = Automate(input_set, driver, url_start)
    while i < RETRY and len(fail_set) > 0:
        i += 1
        fail_set = Automate(fail_set, driver, url_start)
    return fail_set


if __name__ == "__main__":
    directory = Path('C:\\Users\\jrlewis8\\Python\\Automation\\main\\Riod\\Upload_Photos\\test')
    input_set = [(file.name.split('.')[0], file) for file in directory.iterdir()]
    fail_set = Start(input_set)
    if len(fail_set) == 0:
        print("Automation complete for all input, with 0 errors.")
    else:
        print("Automation complete with errors. The task could not be automated for the following input:")
        for emplid, photo in fail_set:
            print(str(emplid) + ": " + str(photo))