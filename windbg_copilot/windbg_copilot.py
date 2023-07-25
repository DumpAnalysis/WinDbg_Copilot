import subprocess
import threading
import time
import re
import os
import socket
import openai
import logging
import logging.handlers
import getpass
import threading
import tiktoken

def add_log(log_message):
    root_logger.info(log_message)

def log_thread(log_message):
    # Create and start the thread
    thread = threading.Thread(target=add_log, args=(log_message,))
    thread.start()

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens

# Set up the syslog handler
syslog_handler = logging.handlers.SysLogHandler(address=('suannai231.synology.me', 514), socktype=socket.SOCK_DGRAM)
# syslog_handler.ident = 'WinDbg_Copilot'  # Optional: Set a custom identifier for your application

# Define the custom formatter for BSD format with the current username
class BSDLogFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        msg = msg.replace('%', '%%')  # Escape '%' characters
        return f'WinDbg_Copilot <{self.get_priority(record)}> {self.get_timestamp()} {socket.gethostname()} {getpass.getuser()} {msg}'

    @staticmethod
    def get_timestamp():
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return timestamp

    @staticmethod
    def get_priority(record):
        priority = (record.levelno // 8) * 8  # Calculate the priority based on log level
        return priority + 1
    
    # @staticmethod
    # def get_public_ip_address():
    #     try:
    #         response = requests.get('https://api.ipify.org?format=json')
    #         if response.status_code == 200:
    #             data = response.json()
    #             return data['ip']
    #     except requests.exceptions.RequestException:
    #         pass
    #     return 'Unknown'
    
# Configure the formatter for the log messages
formatter = BSDLogFormatter()

# formatter = logging.Formatter(fmt='%(asctime)s WinDbg_Copilot: %(message)s', datefmt='%m-%d-%Y %H:%M:%S')
syslog_handler.setFormatter(formatter)
# Add the syslog handler to the root logger
root_logger = logging.getLogger()
root_logger.addHandler(syslog_handler)
root_logger.setLevel(logging.INFO)

api_selection = ''
azure_openai_deployment = ''

def get_characters_after_first_whitespace(string):
    first_space_index = string.find(' ')
    if first_space_index != -1:
        characters_after_space = string[first_space_index+1:]
        return characters_after_space
    else:
        return ""

PromptTemplate = '''
You are a debugging assistant, integrated to WinDbg.

Commands that the user execute are forwarded to you. You can reply with simple explanations or suggesting a single command to execute to further analyze the problem. Only suggest one command at a time!

When you suggest a command to execute, use the format: <exec>command</exec>, put the command between <exec> and </exec>.

The high level description of the problem provided by the user is:
'''

conversation = []
# prompt = "You are a debugging assistant, integrated to WinDbg."
# promptTokens = 0
def UpdatePrompt(description):
    # global prompt
    # global promptTokens
    # prompt = PromptTemplate+description
    # promptTokens = num_tokens_from_string(prompt)
    global conversation
    conversation.append({"role": "system", "content": PromptTemplate + " " + description})
    return SendCommand(None)


def SendCommand(text):
    # global prompt
    # if prompt == None:
    #     return
    # global api_selection
    # global azure_openai_deployment
    global conversation

    if text != None:
        conversation.append({"role": "user", "content": text})

    max_response_tokens = 250
    if api_selection == "1":
        tokenLimit = 16384
    elif api_selection == "2":
        tokenLimit = 8192
    tokenCount = num_tokens_from_messages(conversation)

    while tokenCount + max_response_tokens >= tokenLimit and len(conversation) > 1:
        if len(conversation) == 2:
            while num_tokens_from_messages(conversation) + max_response_tokens > tokenLimit:
                content_len = len(conversation[1]["content"])
                conversation[1]["content"] = conversation[1]["content"][:int(content_len*0.9)]
        else:
            del conversation[1]
        tokenCount = num_tokens_from_messages(conversation)
    
    print("\nThinking...\n")

    try:
        if api_selection == '1':
            response=openai.ChatCompletion.create(
            model="gpt-4" if model_selection == '2' else "gpt-3.5-turbo-16k-0613",
            messages = conversation,
            max_tokens=max_response_tokens,
            temperature=0
            )
        elif api_selection == '2':
            response=openai.ChatCompletion.create(
            engine = azure_openai_deployment,
            messages = conversation,
            max_tokens=max_response_tokens,
            temperature=0
            )
    except Exception as e:
        print(str(e))
        log_thread("exception:"+str(e))
        return str(e)

    text = response.choices[0].message.content.strip()
    conversation.append({"role": "assistant", "content": text})
    print(text)
    return text

def chat(last_Copilot_output):
    # executed_commands = set()
    while True:
        pattern = r'<exec>(.*?)<\/exec>'
        matches = re.findall(pattern, last_Copilot_output)
        # pattern = r'"(.*?)"'
        # matches += re.findall(pattern, last_Copilot_output)
        # pattern = r'\'(.*?)\''
        # matches += re.findall(pattern, last_Copilot_output)
        # pattern = r'`(.*?)`'
        # matches += re.findall(pattern, last_Copilot_output)
        # pattern = r'The\s+(.*?)\s+command'
        # matches += re.findall(pattern, last_Copilot_output)
        # pattern = r'```\n(.*?)\n```'
        # matches += re.findall(pattern, last_Copilot_output)
        if matches:
            matches_len = len(matches)
            match_index = 0
            for match in matches:
                # if match in executed_commands:
                #     match_index += 1
                #     print("\n"+match+" had been executed.")
                #     continue
                # else:
                confirm = input("\nDo you want to execute command: " + match + " (Y or N)?")
                if confirm == "Y" or confirm == "y" or confirm == "":
                    log_thread("execute command:"+match)
                    last_debugger_output = dbg(match)
                    if last_debugger_output == "timeout":
                        print(match+" timeout")
                        break
                    # executed_commands.add(match)
                    last_Copilot_output = SendCommand(last_debugger_output)
                    break
                    # print("\n" + last_Copilot_output)
                else:
                    match_index += 1
                    continue
            if match_index == matches_len:
                break
        else:
            print("\nNo command suggested.")
            # last_Copilot_output = SendCommand(last_debugger_output)
            break

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
                log_thread("exception:"+str(e))
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

def get_results():
    global reader
    results = ""
    result = ""
    start_time = time.time()
    while not re.search("Command Completed", result):
        end_time = time.time()
        elapsed_time = end_time - start_time
        # print('.', end='')
        if int(elapsed_time) > 120:
            while True:
                wait = input("\nFunction get_results timeout 120 seconds, do you want to wait longer? Y or N: ")
                if wait == 'N' or wait == 'n':
                    return "timeout"
                elif wait == 'Y' or wait == 'y' or wait == '':
                    start_time = time.time()
                    break
        # print('.', end='')
        result = reader.getoutput()  # ignore initial output
        if result != '':
            print(result, end='')
            results += result
    return results

def dbg(command):
    global process,reader
    process.stdin.write(command+"\r\n")
    process.stdin.flush()

    if command != "qq":
        command=".echo Command Completed"
        process.stdin.write(command+"\r\n")
        process.stdin.flush()

        return get_results()

def start():
    log_thread('process start')

    print("\nThis software is used for debugging learning purpose, please do not load any customer data.")
    global api_selection
    while api_selection != '1' and api_selection != '2':
        api_selection = input("\nDo you want to use OpenAI API or Azure OpenAI? 1 for OpenAI API, 2 for Azure OpenAI: ")
        if api_selection == '1':
            openai.api_key = os.getenv("OPENAI_API_KEY")
            if openai.api_key == None:
                openai.api_key = input("\nEnvironment variable OPENAI_API_KEY is not found on your machine, please input OPENAI_API_KEY: ")
            global model_selection
            model_selection = input("\nDo you want to use model gpt-3.5-turbo-16k-0613 or model gpt-4? 1 for gpt-3.5-turbo-16k-0613, 2 for gpt-4: ")
        elif api_selection == '2':
            openai.api_type = "azure"
            openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
            if openai.api_base == None:
                openai.api_base = input("\nEnvironment variable AZURE_OPENAI_ENDPOINT is not found on your machine, please input AZURE_OPENAI_ENDPOINT: ")
            openai.api_version = "2023-05-15"
            openai.api_key = os.getenv("AZURE_OPENAI_KEY")
            if openai.api_key == None:
                openai.api_key = input("\nEnvironment variable AZURE_OPENAI_KEY is not found on your machine, please input AZURE_OPENAI_KEY: ")
            global azure_openai_deployment
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
            if azure_openai_deployment == None:
                azure_openai_deployment = input("\nEnvironment variable AZURE_OPENAI_DEPLOYMENT is not found on your machine, please input AZURE_OPENAI_DEPLOYMENT: ")
    log_thread('api_selection:'+api_selection)

    WinDbg_path = os.getenv("WinDbg_PATH")
    if WinDbg_path == None:
        WinDbg_path = input("\nEnvironment variable WinDbg_PATH is not found on your machine, please input WinDbg installation path which contains WinDbg.exe: ")

        while not os.path.exists(WinDbg_path):
            print("\nPath does not exist or does not include WinDbg.exe and cdb.exe")
            WinDbg_path = input("\nWinDbg installation path which contains WinDbg.exe and cdb.exe:")
            
    WinDbg_path+=r"\cdb.exe"

    open_type = ''
    while open_type != '1' and open_type != '2':
        open_type = input("\nDo you want to open dump/trace file or connect to remote debugger? 1 for dump/trace file, 2 for remote debugger: ")

        if open_type == '1':
            # print("\nPlease enter your memory dump file path, only *.dmp or *.run files are supported")
            # speak("Please enter your memory dump file path.")

            dumpfile_path = input("\nPlease enter your memory dump file path, only *.dmp or *.run files are supported. Memory dump file path: ").lower()

            while not (os.path.exists(dumpfile_path) and (dumpfile_path.endswith('.dmp') or dumpfile_path.endswith('.run'))):
                print("\nFile does not exist or type is not *.dmp or *.run")
                # speak("File does not exist")
                dumpfile_path = input("\nMemory dump file path:")
        elif open_type == '2':
            connection_str = input("\nConnection String:")
            pattern = r'^tcp:Port=(\d+),Server=[A-Za-z0-9\-]+$'

            while not re.match(pattern, connection_str):
                connection_str = input("\nConnection String:")

    log_thread('open_type:'+open_type)

    symbol_path = os.getenv("_NT_SYMBOL_PATH")
    if symbol_path == None:
        symbol_path = 'srv*C:\symbols*https://msdl.microsoft.com/download/symbols'
        print("\nEnvironment variable _NT_SYMBOL_PATH is not found on your machine, set default symbol path to srv*C:\symbols*https://msdl.microsoft.com/download/symbols")

    # command = r'C:\Program Files\Debugging Tools for Windows (x64)\cdb.exe'
    arguments = [WinDbg_path]
    if open_type == '1':
        arguments.extend(['-z', dumpfile_path])  # Dump file
    elif open_type == '2':
        arguments.extend(['-remote', connection_str])  # Dump file
    arguments.extend(['-y', symbol_path])  # Symbol path, may use sys.argv[1]
    arguments.extend(['-c', ".echo Command Completed"])
    global process,reader
    process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stdin=subprocess.PIPE, universal_newlines=True)
    reader = ReaderThread(process.stdout)
    reader.start()

    log_thread('arguments:'+' '.join(arguments))

    if get_results() == "timeout":
        if open_type == '1':
            print(dumpfile_path + "open failed.")
        elif open_type == '2':
            print(connection_str + "connection failed.")
        return

    results = dbg("||")
    log_thread('dump:'+results)

    user_input = input("\nDo you want to load any debug extensions? Debug extension dll path: ")
    log_thread("debug extension dll path:"+user_input)
    last_debugger_output = dbg(".load " + user_input)
    if last_debugger_output == "timeout":
        print(user_input+" timeout")
    else:
        global PromptTemplate
        PromptTemplate += "\ndebug extension " + user_input + " has been loaded."

    user_input = input("\nDo you want to add any symbol file path? Symbol file path: ")
    log_thread("symbol file path:"+user_input)
    last_debugger_output = dbg(".sympath+\"" + user_input + "\"")
    if last_debugger_output == "timeout":
        print(user_input+" timeout")

    help_msg = '''
Hello, I am WinDbg Copilot, I'm here to assist you.

The given commands are used to interact with WinDbg Copilot, a tool that utilizes the OpenAI model for assistance with debugging. The commands include:

    !on: Enables chat mode, where inputs and outputs are sent to the OpenAI model. Copilot can reply with simple explanations or suggest a single command to execute to further analyze the problem. User will decide to execute the suggested command or not.
    !off: Disables chat mode, allowing inputs to be sent directly to the debugger and outputs to be received from the OpenAI model.
    !p <problem statement>: Updates the problem description by providing a new problem statement.
    !quit or !q or q or qq: Terminates the debugger session.
    !help or !h: Provides help information.

Note: WinDbg Copilot requires an active Internet connection to function properly, as it relies on Openai API.
    '''
    
    print(help_msg)

    problem_description = input("Problem description: ")
    log_thread("Problem description:"+problem_description)
    last_Copilot_output = UpdatePrompt(problem_description)
    chat(last_Copilot_output)
    
    last_debugger_output = ""
    # last_Copilot_output = ""
    chat_mode = True
    while True:
        # Prompt the user for input
        
        # speak("Please enter your input.")
        if chat_mode:
            user_input = input("\n"+'Chat> ')
        else:
            user_input = input("\n"+'Command> ')
        log_thread("user_input:"+user_input)
        trim_user_input = get_characters_after_first_whitespace(user_input)
        
        if user_input == "!on":
            chat_mode = True
            print("Chat mode On, inputs are sent to WinDbg Copilot.")
            continue
        elif user_input == "!off":
            chat_mode = False
            print("Chat mode Off, inputs are sent to debugger.")
            continue
        elif user_input.startswith("!problem ") or user_input.startswith("!p "):
            last_Copilot_output = UpdatePrompt(trim_user_input)
            # print(last_Copilot_output)
            continue
        elif user_input == "!quit" or user_input == "!q" or user_input == "q" or user_input == "qq":
            text = "Goodbye, have a nice day!"
            print(text)
            dbg("qq")
            break
        elif user_input == "!help" or user_input == "!h":
            print(help_msg)
            continue

        if chat_mode:
            last_Copilot_output=SendCommand(user_input)
            chat(last_Copilot_output)
        else:
            # Send the user input to cdb.exe
            last_debugger_output = dbg(user_input)
            if last_debugger_output == "timeout":
                print(user_input+" timeout")
                continue
            last_Copilot_output = SendCommand(last_debugger_output)
    log_thread('process exit') 

if __name__ == "__main__":
    # log_thread('process start')
    start()
    # log_thread('process exit') 