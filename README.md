# Sam-Proj
- Reputation server stress test home project
- This code is running a stress test on Sam's reputation rerver, and generating a CSV file with all responses from the server.

# Requirments
- Python3.7+
- PIP
- requests

# How To Use
#Clone this repository
- $https://github.com/avivdo/Sam-Proj.git
- open CLI
- run python reputation_service_stress_test.py
- Insert requested parameters
- Wait for results

# Working Process
- Getting input from the user
- Generate urls for the server stress test based on the user's input
- Creating threads that will run get requests over and over till timeout/keyboard interrupt(CTRL+C in Windows)
- Starting all threads
- Summarize result after all threads done working
- Write two CSV files: one with all responds from the server, and the second one with the result summarize
- print result summarize to CLI

# My Test Environment
- Windows 11
- Python 3.10


