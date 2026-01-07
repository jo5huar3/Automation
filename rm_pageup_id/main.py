from pathlib import Path
from datetime import datetime
import time
import argparse
import sys
import pandas as pd
from typing import Any, Optional
from dataclasses import dataclass, field
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from datetime import datetime
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException,
    NoSuchElementException,
    NoSuchFrameException,
)


@dataclass
class RunStats:
    start_time: datetime
    finish_time: Optional[datetime] = None

    # inputs
    input_sz: int = 0

    # failures (you store whatever key you iterated + any details)
    fail_set: dict[Any, Any] = field(default_factory=dict)
    fail_set_sz: int = 0

    @property
    def elapsed_seconds(self) -> Optional[float]:
        if self.finish_time is None:
            return None
        return (self.finish_time - self.start_time).total_seconds()


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

def click_search_and_wait(
    driver,
    by, locator,                         # the Search button
    results_by=None, results_locator=None, # something that appears when results load
    msg_by=None, msg_locator=None,         # message area (no rows / validation / etc.)
    timeout=15,
    poll=0.2,
):
    """
    Clicks Search and waits for *either*:
      - URL changes (navigation)
      - the clicked button becomes stale (DOM refresh / partial postback)
      - results marker appears
      - message marker appears

    Returns: one of
      'navigated', 'results', 'message', 'updated', 'no_change'
    """
    before_url = driver.current_url

    # Get the clickable element ourselves so we can wait on staleness later
    btn_el = wait(driver, EC.element_to_be_clickable((by, locator)), timeout=timeout, poll=poll)

    # Click using your helper (keeps your small post-click sleep)
    wait_click(driver, by, locator, timeout=timeout, poll=poll)

    conditions = [
        EC.url_changes(before_url),
        EC.staleness_of(btn_el),
    ]
    if results_by and results_locator:
        conditions.append(EC.presence_of_element_located((results_by, results_locator)))
    if msg_by and msg_locator:
        conditions.append(EC.presence_of_element_located((msg_by, msg_locator)))

    try:
        wait(driver, EC.any_of(*conditions), timeout=timeout, poll=poll)
    except TimeoutException:
        return "no_change"

    # Classify outcome
    if driver.current_url != before_url:
        return "navigated"
    if msg_by and msg_locator:
        try:
            driver.find_element(msg_by, msg_locator)
            return "message"
        except Exception:
            pass
    if results_by and results_locator:
        try:
            driver.find_element(results_by, results_locator)
            return "results"
        except Exception:
            pass

    # staleness triggered but no explicit marker provided/found
    return "updated"

def find_row_with_selected_option_value(
    driver,
    grid_table_id: str,           # e.g. "SCC_PERS_NID_H$scrolli$0"
    option_value: str,            # e.g. "PGUP"
    additional_wait_id: str | None = None,
    timeout=10,
    poll=0.2,
):
    # 1) Table exists
    wait(driver, EC.presence_of_element_located((By.ID, grid_table_id)), timeout=timeout, poll=poll)

    # 2) Grid “loaded” marker exists (header pager control is a good PeopleSoft signal)
    #    This is derived from your HTML: SCC_PERS_NID_H$hpage$0
    #    If your grid name changes, adjust this id.
    if additional_wait_id:
        wait(driver, EC.presence_of_element_located((By.ID, additional_wait_id)), timeout=timeout, poll=poll)

    # 3) Now it’s safe to conclude non-existence using find_elements (no exception)
    row_xpath = (
        f"//table[@id='{grid_table_id}']"
        "//tr[.//select[.//option[@value='%s' and (@selected or @selected='selected')]]]"
        % option_value
    )
    rows = driver.find_elements(By.XPATH, row_xpath)
    return rows[0] if rows else None

