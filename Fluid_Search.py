import sys
import csv
import time
import threading
from multiprocessing import Process, Queue, Value, Lock
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

NUM_PROCESS = 2
MAX_RETRY = 5
MINUTE = 60

class Course:
    """
    Class to keep the count of the number of times the SUBJ #### combination appears.
    """
    def __init__(self, subject : str, course_number : str, count = 1) -> None:
        self.subject = subject
        self.course_number = course_number
        self.count = count

    def Incriment_Count(self):
        self.count = self.count + 1

    def Get_Subject(self):
        return self.subject

    def Get_Count(self):
        return self.count
    
    def Get_Course_Number(self):
        return self.course_number


def Search_for_Courses(classes : dict[list[Course]], queue : Queue, failed_search_queue : Queue, cookies, initial_url, lock):
    """
    Conducts fluid search with SUBJ ####
    Reports if the search returns 0 results or if there is a discrepancy in the number of class options available.
    When an error occurs in a search the course being search gets added to a queue where it will get retried by the main process.
    """ 
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
        for course in classes[subject]:
            current_search =  str(subject) + " " + str(Course.Get_Course_Number(course))
            lock.acquire()
            try:
                try:
                    search_field = driver.find_element(By.ID, 'PTS_KEYWORDS3')
                    search_field.send_keys(current_search + Keys.ENTER)
                    try:
                        result_element = driver.find_element(By.ID, 'win14divPTS_SEARCHED_KW2')
                        if result_element.text == "No Courses available for the selected filters":
                                line_buffer_t.append(current_search + ": " + result_element.text + ".\n")
                        else:
                            class_count_element = driver.find_element(By.ID, 'win14divPTS_LIST_SUMMARY$0')
                            class_count_statement = class_count_element.text.split("\n")[1]
                            if str(Course.Get_Count(course)) != class_count_statement.split(' ')[0]:
                                """ Count does not match the number of class options that the search returned. """
                                line_buffer_t.append(current_search + ": Appears in " + str(Course.Get_Count(course)) \
                                                     + " rows of the csv but fluid search returns: " + class_count_statement + ".\n")
                    except NoSuchElementException:
                        no_result_element = driver.find_element(By.ID, 'PTS_SRCH_PTS_INDEXTIME')
                        line_buffer_t.append(current_search + ": " + 
                                        no_result_element.text.split(".")[0] + ".\n")    
                except:
                    failed_search_queue.put((subject, course))
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

def Refresh_Home_Screen(driver : webdriver.Firefox, lock, flag_lock, continue_flag):
    """
    Every X minutes reload the home screen of the window where the user credentials were verified to avoid a timeout.
    """
    start_time = time.time()
    while True:
        with flag_lock:
            if not continue_flag.value:
                break
        if (time.time() - start_time) > 10 * MINUTE:
            with lock:
                driver.get(driver.current_url)
            start_time = time.time()
        time.sleep(5)

def Offload_Failed_Queue(failed_search_queue : Queue, failed_searches : dict):
    """
    Empty failed_search_queue and move elements to failed_searches dictionary.
    """
    while not failed_search_queue.empty():
        failed_search = failed_search_queue.get()
        subject = failed_search[0]
        course = failed_search[1]
        if subject in failed_searches.keys():
            failed_searches[subject].append(course)
        else:
            failed_searches[subject] = [course]

def Split_Dictionary(classes : dict[list], classes_p : list[dict]):
    """
    Allocate subjects with their corresponding course numbers to evenly search processes.
    """
    [classes_p.append({}) for i in range(NUM_PROCESS)]  
    i = 0
    for subject in classes.keys():
        classes_p[i % NUM_PROCESS][subject] = classes[subject]
        i += 1

def StartProcesses(classes : dict[list[Course]]):
    """
    Creates MAX_PROCESS number of processes to perform searches and one thread to perform refreshes of the home screen. When no
    more processes will be created to conduct searches the main thread will signal the thread performing refreshes to break out
    of its loop and terminate.
    """
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
    continue_flag = Value('i', 1)
    flag_lock = threading.Lock()
    refresh_thread = threading.Thread(target=Refresh_Home_Screen, args=(driver, lock, flag_lock, continue_flag))
    refresh_thread.start()
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
    continue_flag.value = 0
    refresh_thread.join()
    while not queue.empty():
        line_buffer.append(queue.get())
    while not failed_search_queue.empty() and i == MAX_RETRY:
        course = failed_search_queue.get()
        line_buffer.append(str(course[0] + " " + course[1] + ": Error unsuccessful search.\n"))
    return line_buffer

def Find_Course_Index(courses : list[Course], course_number):
    """
    Return index that matches course_number or return None if it does not exist.
    """
    for i in range(len(courses)):
        if course_number == courses[i].Get_Course_Number():
            return i
    return None

if __name__ == "__main__":
    classes = {}
    with open(sys.argv[1], 'r') as csv_file:
        # index[3] : subject
                # index[4] : course number
                csv_reader = csv.reader(csv_file)
                next(csv_reader)
                for row in csv_reader:
                    if row[3] in classes.keys():
                        index = Find_Course_Index(classes[row[3]], row[4])
                        if index == None:
                            classes[row[3]].append(Course(row[3], row[4]))
                        else:
                            classes[row[3]][index].Incriment_Count()
                    else:
                       classes[row[3]] = [Course(row[3], row[4])]
         
    output_filename = sys.argv[1].split(".")[0] + "_FluidSearchResult.txt"
    with open(output_filename, 'w') as file:
       file.writelines(StartProcesses(classes))
    print("Results at " + output_filename)