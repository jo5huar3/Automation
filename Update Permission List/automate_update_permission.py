import csv
import sys
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
'''
Open firefox browser from the terminal with the following command:
    firefox.exe -marionette -start-debugger-server 2828
Navigate to the UHS Security search page then run the script to start automation.

Create a csv file with emplids as the first column to and the new permission list 
as the second column. The first row should contain column titles.

To run use command: 
    'python automate_update_permission.py <path to csv file>' 
'''

RETRY = 3

def Automate(input_set: dict[list], driver: webdriver.Firefox, url_start: str):
    fail_set = {}
    driver.implicitly_wait(5)
    for emplid in input_set.keys():
        for val in input_set[emplid]:
            try:
                driver.get(url_start)
                driver.switch_to.frame(driver.find_element(By.ID, "main_target_win0"))
                driver.find_element(By.ID, "PSOPRDEFN_SRCH_OPRID").send_keys(emplid)
                driver.find_element(By.ID, "#ICSearch").click()
                driver.execute_script(
                    f'if(document.getElementById("ICTAB_0").getAttribute("aria-selected") == "false") {{ document.getElementById("ICTAB_0").click(); }}'
                )
                driver.find_element(By.ID, "PSOPRDEFN_OPRCLASS").clear()
                driver.find_element(By.ID, "PSOPRDEFN_OPRCLASS").send_keys(val)
                driver.find_element(By.ID, "#ICSave").click()
                driver.execute_script(
                    f'if(document.getElementById("PSOPRDEFN_OPRCLASS").value != "{val}") {{ throw new Error("text field did not change");}}'
                )
            except:
                if emplid in fail_set.keys():
                    fail_set[emplid].append(val)
                else:
                    fail_set[emplid] = [val]
    try:
        driver.get(url_start)
    except:
        pass
    return fail_set


def Start(input_set: dict[list]):
    fail_set = {}
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
    input = {}
    with open(sys.argv[1], 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)
        for row in csv_reader:
            key = row[0]
            input[key] = []
            for val in row[1:]:
                if len(val) > 0:
                    input[key].append(val)
    fail_set = Start(input)
    if len(fail_set) == 0:
        print("Automation complete for all input with 0 errors.")
    else:
        print("Automation complete with errors. The task could not be automated for the following input:",end="")
        for emplid in fail_set.keys():
            print("\n" + str(emplid) + ": ", end="")
            for val in fail_set[emplid]:
                print(str(val), end="")