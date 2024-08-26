import sys
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
'''
Open firefox browser from the terminal with the following command:
    firefox.exe -marionette -start-debugger-server 2828
Navigate to the UHS Security search page then run the script to start automation.

Create a txt file with the emplids to change seperated by a space.
To run use command: 
    'python automate_add_roles.py <path to txt file> <new password>' 
'''
RETRY = 1

def Automate(input_set: list, driver: webdriver.Firefox, url_start: str, password_new: str):
    line_buffer = []
    for emplid in input_set:
        try:
            driver.get(url_start)
            driver.switch_to.frame(driver.find_element(By.ID, "main_target_win0"))
            driver.find_element(By.ID, "PSOPRDEFN_SRCH_OPRID").send_keys(emplid)
            driver.find_element(By.ID, "#ICSearch").click()
            driver.execute_script(
                f'if(document.getElementById("ICTAB_0").getAttribute("aria-selected") == "false") {{ document.getElementById("ICTAB_0").click(); }}'
            )
            driver.find_element(By.ID, "PSUSRPRFL_WRK_CHANGE_PWD_BTN").click()
            driver.find_element(By.ID, "PSUSRPRFL_WRK_OPERPSWD").send_keys(password_new)
            driver.find_element(By.ID, "PSUSRPRFL_WRK_OPERPSWDCONF").send_keys(password_new)
            driver.find_element(By.ID, "#ICSave").click()
            driver.execute_script(
                f'if(document.getElementById("PSUSRPRFL_WRK_OPERPSWD")) {{throw new Error("Password did not save.");}}'
            )
        except:
            line_buffer.append(emplid)
    try:
        driver.get(url_start)
    except:
        pass
    return line_buffer

def Start(input_set: list, password_new: str):
    fail_set = []
    driver = webdriver.Firefox(service=Service(
        service_args=['--marionette-port', '2828', '--connect-existing']))
    driver.implicitly_wait(5)
    url_start = driver.current_url
    i = 1
    fail_set = Automate(input_set, driver, url_start, password_new)
    while i < RETRY and len(fail_set) > 0:
        i += 1
        fail_set = Automate(fail_set, driver, url_start, password_new)
    return fail_set

if __name__ == "__main__":
    input = []
    with open(sys.argv[1], 'r') as file:
        input = file.read().split(" ")
    unique_list = []
    [unique_list.append(val) for val in input if val not in unique_list]
    password_new = sys.argv[2]
    fail_set = Start(unique_list, password_new)
    if len(fail_set) == 0:
        print("Automation complete for all input with 0 errors.")
    else:
        print("Automation complete with errors. The task could not be automated for the following input: ", end="")
        for fail in fail_set:
            print("\n" + str(fail), end=" ")
