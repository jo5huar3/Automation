import csv
import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from datetime import datetime
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RETRY = 1 

Js = {
    "-click" : "arguments[0].click()",
    "-input" : "arguments[0].value = ",
    "get-txt" : "return arguments[0].value",
    "select-opt-val" : """(function(arguments) { arguments[0].value = arguments[1]; let event = new Event('change', { bubbles: true }); arguments[0].dispatchEvent(event);  })();      """,
    "get-selectedOptTxtCnt" : "return arguments[0].options[arguments[0].selectedIndex].textContent",
    "get-txtCnt": "return arguments[0].textContent",
    "set-selectInd" : "arguments[0].selectedIndex = ",
    "srch-set-OPT" : "for (let i = 0; i < arguments[0].length; i++) {if (arguments[0][i].text == arguments[1]) { arguments[0].selectedIndex = i; break; }}",
    "table.next" : "const a = document.getElementsByClassName(arguments[0]); const b = a[0]; \
        if(b.children[0].tagName == 'A') { b.click() } else { return 1 }",
    "get_table_size" : 'let span = document.querySelectorAll("td span.PSGRIDCOUNTER"); return span[0].textContent;',
    "get_cell_with_NAME" : """\
        let arr = document.querySelectorAll('span[id^="TRNS_CRSE_DTL_REPEAT_CODE$"]'); 
        let a = [];
        for (const ar of arr) { a.push([ar.id, ar.textContent]); } return a;
    """,
    "get_cell_with_ID" : """\
        let arr = document.querySelectorAll('input[name^="TRNS_CRSE_DTL_REPEAT_CODE$"]'); let a = [];\
        for (const ar of arr) { a.push([ar.name, ar.value]); } return a;\
    """,
    "search_table_ret" : """\
    let spans = document.querySelectorAll("span[id^='TRNS_CRSE_DTL_CRSE_ID$"); \
        for (let s of spans) { \
            if (s.textContent.trim() == arguments[0]) {
                let row = s.closest('tr');\
                let cell = row.querySelector("span[id^='TRNS_CRSE_DTL_REPEAT_CODE$']"); 
                if (cell.textConent == "ILGL") {cell.textConent = "";}
                } 
        } return null;\
    """,
    'get_disabled_attribute' : 'const el =  document.getElementById(arguments[0]); return el.getAttribute("disabled");'
}


    
def sendkeys_ENSURE(driver: webdriver.Chrome, id: str, val: str, sec: float = 0.25) -> int:
    try:
        element = driver.find_element(By.ID, id)
        element.clear()
        element.send_keys(val)
        element.send_keys(Keys.TAB)
        time.sleep(sec)
        return 0
    except Exception as e:
        return e

def click_ENSURE(driver: webdriver.Chrome, id: str, sec: float = 0.25) -> int:
    try:
        element = driver.find_element(By.ID, id)
        element.click()
        time.sleep(sec)
        return 0
    except Exception as e:
        return e

def tabout_FOCUS(driver: webdriver.Chrome, id: str, sec: float = 0.25) -> int:
    try:
        element = driver.find_element(By.ID, id)
        element.send_keys(Keys.TAB)
        time.sleep(sec)
        return 0
    except Exception as e:
        return e

def exec_SCRIPT(driver: webdriver.Chrome, script: str, val : str = None, sec: float = 0.25) -> int:
    try:
        response = driver.execute_script(Js[script], val)
        time.sleep(sec)
        return response or 0
    except Exception as e:
        return e
    
def exec_ENSURE(driver: webdriver.Chrome, id: str, script: str, val : str = None, sec: float = 0.25) -> int:
    try:
        element = driver.find_element(By.ID, id)
        response = driver.execute_script(Js[script], element, val)
        time.sleep(sec)
        return response or 0
    except Exception as e:
        return e