def results_contains_description(
    driver,
    results_table_id: str,          # e.g. "gbPTS_CFG_CL_STD_RSL$0"
    description_text: str,          # e.g. "PGUP"
    timeout=10,
    poll=0.2,
) -> bool:
    # 1) results grid exists => DOM loaded for results
    wait(driver, EC.presence_of_element_located((By.ID, results_table_id)), timeout=timeout, poll=poll)

    # 2) non-throwing search inside the grid for a Description cell matching text
    xpath = (
        f"//table[@id='{results_table_id}']"
        f"//span[starts-with(@id,'PTS_CFG_CL_RSLT_NUI_SRCH8$19$$') and normalize-space()='{description_text}']"
    )
    return len(driver.find_elements(By.XPATH, xpath)) > 0

def wait(driver, condition, timeout=10, poll=0.2):
    return WebDriverWait(
        driver,
        timeout,
        poll_frequency=poll,
        ignored_exceptions=(NoSuchElementException, StaleElementReferenceException),
    ).until(condition)

def wait_click(driver, by, locator, timeout=10, poll=0.2, retries=3, js_fallback=True):
    last_err = None
    for _ in range(retries):
        try:
            el = wait(driver, EC.element_to_be_clickable((by, locator)), timeout, poll)
            try:
                el.click()
            except (StaleElementReferenceException, ElementClickInterceptedException):
                # Try JS click if normal click fails
                if js_fallback:
                    el = driver.find_element(by, locator)  # refetch
                    driver.execute_script("arguments[0].click();", el)
                else:
                    raise
            time.sleep(0.2)
            return el
        except (StaleElementReferenceException, ElementClickInterceptedException, TimeoutException) as e:
            last_err = e
            # tiny pause to let PS finish repainting
            time.sleep(poll)

    raise last_err

def wait_send_keys(driver, by, locator, text, timeout=10, poll=0.2, tab_out=True):
    el = wait(driver, EC.visibility_of_element_located((by, locator)), timeout, poll)
    el.clear()
    el.send_keys(text)
    if tab_out:
        el.send_keys(Keys.TAB)
    time.sleep(0.2)
    return el   

def switch_to_iframe(
    driver,
    frame_locator,              # e.g. (By.ID, "ptifrmtgtframe")
    timeout: float = 10,
    poll: float = 0.2,
    reset_to_default: bool = True,
):
    """
    Waits for an iframe to exist and switches into it.
    Returns the WebElement for the iframe (useful for debugging/logging).
    """
    if reset_to_default:
        driver.switch_to.default_content()

    wait = WebDriverWait(
        driver,
        timeout,
        poll_frequency=poll,
        ignored_exceptions=(NoSuchFrameException,),
    )
    
    # This condition switches to the frame for you, but doesn't return the element.
    wait.until(EC.frame_to_be_available_and_switch_to_it(frame_locator))

def js_on(
    driver,
    script: str,
    element_locator=None,     # e.g. (By.ID, "username") or None
    *args,
    timeout: float = 10,
    poll: float = 0.2,
    retries: int = 2,
):
    """
    Execute JS. If element_locator is provided, waits for the element and passes it
    as arguments[0]. Retries on stale element.
    """
    def _get_el():
        if element_locator is None:
            return None
        return WebDriverWait(driver, timeout, poll_frequency=poll).until(
            lambda d: d.find_element(*element_locator)
        )

    last_err = None
    for _ in range(max(1, retries + 1)):
        try:
            el = _get_el()
            if el is None:
                return driver.execute_script(script, *args)
            return driver.execute_script(script, el, *args)
        except StaleElementReferenceException as e:
            last_err = e

    raise last_err

    
def task(driver, start_url: str, **kwargs):  
    try:
        pass
    except:
        pass
    return 0

