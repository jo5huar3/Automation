import sys
import csv
import threading
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

# Start firefox: firefox.exe -marionette -start-debugger-server 2828
def Search_for_Course(classes : dict[list], driver : webdriver, lock : threading.Lock, window_handle, initial_url, line_buffer : list, main_window_handle):
    line_buffer_t = []
    for subject in classes.keys():
        for course_number in classes[subject]:
            current_search =  str(subject + " " + course_number)
            lock.acquire()
            try:
                driver.switch_to.window(window_handle)
                try:
                    # Send 'SUBJ XXXX' to search text field.
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.ID, 'PTS_KEYWORDS3'))
                    )
                    text_field = driver.find_element(By.ID, 'PTS_KEYWORDS3')
                    #text_field.clear()
                    text_field.send_keys(current_search + Keys.ENTER)
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, 'win22divPTS_SEARCHED_KW2'))
                        )
                        element = driver.find_element(By.ID, 'win22divPTS_SEARCHED_KW2')
                        if element.text == "No Courses available for the selected filters":
                            line_buffer_t.append(current_search + ": " + element.text + ".\n")
                    except TimeoutException:
                        # PTS_SRCH_PTS_INDEXTIME : ID of element that appears on No results were returned page.
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, 'PTS_SRCH_PTS_INDEXTIME'))
                        )
                        no_results_element = driver.find_element(By.ID, 'PTS_SRCH_PTS_INDEXTIME')
                        line_buffer_t.append(current_search + ": " + 
                                        no_results_element.text.split(".")[0] + ".\n")       
                except:
                    line_buffer_t.append(current_search + ": Error unsuccessful search.\n")
                # Return to the fluid search home screen to for next iteration.
                try:
                    driver.get(initial_url)
                except:
                    trash = input("Error: driver.get(initial_url) Check connection press enter to continue.")
                    driver.close()
                    driver.switch_to.window(main_window_handle)
                    driver.switch_to.new_window("tab")
                    driver.get(initial_url)
                    window_handle = driver.current_window_handle   
            finally:
                lock.release()
            time.sleep(2)
    lock.acquire()
    line_buffer.extend(line_buffer_t)
    driver.switch_to.window(window_handle)
    driver.close()
    lock.release()

def Split_Dictionary(classes : dict[list], classes_s1 : dict[list], classes_s2 : dict[list]):
    total_1 = 0 
    total_2 = 0
    for subject in classes.keys():
        if total_2 < total_1:
            classes_s2[subject] = classes[subject]
            total_2 += len(classes[subject])
        else:
            classes_s1[subject] = classes[subject]
            total_1 += len(classes[subject])

def Multithread_Search(classes : dict[list]) -> list[str]:
    line_buffer = []
    driver = webdriver.Firefox(service=Service(
        service_args=['--marionette-port', '2828', '--connect-existing']
    ))
    main_window_handle = driver.current_window_handle
    initial_url = driver.current_url
    lock = threading.Lock()
    threads = []
    classes_s1 = {}
    classes_s2 = {}
    Split_Dictionary(classes, classes_s1, classes_s2)
    for i in range(2):
        lock.acquire()
        driver.switch_to.new_window('tab')
        driver.get(initial_url)
        new_window_handle = driver.current_window_handle
        if i == 0:
            t = threading.Thread(target=Search_for_Course, 
                                args=(classes_s1, driver, lock, new_window_handle, initial_url, line_buffer, main_window_handle))
        else:
            t = threading.Thread(target=Search_for_Course, 
                                args=(classes_s2, driver, lock, new_window_handle, initial_url, line_buffer, main_window_handle))
        t.start()
        threads.append(t)
        driver.switch_to.window(main_window_handle)
        lock.release()
    for t in threads:
        t.join()
    return line_buffer

if __name__ == "__main__":
    classes = {}
    with open(sys.argv[1], 'r') as csv_file:
        # index[3] : subject
                # index[4] : course number
                csv_reader = csv.reader(csv_file)
                next(csv_reader)
                for row in csv_reader:
                    if row[3] in classes.keys():
                       if not row[4] in classes[row[3]]:
                           classes[row[3]].append(row[4])
                    else:
                       classes[row[3]] = [row[4]]          
    output_filename = sys.argv[1].split(".")[0] + "_FluidSearchResult.txt"
    with open(output_filename, 'w') as file:
       file.writelines(Multithread_Search(classes))
    print("Results at " + output_filename)
    print(classes)