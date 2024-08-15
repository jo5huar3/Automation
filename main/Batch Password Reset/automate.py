import csv
import sys
from selenium import webdriver
from selenium.webdriver.firefox.service import Service


def Automate(input_set: dict[list], driver: webdriver.Firefox, url_start: str):
    line_buffer = []
    for key in input_set.keys():
        try:
            pass

        except:
            pass
    
    return line_buffer


def Start(input_set: dict[list]):
    driver = webdriver.Firefox(service=Service(
        service_args=['--marionette-port', '2828', '--connect-existing']))
    driver.implicitly_wait(5)
    url_start = driver.current_url
    return Automate(input_set, driver, url_start)




if __name__ == "__main__":
    input = {}
    with open(sys.argv[1], 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)
        for row in csv_reader:
            search_key = (row[0], row[1])
            if search_key in input.keys():
                input[search_key].append(row[2])
            else:
                input[search_key] = [row[2]]
    output = Start(input)
    if len(output) != 0:
        output_filename = sys.argv[1].split(".")[0] + "_Result.txt"
        with open(output_filename, 'w') as file:
            file.writelines(output) 