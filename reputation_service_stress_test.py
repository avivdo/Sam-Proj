import os.path
import requests
import random
from time import time, sleep
from threading import Thread, Event, get_native_id
import csv
from datetime import datetime
import numpy as np

# globals
THREAD_RES_DICT = {}
MAX_THREADS = 250
MAX_DOMAINS = 5000


def beauty_wait(event: Event):
    """
    Beautify waiting screen while tasks are running
    :param event: Thread-safe flag to stop the function
    :return:
    """
    dots = [".  ", ".. ", "..."]
    index = 0
    while not event.is_set():
        print(f"\rRunning{dots[index]}", end="")
        index = (index + 1) % len(dots)
        sleep(1)
    print("\n")


def get_valid_int_val(msg: str, min_val: int = None, max_val: int = None) -> int:
    """
    The function repeatedly asking for an input from the user, until the input will fit the restrictions.

    :param msg: Message to show the user
    :param min_val: Lowest acceptable INT value
    :param max_val: Highest acceptable INT value
    :return: User's input after verifying it matches the given limitations
    """
    while True:  # keep taking an input from the user until it matches the limitations
        val = input(msg)
        try:
            val = int(val)
        except ValueError:
            print(f"ERROR - {val} is not an INT value")
            continue

        # check if the input within the min and max range
        if min_val:
            if val < min_val:
                print(f"ERROR - {val} is lower than the minimum value({min_val})")
                continue
        if max_val:
            if val > max_val:
                print(f"ERROR - {val} is higher than the maximum value({max_val})")
                continue

        break
    return val


def rep_service_stress(event: Event, urls: str, timeout: int, header: dict):
    """
    The function repeatedly making GET requests to a random URLs from a given list,
    and storing the returned data as a dictionary into a global dictionary.
    It will keep running until it will reach timeout or get a keyboard interrupt.

    The dictionary keys: stop_reason, fail, response, request_time
    Global dictionary keys: ID of the thread

    :param event: A thread-safe flag that used here to stop a thread in case of keyboard interrupt
    :param urls: The url to run stress test on
    :param timeout: Time in seconds to stop the thread
    :param header: An authorisation header for the url
    :return:

    """
    start = time()
    res_dict = {"stop_reason": "timeout",
                "fail": 0,
                "response": [],
                "request_time": []}
    request_time = []
    while int(time() - start) < timeout:
        try:  # sending get request, measuring the time of the request
            req_start_time = time()
            req = requests.get(random.choice(urls), headers=header)
            request_time.append(float(f"{time() - req_start_time:.1f}"))
            answer = req.json()
            res_dict["response"].append(answer)
            if req.status_code != 200 or "domain_error" in answer.keys():
                res_dict["fail"] += 1
        except Exception:
            res_dict["fail"] += 1

        if event.is_set():  # KeyboardInterrupt raised to stop the loop in the middle
            res_dict["stop_reason"] = "keyboard interrupt"
            res_dict["request_time"] = request_time
            THREAD_RES_DICT[str(get_native_id())] = res_dict
            return
    else:  # Reached timeout
        res_dict["request_time"] = request_time
        THREAD_RES_DICT[str(get_native_id())] = res_dict
    return


def write_dict_to_csv(data: (list, str), path: str, f_name: str):
    """
    Get a list of dictionaries and a path to save to CSV file in it.
    The function saves a CSV file with the data in the given path if it's exist, otherwise in current folder.

    :param data: A list of dictionaries OR a string to save to a CSV file
    :param path: A system location to save the CSV in
    :param f_name: The name of the CSV file
    :return:
    """
    try:  # check if path exist, re-route to current folder if not
        if not os.path.isdir(path):
            if path != "":
                print("Couldn't find the given path, saving CSV file in current dir.")
                path = ""
        else:
            path += "\\"

        # write data to csv file, keys are the column headers
        with open(path + f_name, "w", newline="") as csv_f:
            if str(type(data[0])).split('\'')[1] == "dict":
                writer = csv.DictWriter(csv_f, fieldnames=list(data[0].keys()))
                writer.writeheader()
            elif str(type(data)).split('\'')[1] == "str":
                writer = csv.writer(csv_f, delimiter="\n")
                data = [data.split("\n")]
            for result in data:
                writer.writerow(result)
    except Exception as ex:
        print(f"Failed to write CSV file\n{ex}")