def select_option(driver: webdriver.Chrome, id: str, option: str, sec: float = 0.15) -> int:
    try:
        container = driver.find_element(By.ID, id)
        options = container.find_elements(By.TAG_NAME, 'option')
        time.sleep(sec)
        for i, opt in enumerate(options):
            if opt.text == option:
                exec_ENSURE(driver, f"{id}", f"arguments[0].selectedIndex = {i};", 0.25)
                break
        return 0
    except Exception as e:
        return e

def select_option_selenium(driver: webdriver.Chrome, id: str, val: str, sec: float = 0.15) -> int:
    try:
        element = driver.find_element(By.ID, id)
        select = Select(element)
        select.select_by_value(val)
        time.sleep(sec)
        return 0
    except Exception as e:
        return e

def refresh_iframe(driver: webdriver.Chrome, id: str, sec: float = 0.15, bckout = True) -> int:
    try:
        if bckout:
            driver.switch_to.default_content()
        IFRAME = driver.find_element(By.ID, id)
        driver.switch_to.frame(IFRAME)
        time.sleep(sec)
        return 0
    except Exception as e :
        return e
 
    
def handlePopup(driver : webdriver.Chrome):
    try:
        driver.implicitly_wait(1)
        driver.switch_to.default_content()
        main = driver.current_window_handle
        for h in driver.window_handles:
            if h != main:
                driver.switch_to.window(h)
                break
        try:
            click_ENSURE(driver, '#ICYes')
        except:
            click_ENSURE(driver, "#ICOK")
        driver.switch_to.window(main)
        driver.implicitly_wait(5)
        refresh_iframe(driver, "ptifrmtgtframe")
        WebDriverWait(driver, 10, 0.5).until(
            lambda dvr: dvr.execute_script(
                Js['get_disabled_attribute'], 'DERIVED_TRCR_UNPOST_PB$0') != 'disabled' 
        ) 
    except:
        driver.implicitly_wait(5)
        refresh_iframe(driver, "ptifrmtgtframe")
        return 1
    driver.implicitly_wait(5)
    return 0

    
def task(driver, emplid, acad_career, institution):    
    try:
        refresh_iframe(driver, "ptifrmtgtframe")
        sendkeys_ENSURE(driver, "TRNSFR_CRS_SRCH_EMPLID", emplid)
        select_option_selenium(driver, 'TRNSFR_CRS_SRCH_ACAD_CAREER', acad_career)
        sendkeys_ENSURE(driver, "TRNSFR_CRS_SRCH_INSTITUTION", institution)
        click_ENSURE(driver, "PTS_CFG_CL_WRK_PTS_SRCH_BTN")

        refresh_iframe(driver, "ptifrmtgtframe")

        el = driver.find_elements(By.CSS_SELECTOR, 'td span.PSGRIDCOUNTER')
        container1 = el[0].text
        container2 = el[1].text

        container1 = int(container1.split('of ')[1])
        container2 = int(container2.split('of ')[1])

        #print(container1)
        #print(container2)
        for i in range(container1):
            click_ENSURE(driver, "ICTAB_2")
            disabled =  driver.execute_script(Js['get_disabled_attribute'], 'DERIVED_TRCR_UNPOST_PB$0')
            status = 'UNPOST' if disabled == 'disabled' else 'POST'
            #print(status)
            click_ENSURE(driver, "ICTAB_0")
            update_pending = False
            for j in range(container2):
                el = None
                if status == 'UNPOST':
                    elements = driver.find_elements(By.CSS_SELECTOR, f"""input[name^="TRNS_CRSE_DTL_REPEAT_CODE$"]""")
                    el = [ (el_.get_attribute('value'), el_.get_attribute('id')) for el_ in elements]
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, f"""span[id^="TRNS_CRSE_DTL_REPEAT_CODE$"]""")
                    el = [ (el_.text, el_.get_attribute('id')) for el_ in elements]
                #print(el)
                change_list = []
                for cell in el:
                    if cell[0] == 'ILGL':
                        change_list.append(cell[1])
                #print(change_list)
                if change_list:
                    update_pending = True
                    if status == "POST":
                        click_ENSURE(driver, "ICTAB_2")
                        click_ENSURE(driver, "DERIVED_TRCR_UNPOST_PB$0", 1.5)
                        WebDriverWait(driver, 10, 0.5).until(
                            lambda dvr: dvr.execute_script(
                                Js['get_disabled_attribute'], 'DERIVED_TRCR_POST_PB$0') != 'disabled'
                        )
                        time.sleep(0.25)
                        status = "UNPOST"
                        click_ENSURE(driver, "ICTAB_0")
                    for id in change_list:
                        sendkeys_ENSURE(driver, id, "")
                if j == container2 - 1:
                    break  
            if update_pending:
                click_ENSURE(driver, '#ICSave')
                click_ENSURE(driver, "ICTAB_2")
                click_ENSURE(driver, "DERIVED_TRCR_POST_PB$0", 1.5)
                WebDriverWait(driver, 10, 0.5).until(
                    lambda dvr: dvr.execute_script(
                        Js['get_disabled_attribute'], 'DERIVED_TRCR_UNPOST_PB$0') != 'disabled' or
                        not handlePopup(driver)
                )    
                time.sleep(0.25)
                click_ENSURE(driver, "ICTAB_0")
                
            if i == container1 - 1:
                    break  
            click_ENSURE(driver, '$ICField4$hdown$0')
    except:
        return (emplid, acad_career, institution)
    return 0

