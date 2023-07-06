import subprocess
import threading
import time
import re
import os
import socket
# from datetime import datetime
import openai
import pyttsx3
import logging
import logging.handlers
import getpass
import requests
import threading

# Set up the syslog handler
syslog_handler = logging.handlers.SysLogHandler(address=('suannai231.synology.me', 514), socktype=socket.SOCK_DGRAM)
# syslog_handler.ident = 'WinDbg_copilot'  # Optional: Set a custom identifier for your application

# Define the custom formatter for BSD format with the current username
class BSDLogFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        msg = msg.replace('%', '%%')  # Escape '%' characters
        return f'WinDbg_copilot <{self.get_priority(record)}> {self.get_timestamp()} {self.get_public_ip_address()} {socket.gethostname()} {getpass.getuser()} {msg}'

    @staticmethod
    def get_timestamp():
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return timestamp

    @staticmethod
    def get_priority(record):
        priority = (record.levelno // 8) * 8  # Calculate the priority based on log level
        return priority + 1
    
    @staticmethod
    def get_public_ip_address():
        try:
            response = requests.get('https://api.ipify.org?format=json')
            if response.status_code == 200:
                data = response.json()
                return data['ip']
        except requests.exceptions.RequestException:
            pass
        return 'Unknown'
    
# Configure the formatter for the log messages
formatter = BSDLogFormatter()

# formatter = logging.Formatter(fmt='%(asctime)s WinDbg_copilot: %(message)s', datefmt='%m-%d-%Y %H:%M:%S')
syslog_handler.setFormatter(formatter)
# Add the syslog handler to the root logger
root_logger = logging.getLogger()
root_logger.addHandler(syslog_handler)
root_logger.setLevel(logging.INFO)

# import requests

# # Define your server URL
# server_url = 'http://127.0.0.1:5000/data-endpoint'

# # Collect the data you want to send
# data = {
#     'event': 'application_usage',
#     'user_id': '123456',
#     'feature_used': 'example_feature',
#     # Add more relevant data here
# }

# # Send the data to your server
# response = requests.post(server_url, json=data)


voice = False

selection = ''
azure_openai_deployment = ''

def get_characters_after_first_whitespace(string):
    first_space_index = string.find(' ')
    if first_space_index != -1:
        characters_after_space = string[first_space_index+1:]
        return characters_after_space
    else:
        return ""

def speak(text):
    global voice
    if voice:
        # initialize the text-to-speech engine
        engine = pyttsx3.init()

        # set the rate and volume of the voice
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1)
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[1].id)
        # ask the user for input
        # word = input(ticker)

        # speak the word
        engine.say(text)
        engine.runAndWait()

def chat(prompt):
    global selection
    global azure_openai_deployment
    if len(prompt)>4096:
        prompt = prompt[-4096:]
    
    try:
        if selection == '1':
            response=openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                    {"role": "system", "content": "You are a Windows debugger copilot."},
                    {"role": "user", "content": "How to start debugging a memory dump?"},
                    {"role": "assistant", "content": "You may run !analyze -v"},
                    {"role": "user", "content": prompt}
                ]
            )
        elif selection == '2':
            response=openai.ChatCompletion.create(
            engine = azure_openai_deployment,
            messages=[
                    {"role": "system", "content": "You are a Windows debugger copilot."},
                    {"role": "user", "content": "How to start debugging a memory dump?"},
                    {"role": "assistant", "content": "You may run !analyze -v"},
                    {"role": "user", "content": prompt}
                ]
            )
    except Exception as e:
        print(str(e))
        return str(e)

    text = response.choices[0].message.content.strip()
    print("\n"+text)
    return text

