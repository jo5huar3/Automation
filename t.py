 
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# ACE_PSUSRPRFL_WRK_LABEL_TEXT_LBL


driver = webdriver.Firefox(service=Service(
        service_args=['--marionette-port', '2828', '--connect-existing']))
#element = driver.find_element(By.ID, "ACE_PSUSRPRFL_WRK_LABEL_TEXT_LBL")

driver.implicitly_wait(5)
driver.switch_to.frame(driver.find_element(By.ID, "main_target_win0"))
element = driver.find_element(By.ID, "#ICSave")
if not driver.execute_script(f'return arguments[0].click()', element):
        print("Alert message:")
