import csv
import sys
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

RETRY = 3

def Automate(input_set: dict[list], driver: webdriver.Firefox, url_start: str):
    fail_set = {}
    for emplid in input_set.keys():
        try:
            driver.get(url_start)
            driver.switch_to.frame(driver.find_element(By.ID, "main_target_win0"))
            driver.find_element(By.ID, "PSOPRDEFN_SRCH_OPRID").send_keys(emplid)
            driver.find_element(By.ID, "#ICSearch").click()
            driver.find_element(By.ID, "ICTAB_2").click()
            view_all_triggered = False
            for val in input_set[emplid]:
                try: 
                    result = str(driver.execute_script('return document.getElementById("PSROLEUSER_VW$hpage$0").options[0].text')).split(' ')
                    user_roles_total = int(result[len(result) - 1])
                    if user_roles_total > 10 and not view_all_triggered:
                        view_all_triggered = True
                        driver.find_element(By.ID, "PSROLEUSER_VW$hviewall$0").click()
                    i = 0
                    while i < user_roles_total:
                        if driver.execute_script(f'return document.getElementById("PSROLEUSER_VW_DYNAMIC_SW${i}").checked'):
                            user_role_cur = str(driver.find_element(By.ID, f'win0divPSROLEUSER_VW_ROLENAME${i}').text)
                        else:
                            user_role_cur = str(driver.execute_script(f'return document.getElementById("PSROLEUSER_VW_ROLENAME${i}").value'))
                        if val == user_role_cur:
                            break
                        i += 1
                    if i == user_roles_total:
                        driver.find_element(By.ID, f"PSROLEUSER_VW$new${i - 1}$$0").click()
                        driver.find_element(By.ID, f"PSROLEUSER_VW_ROLENAME${i}").send_keys(val)
                        driver.find_element(By.ID, f"#ICSave").click()
                except:
                    if emplid in fail_set.keys():
                        fail_set[emplid].append(val)
                    else:
                        fail_set[emplid] = [val]
        except:
            fail_set[emplid] = [val for val in input_set[emplid]]
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
        print("Automation complete for all input, with 0 errors.")
    else:
        print("Automation complete with errors. The task could not be automated for the following input:")
        for emplid in fail_set.keys():
            print("\n" + str(emplid) + ": ", end="")
            for val in fail_set[emplid]:
                print(str(val), end=" ")