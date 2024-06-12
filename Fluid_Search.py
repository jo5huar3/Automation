import sys
import csv
import time
from multiprocessing import Process, Queue, Lock
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

NUM_PROCESS = 2
MAX_RETRY = 5

def Search_for_Courses(classes : dict[list], queue : Queue, failed_search_queue : Queue, cookies, initial_url, lock): 
    line_buffer_t = []
    with lock:
        driver = webdriver.Firefox()
        driver.implicitly_wait(5)
        driver.get(initial_url)
        driver.delete_all_cookies()
        [driver.add_cookie(cookie) for cookie in cookies]
        driver.get(initial_url)
    time.sleep(1)
    for subject in classes.keys():
        for course_number in classes[subject]:
            current_search =  str(subject + " " + course_number)
            lock.acquire()
            try:
                try:
                    search_field = driver.find_element(By.ID, 'PTS_KEYWORDS3')
                    search_field.send_keys(current_search + Keys.ENTER)
                    try:
                        result_element = driver.find_element(By.ID, 'win14divPTS_SEARCHED_KW2')
                        if result_element.text == "No Courses available for the selected filters":
                                line_buffer_t.append(current_search + ": " + result_element.text + ".\n")
                    except NoSuchElementException:
                        no_result_element = driver.find_element(By.ID, 'PTS_SRCH_PTS_INDEXTIME')
                        line_buffer_t.append(current_search + ": " + 
                                        no_result_element.text.split(".")[0] + ".\n")    
                except:
                    failed_search_queue.put((subject, course_number))
                try:
                    driver.get(initial_url)
                except:
                    input("Error: driver.get(initial_url) Check connection and press enter to continue.")
                    driver.get(initial_url)
            finally:
                lock.release()
            time.sleep(2)
    with lock:
        [queue.put(line) for line in line_buffer_t]
        driver.quit()

def Offload_Failed_Queue(failed_search_queue : Queue, failed_searches : dict):
    while not failed_search_queue.empty():
        course = failed_search_queue.get()
        subject = course[0]
        course_number = course[1]
        if subject in failed_searches.keys():
            failed_searches[subject].append(course_number)
        else:
            failed_searches[subject] = [course_number]

def Split_Dictionary(classes : dict[list], classes_p : list[dict]):
    [classes_p.append({}) for i in range(NUM_PROCESS)]  
    i = 0
    for subject in classes.keys():
        classes_p[i % NUM_PROCESS][subject] = classes[subject]
        i += 1

def StartProcesses(classes : dict[list]):
    line_buffer = []
    driver = webdriver.Firefox(service=Service(
        service_args=['--marionette-port', '2828', '--connect-existing']))
    cookies = driver.get_cookies()
    initial_url = driver.current_url
    classes_p = []
    Split_Dictionary(classes, classes_p)
    lock = Lock()
    process_list = []
    queue = Queue()
    failed_search_queue = Queue()
    for i in range(NUM_PROCESS):
        process = Process(target=Search_for_Courses, args=(classes_p[i], queue, failed_search_queue, cookies, initial_url, lock))
        process.start()
        process_list.append(process)
    for process in process_list:
        process.join()
    i = 0
    failed_searches = {}
    while not failed_search_queue.empty() and i < MAX_RETRY:
        i += 1
        failed_searches = {}
        Offload_Failed_Queue(failed_search_queue, failed_searches)
        process = Process(target=Search_for_Courses, args=(failed_searches, queue, failed_search_queue, cookies, initial_url, lock))
        process.start()
        process.join()
    while not queue.empty():
        line_buffer.append(queue.get())
    while not failed_search_queue.empty() and i == MAX_RETRY:
        course = failed_search_queue.get()
        line_buffer.append(str(course[0] + " " + course[1] + ": Error unsuccessful search.\n"))
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
       file.writelines(StartProcesses(classes))
    print("Results at " + output_filename)