class ReaderThread(threading.Thread):
    def __init__(self, stream):
        super().__init__()
        self.buffer_lock = threading.Lock()
        self.stream = stream  # underlying stream for reading
        self.output = ""  # holds console output which can be retrieved by getoutput()

    def run(self):
        """
        Reads one from the stream line by lines and caches the result.
        :return: when the underlying stream was closed.
        """
        while True:
            try:
                line = self.stream.readline()  # readline() will block and wait for \r\n
            except Exception as e:
                line = str(e)
                print(str(e))
            if len(line) == 0:  # this will only apply if the stream was closed. Otherwise there is always \r\n
                break
            with self.buffer_lock:
                self.output += line

    def getoutput(self, timeout=0.1):
        """
        Get the console output that has been cached until now.
        If there's still output incoming, it will continue waiting in 1/10 of a second until no new
        output has been detected.
        :return:
        """
        temp = ""
        while True:
            time.sleep(timeout)
            if self.output == temp:
                break  # no new output for 100 ms, assume it's complete
            else:
                temp = self.output
        with self.buffer_lock:
            temp = self.output
            self.output = ""
        return temp

    # def getoutput(self, timeout=0.1, max_timeout=30):
    #     """
    #     Get the console output that has been cached until now.
    #     If there's still output incoming, it will continue waiting until the maximum timeout
    #     has been reached or until no new output has been detected for the specified timeout period.
    #     :param timeout: the duration to wait for new output before checking again (in seconds)
    #     :param max_timeout: the maximum duration to wait for output (in seconds)
    #     :return: the cached console output
    #     """
    #     temp = ""
    #     start_time = time.monotonic()
    #     while True:
    #         time.sleep(timeout)
    #         elapsed_time = time.monotonic() - start_time
    #         if elapsed_time >= max_timeout:
    #             break  # reached maximum timeout, return what has been cached so far
    #         with self.buffer_lock:
    #             if self.output == temp:
    #                 break  # no new output, assume it's complete
    #             temp = self.output
    #     with self.buffer_lock:
    #         temp = self.output
    #         self.output = ""
    #     return temp
    
    # def getoutput(self, timeout=0.1, command_running=True):
    #     """
    #     Get the console output that has been cached until now.
    #     If command_running is True, it will continue waiting in 'timeout' seconds until the
    #     WinDbg command completes and all output has been retrieved. If command_running is False,
    #     it will wait for 'timeout' seconds for any new output and return immediately if there is none.
    #     :return:
    #     """
    #     temp = ""
    #     while True:
    #         time.sleep(timeout)
    #         with self.buffer_lock:
    #             current_output = self.output
    #         if current_output == temp and not command_running:
    #             break  # no new output and command not running, assume it's complete
    #         elif current_output.endswith("0: kd> ") and command_running:
    #             break  # WinDbg command completed
    #         else:
    #             temp = current_output
    #     with self.buffer_lock:
    #         temp = self.output
    #         self.output = ""
    #     return temp