def Automate(input_set: list[str], driver: webdriver.Chrome, start_url: str):
    fail_set = {}
    for key in input_set:
        try:
            switch_to_iframe(driver, (By.ID, "ptifrmtgtframe"))
            wait_send_keys(driver, By.ID, "PEOPLE_SRCH_EMPLID", key)
            wait_click(driver, By.ID, "PTS_CFG_CL_WRK_PTS_ACCESS_MODE_C")
            result = click_search_and_wait(driver, By.ID, "PTS_CFG_CL_WRK_PTS_SRCH_BTN", By.ID, "l0PTS_CFG_CL_STD_RSL$0")
            needs_removal = False
            if result == "results" and results_contains_description(driver, "gbPTS_CFG_CL_STD_RSL$0", "PGUP"):
                needs_removal = True
                wait_click(driver, By.XPATH, "//div[span[normalize-space()='PGUP']]")
            #print(f"DEBUG: {result}")
            if needs_removal:
                row_xpath = (
                    "//tr[.//select"
                    "[.//option[@value='PGUP' and (@selected or @selected='selected')]]]"
                )
                switch_to_iframe(driver, (By.ID, "ptifrmtgtframe"))
                result = find_row_with_selected_option_value(
                    driver,
                    "SCC_PERS_NID_H$scrolli$0",
                    "PGUP",
                    "SCC_PERS_NID_H$hpage$0",
                )
                if result:
                    wait_click(driver, By.XPATH, row_xpath + "//a[starts-with(@id,'SCC_PERS_NID_H$delete$0$$') and contains(@id,'$$')]")
                    driver.switch_to.default_content()
                    wait_click(driver, By.ID, "#ALERTOK")
                    switch_to_iframe(driver, (By.ID, "ptifrmtgtframe"))
                    wait_click(driver, By.ID, "#ICSave")
            else:
                fail_set[key] = f"PGUP ID does not exist for this user."
        except Exception as e:
            fail_set[key] = f"Exception: {e}"
        finally:
            try:
                driver.get(start_url)
            except:
                # Cannot recover from this
                pass
    return fail_set

def Start(input_set: pd.DataFrame, mode):
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
    driver.implicitly_wait(0)
    url_start = driver.current_url
    
    i = 1
    fail_set = Automate(input_set, driver, url_start)
    while i < RETRY and len(fail_set) > 0:
        i += 1
        fail_set = Automate(list(fail_set.keys()), driver, url_start)
    return fail_set

def auto_init_(data: str, mode: str) -> RunStats:
    path = Path(data)
    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path,  dtype=str)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=0, engine="openpyxl", dtype=str)
    else:
        raise ValueError(f"Unsupported file type: {ext} (expected .csv or .xlsx/.xls)")
    input_set = (
        df["EMPLID"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
    run_stats = RunStats(
        start_time=datetime.now(),
        fail_set={},
        input_sz=len(input_set)
    )
    run_stats.fail_set = Start(input_set, mode)
    run_stats.finish_time = datetime.now()
    run_stats.fail_set_sz = len(run_stats.fail_set)
    return run_stats

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Example CLI with required --data and optional --mode.")
    parser.add_argument(
        "--data",
        required=True,
        help="Mandatory data input (e.g., a file path or a literal string).",
    )
    parser.add_argument(
        "--mode",
        choices=["standard", "debug"],
        default="standard",
        help="Optional mode (default: standard).",
    )
    return parser.parse_args(argv)

def main(argv: list[str]) -> int:
    args = parse_args(argv)

    print("Parsed arguments:", args)
    
    run_stats = auto_init_(args.data, args.mode)
    
    with open(f"{args.data.split('.')[0]}_results.txt", "w") as f:
        f.write(f"""Automation started at {run_stats.start_time.strftime("%H:%M:%S")}.\n""")
        str_ = f"""Automation finished at {run_stats.finish_time.strftime("%H:%M:%S")}."""
        if run_stats.fail_set_sz == 0:
            f.write(f"Automation complete for {run_stats.input_sz} input with 0 errors.\n{str_}\n")
        else:
            f.write(f"Automation complete for {run_stats.input_sz} input with {run_stats.fail_set_sz} errors.\n{str_}\nThe task could not be automated for the following input:\n")
            for k, v in sorted(run_stats.fail_set.items()):
                f.write(f"{k}: {v}\n")
        print(f"Results stored @ {f.name}")
    return 0

# pip install pandas selenium openpyxl
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))