def urls_generate(domains_file: str, url_base: str):
    """
    Get a domains file and an url, and generate full url for each domain(<url>/<domain>).

    :param domains_file: A .txt file that contains list of domains, one per line.
    :param url_base: An url that we want to attach to him the domains
    :return: A list of urls
    """
    # load the domains from file
    try:
        with open(domains_file, "r") as domains_f:
            all_domains = domains_f.read().splitlines()
    except FileNotFoundError:
        print("Couldn't find 'domains.txt' in current folder\nClosing the program")
        exit(3)
    except Exception as ex:
        print(f"{ex}\nClosing the program")
        exit(4)

    # Generating list of urls based on url and given domains
    url_lst = []
    try:
        for domain in random.sample(all_domains, domains_amount):
            url_lst.append(url_base + domain)
    except ValueError as ex:
        print(f"{ex}\nClosing the program")
        exit(5)
    except Exception as ex:
        print(f"{ex}\nClosing the program")
        exit(6)

    return url_lst


if __name__ == "__main__":
    current_time = datetime.now().strftime('%H_%M_%S')

    # ask for input from the user
    try:
        threads_amount = get_valid_int_val(f"Enter amount of concurrent requests, max {MAX_THREADS}:", min_val=1, max_val=MAX_THREADS)
        domains_amount = get_valid_int_val(f"Enter amount of domains, max {MAX_DOMAINS}:", min_val=1, max_val=MAX_DOMAINS)
        timeout = get_valid_int_val("Enter timeout in seconds:", min_val=1)
        csv_path = input("Enter a path to save the CSV result file(leave empty to save at current location):")
        url_header = {'Authorization': 'Token I_am_under_stress_when_I_test'}
    except KeyboardInterrupt as ex:
        print("\nClosing the program due to a keyboard interrupt ")
        exit(2)

    urls = urls_generate("domains.txt", "https://reputation.gin.dev.securingsam.io/domain/ranking/")
    thread_lst = []
    thread_event = Event()
    beauty_wait_event = Event()
    res_sum = {"stop_reason": "",
               "request_time": [],
               'fail': 0,
               "response": [],
               }
    start_time = time()

    # creating and starting threads that will run the stress function
    try:
        thread_lst.append(Thread(target=beauty_wait, args=(beauty_wait_event,)))
        for _ in range(threads_amount):
            thrd = Thread(target=rep_service_stress, args=(thread_event, urls, timeout, url_header,))
            thread_lst.append(thrd)

        for thread in thread_lst:
            thread.start()

        sleep(timeout)
        res_sum["stop_reason"] = "timeout"
    except KeyboardInterrupt:
        thread_event.set()
        res_sum["stop_reason"] = "keyboard interrupt"
    except Exception as ex:
        print(f"Got an exception:\n{ex}")

    # ensure all threads are done working
    try:
        for thread in thread_lst[1:]:
            if thread.is_alive():
                thread.join()
    except KeyboardInterrupt:
        pass
    beauty_wait_event.set()
    try:
        if thread_lst[0].is_alive():
            thread_lst[0].join()
    except KeyboardInterrupt:
        pass

    end_time = time()

    if bool(THREAD_RES_DICT):  # We got results from the threads, summarize all of them into one result variable
        for thread_dict in THREAD_RES_DICT.values():
            res_sum["request_time"] += thread_dict["request_time"]
            res_sum["fail"] += thread_dict["fail"]
            res_sum["response"] += thread_dict["response"]
        total_req_amount = len(res_sum['request_time'])
        fail_ratio = (res_sum['fail']/total_req_amount)*100
        avg_time_req = f"{sum(res_sum['request_time'])/total_req_amount:.1f}"
    else:  # We got no results from the threads, set default values.
        total_req_amount = 0
        fail_ratio = 0
        avg_time_req = -1

    # write all the server responses to a csv file
    csv_name_response = f"stress_test_responses_{current_time}.csv"
    write_dict_to_csv(res_sum["response"], csv_path, csv_name_response)

    # print summarize to console
    summarize = (f"Test is over!\n" 
                 f"Reason: {res_sum['stop_reason']}\n"
                 f"Time in total: {int(end_time - start_time)} seconds\n"
                 f"Requests in total: {total_req_amount}\n"
                 f"Error rate: {fail_ratio}%({res_sum['fail']}/{total_req_amount})\n"
                 f"P90: {np.percentile(res_sum['request_time'], 90)}\n"
                 f"Average time for one request: {avg_time_req} {'ms' if int(1)==0 else 'seconds'}\n"
                 f"Max time for one request: {max(res_sum['request_time'])} seconds\n"
                 f"Min time for one request: {min(res_sum['request_time'])} seconds")
    csv_name_summarize = f"stress_test_summarize_{current_time}.csv"
    write_dict_to_csv(summarize, csv_path, csv_name_summarize)
    print(summarize)