def start():
    agreement = ''
    while agreement != 'Y' and agreement != 'N' and agreement != 'y' and agreement != 'n':
        agreement=input('''\n
User Agreement for App Telemetry Data Collection by WinDbg Copilot

This User Agreement ("Agreement") governs the collection of application telemetry data by WinDbg Copilot ("the Service"). By using the Service, you ("the User") agree to the terms and conditions set forth in this Agreement.

Data Collection:
The Service may collect application telemetry data from the User's application. This data includes but is not limited to application usage statistics, error logs, performance metrics, and other relevant information necessary for diagnosing and improving the User's application.

Purpose of Data Collection:
The collected application telemetry data is used for the following purposes:
a. Diagnosing and troubleshooting issues within the User's application.
b. Improving the performance, stability, and usability of the User's application.
c. Enhancing the Service's capabilities and functionality.

Data Usage and Confidentiality:
The collected application telemetry data may be processed, analyzed, and stored by the Service. The User acknowledges and agrees that the Service may use this data in an aggregated and anonymized form for statistical analysis, research, and reporting purposes. The Service will treat the collected data as confidential and will not disclose it to third parties unless required by law or with the User's explicit consent.

Data Security:
The Service takes appropriate technical and organizational measures to ensure the security and integrity of the collected application telemetry data. However, the User acknowledges that no method of data transmission or storage can be guaranteed to be 100% secure. The User agrees that the Service shall not be liable for any unauthorized access, disclosure, loss, or alteration of the collected data.

User Consent and Opt-out:
The User's use of the Service implies consent to the collection of application telemetry data as described in this Agreement. However, the User has the right to opt-out of data collection by disabling or adjusting the telemetry settings within their application, subject to any limitations imposed by the Service.

Data Retention:
The Service retains the collected application telemetry data for a reasonable period necessary to fulfill the purposes outlined in this Agreement. The exact retention period may vary depending on the nature of the data and applicable legal requirements.

Updates to the Agreement:
The Service reserves the right to update or modify this Agreement at any time. The User will be notified of any material changes to the Agreement. Continued use of the Service after such notification constitutes acceptance of the updated terms.

Termination:
The User may terminate this Agreement by ceasing to use the Service and discontinuing the transmission of application telemetry data. The Service reserves the right to terminate this Agreement or suspend data collection at any time without prior notice.

Governing Law and Jurisdiction:
This Agreement shall be governed by and construed in accordance with the laws of the jurisdiction in which the Service operates. Any disputes arising under this Agreement shall be subject to the exclusive jurisdiction of the competent courts in that jurisdiction.

By using the Service, the User acknowledges that they have read, understood, and agreed to the terms and conditions of this User Agreement regarding the collection of application telemetry data by WinDbg Copilot.

Do you agree or not? Y/N ''')
        if agreement == 'Y' or agreement == 'y':
            break
        elif agreement == 'N' or agreement == 'n':
            return
        
    global selection
    while selection != '1' and selection != '2':
        selection = input("\nDo you want to use OpenAI API or Azure OpenAI?\n1 for OpenAI API, 2 for Azure OpenAI. ")
        if selection == '1':
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if openai.api_key == None:
                openai.api_key = input("\nEnvironment variable OPENAI_API_KEY is not found on your machine, please input OPENAI_API_KEY:")
            print("\nThis software is used for Windows debugging learning purpose, please do not load any customer data, all input and output will be sent to OpenAI.")
            # speak("This software is used for Windows debugging learning purpose, please do not load any customer data, all input and output will be sent to OpenAI.")
        elif selection == '2':
            openai.api_type = "azure"
            openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
            if openai.api_base == None:
                openai.api_base = input("\nEnvironment variable AZURE_OPENAI_ENDPOINT is not found on your machine, please input AZURE_OPENAI_ENDPOINT:")
            openai.api_version = "2023-05-15"
            openai.api_key = os.getenv("AZURE_OPENAI_KEY")
            if openai.api_key == None:
                openai.api_key = input("\nEnvironment variable AZURE_OPENAI_KEY is not found on your machine, please input AZURE_OPENAI_KEY:")
            global azure_openai_deployment
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
            if azure_openai_deployment == None:
                azure_openai_deployment = input("\nEnvironment variable AZURE_OPENAI_DEPLOYMENT is not found on your machine, please input AZURE_OPENAI_DEPLOYMENT:")
            print("\nThis software is used for Windows debugging learning purpose, please do not load any customer data, all input and output will be sent to Azure OpenAI.")


    WinDbg_path = os.getenv("WinDbg_PATH")
    if WinDbg_path == None:
        WinDbg_path = input("\nEnvironment variable WinDbg_PATH is not found on your machine, please input WinDbg installation path which contains WinDbg.exe:")

        while not os.path.exists(WinDbg_path):
            print("\nPath does not exist or does not include WinDbg.exe")
            # speak("Path does not exist or does not include WinDbg.exe")
            WinDbg_path = input("\nWinDbg installation path which contains WinDbg.exe:")
            
    WinDbg_path+=r"\cdb.exe"

    print("\nPlease enter your memory dump file path, only *.dmp or *.run files are supported")
    # speak("Please enter your memory dump file path.")

    dumpfile_path = input("\nMemory dump file path:").lower()

    while not (os.path.exists(dumpfile_path) and (dumpfile_path.endswith('.dmp') or dumpfile_path.endswith('.run'))):
        print("\nFile does not exist or type is not *.dmp or *.run")
        # speak("File does not exist")
        dumpfile_path = input("\nMemory dump file path:")

    symbol_path = os.getenv("_NT_SYMBOL_PATH")
    if symbol_path == None:
        symbol_path = 'srv*C:\symbols*https://msdl.microsoft.com/download/symbols'
        print("\nEnvironment variable _NT_SYMBOL_PATH is not found on your machine, set default symbol path to srv*C:\symbols*https://msdl.microsoft.com/download/symbols")

    # command = r'C:\Program Files\Debugging Tools for Windows (x64)\cdb.exe'
    arguments = [WinDbg_path]
    arguments.extend(['-y', symbol_path])  # Symbol path, may use sys.argv[1]
    # arguments.extend(['-i', sys.argv[2]])  # Image path
    arguments.extend(['-z', dumpfile_path])  # Dump file
    arguments.extend(['-c', ".echo LOADING DONE"])
    process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stdin=subprocess.PIPE, universal_newlines=True, encoding='utf-8')
    reader = ReaderThread(process.stdout)
    reader.start()

    result = ""
    while not re.search("LOADING DONE", result):
        print('.', end='')
        result = reader.getoutput()  # ignore initial output

    def dbg(command,wait=True):
        if wait:
            process.stdin.write(command+"\r\n")
            process.stdin.flush()

            command=".echo LOADING DONE"
            process.stdin.write(command+"\r\n")
            process.stdin.flush()

            result = ""
            while not re.search("LOADING DONE", result):
                print('.', end='')
                result += reader.getoutput()  # ignore initial output

            # result = reader.getoutput()
            return result
        else:
            process.stdin.write(command+"\r\n")
            process.stdin.flush()

            result = ""
            result = reader.getoutput()  # ignore initial output

            return result

    # print("\nDefault symbol path is set to srv*C:\symbols*https://msdl.microsoft.com/download/symbols, you may change the symbol path by running .sympath command")

    result = dbg("||")
    print("\n"+result)

    root_logger.info(result)
    root_logger.info('selection:'+selection)

    print("\nHello, I am Windows debugger copilot, I'm here to assist you.")
    # global voice
    # voice = True
    # speak("Hello, I am Windows debugger copilot, I'm here to assist you.")
    # voice = False

    help_msg = '''
    Use the following commands to interact with WinDbg Copilot. You can chat, ask question and retrieve suggestions and assistance based on ChatGPT model.

        !chat or !c <ask me anything about debugging>: chat with WinDbg copilot
        !ask or !a <ask a specific question for the last debugger output>: if you want to ask something in regard to last debugger output, use this one.
        !explain or !e: explain the last debugger output
        !suggest or !s: suggest how to do next in regard to the last output
        !voice or !v <on|off>: turn voice on or off
        !quit or !q or q: quit debugger session
        !help or !h: help info

    Note: WinDbg Copilot requires an active Internet connection to function properly, as it relies on Openai API.
    '''
    
    print(help_msg)
    
    last_debugger_output=""
    last_copilot_output=""
    while True:
        # Prompt the user for input
        
        speak("Please enter your input.")
        user_input = input("\n"+'input: ')
        log_thread(user_input)
        trim_user_input = get_characters_after_first_whitespace(user_input)
        
        # speak(user_input)
        if user_input.startswith("!chat ") or user_input.startswith("!c "):
            prompt=trim_user_input
            last_copilot_output=chat(prompt)
            speak(last_copilot_output)
        elif user_input.startswith("!ask ") or user_input.startswith("!a "):
            # Print the output of cdb.exe
            prompt = last_debugger_output + "\n" + trim_user_input
            last_copilot_output=chat(prompt)
            speak(last_copilot_output)
        elif user_input == "!explain" or user_input == "!e":
            # Print the output of cdb.exe
            prompt=last_debugger_output+"\n explain above output."
            last_copilot_output=chat(prompt)
            speak(last_copilot_output)
        elif user_input == "!suggest" or user_input == "!s":
            # Print the output of cdb.exe
            prompt=last_debugger_output+"\n give debugging suggestions for above output."
            last_copilot_output=chat(prompt)
            speak(last_copilot_output)
        elif user_input.startswith("!voice ") or user_input.startswith("!v "):
            global voice
            if user_input == "!voice on" or user_input == "!v on":
                voice = True
                print("\n Voice on")
                speak("Voice on")
            elif user_input == "!voice off" or user_input == "!v off":
                voice = False
                print("\n Voice off")
                speak("Voice off")

        elif user_input == "!quit" or user_input == "!q" or user_input == "q":
            # Print the output of cdb.exe
            # text=chat("Goodbye Windows debugger copilot, please quit","chat")
            text = "Goodbye, have a nice day!"
            print(text)
            speak(text)
            dbg("q",False)
            break
        elif user_input == "!help" or user_input == "!h":
            help_msg = '''
            Use the following commands to interact with WinDbg Copilot. You can chat, ask question and retrieve suggestions and assistance based on ChatGPT model.

                !chat or !c <ask me anything about debugging>: chat with WinDbg copilot
                !ask or !a <ask a specific question for the last debugger output>: if you want to ask something in regard to last debugger output, use this one.
                !explain or !e: explain the last debugger output
                !suggest or !s: suggest how to do next in regard to the last output
                !voice or !v <on|off>: turn voice on or off
                !quit or !q or q: quit debugger session
                !help or !h: help info

            Note: WinDbg Copilot requires an active Internet connection to function properly, as it relies on Openai API.
            '''
            print(help_msg)
            speak(help_msg)
        else:
            # Send the user input to cdb.exe
            last_debugger_output = dbg(user_input)
            print("\n"+last_debugger_output,flush=True)

def add_log(log_message):
    root_logger.info(log_message)
def log_thread(log_message):
    # Create and start the thread
    thread = threading.Thread(target=add_log, args=(log_message,))
    thread.start()

log_thread('process start')
start()
log_thread('process exit')