def Automate(input_set: dict[list], driver: webdriver.Chrome, url_start: str):
    fail_set = {}
    for key in input_set.keys():
    # key structure: (emplid, acad_career, inst) 
        result = task(driver, key[0], key[1], key[2])
        if result:
            fail_set[key] = []
        driver.get(url_start)
    return fail_set


def Start(input_set: dict[list], mode ):
    if not mode:
        mode = 'standard'
    fail_set = {}
    driver = None
    options = Options()
    if mode == 'standard':
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_argument("--log-level=3")
    elif mode == 'debug':
        options.debugger_address = "localhost:9222"
    driver = webdriver.Chrome(options=options)
    if mode == 'standard':
        input("Navigate to the page where the automation will start and press enter.")
    driver.implicitly_wait(5)
    url_start = driver.current_url
    
    i = 1
    fail_set = Automate(input_set, driver, url_start)
    while i < RETRY and len(fail_set) > 0:
        i += 1
        fail_set = Automate(fail_set, driver, url_start)
    return fail_set


# command line arguments: main debug <>.csv
if __name__ == "__main__":
    input_set = {}
    var_count = len(sys.argv)
    file_name = sys.argv[var_count - 1]
    run_parameter = None
    if var_count > 2:
        run_parameter = sys.argv[1]
    with open(sys.argv[var_count - 1], 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)
        for row in csv_reader:
            emplid = row[0]
            acad_career = row[7]
            inst = row[8]
            courseID = row[11]
            if (emplid, acad_career, inst) not in input_set.keys():
                input_set[(emplid, acad_career, inst)] = []
            if courseID not in input_set[(emplid, acad_career, inst)]:
                input_set[(emplid, acad_career, inst)].append(courseID)
    start_time = datetime.now()
    fail_set = Start(input_set, run_parameter)
    finish_time = datetime.now()
    input_sz = len(input_set)
    fail_set_sz = len(fail_set)
    with open(f"{file_name.split('.')[0]}_results.txt", "w") as f:
        f.write(f"""Automation started at {start_time.strftime("%H:%M:%S")}.\n""")
        str_ = f"""Automation finished at {finish_time.strftime("%H:%M:%S")}."""
        if len(fail_set) == 0:
            f.write(f"Automation complete for {input_sz} input with 0 errors.\n{str_}\n")
        else:
            f.write(f"Automation complete for {input_sz} input with {fail_set_sz} errors.\n{str_}\nThe task could not be automated for the following input:\n")
            for emplid in fail_set.keys():
                f.write(f"{emplid[0]} {emplid[1]} {emplid[2]}  : ")
                for i, val in enumerate(fail_set[emplid]):
                    f.write(f"{', ' if i else ''}{val}")

