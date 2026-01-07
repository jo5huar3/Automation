import sys
import time
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
            element = driver.find_element(By.ID, "PSOPRDEFN_SRCH_OPRID")
            driver.execute_script(f'arguments[0].value = "{emplid}"', element)
            element = driver.find_element(By.ID, "#ICSearch")
            driver.execute_script(f'arguments[0].click()', element)
            element = driver.find_element(By.ID, "ICTAB_0")
            driver.execute_script(
                f'if(arguments[0].getAttribute("aria-selected") == "false") {{ arguments[0].click(); }}', element
            )
            element = driver.find_element(By.ID, "PSUSRPRFL_WRK_CHANGE_PWD_BTN")
            driver.execute_script(f'arguments[0].click()', element)
            element = driver.find_element(By.ID, "PSUSRPRFL_WRK_OPERPSWD")
            #driver.execute_script(f'arguments[0].value = "{password_new}"', element)
            element.send_keys(password_new)
            element = driver.find_element(By.ID, "PSUSRPRFL_WRK_OPERPSWDCONF")
            #driver.execute_script(f'arguments[0].value = "{password_new}"', element)
            element.send_keys(password_new)
            element = driver.find_element(By.ID, "#ICSave")
            driver.execute_script(f'arguments[0].click()', element)
            driver.switch_to.default_content()
            WebDriverWait(driver, 5).until(
                lambda e: e.execute_script(f'return document.readyState') == 'complete')
            
            try:
                driver.implicitly_wait(0.5)
                alert = driver.find_element(By.ID, "alertmsg")
                #print("Alert msg found.")
                line_buffer.append(emplid)
            except:
                pass
            finally:
                driver.implicitly_wait(5)
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
    start_time = time.time()
    fail_set = Start(unique_list, password_new)
    total_time = time.time() - start_time
    if len(fail_set) == 0:
        print("Automation complete for all input with 0 errors.")
    else:
        print("Automation complete with errors. The task could not be automated for the following input: ")
        for fail in fail_set:
            print(str(fail))
    print(f'Total time taken for {len(unique_list)} resets is {f"{total_time:.2f}"} seconds.')