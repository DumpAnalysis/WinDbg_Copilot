README for WinDbg Copilot

WinDbg Copilot is a ChatGPT powered AI assistant integrated with WinDbg. It analyzes the output of the commands, and provides guidance to solve the stated problem.

Prerequisites

        1. Operating System: Windows 11
        2. If you want to use OpenAI API, add environmet variable OPENAI_API_KEY = <openai api key>
        3. If you want to use Azure OpenAI, add following environment variables:
                AZURE_OPENAI_ENDPOINT = <Azure OpenAI Endpoint>
                AZURE_OPENAI_KEY = <Azure OpenAI Key>
                AZURE_OPENAI_DEPLOYMENT = <Azure OpenAI Deployment Name>
        4. The Windows Debugger (WinDbg) installed on your machine, for example: C:\Program Files\Debugging Tools for Windows (x64)
           Add environment variable WinDbg_PATH = C:\Program Files\Debugging Tools for Windows (x64).
           Add environment variable _NT_SYMBOL_PATH = srv*c:\symbols*https://msdl.microsoft.com/download/symbols
        5. python >=3.9, <3.12 installed on your machine.
        6. An Internet connection for downloading and installing the package.

Installation

        Open a command prompt or terminal window, install the WinDbg Copilot package using pip:

                pip install WinDbg-Copilot

        The packages will be downloaded and installed automatically.

Usage

        Open your Python environment or editor and enter the following command:

                import WinDbg_Copilot as Copilot
                Copilot.start()

        Hello, I am WinDbg Copilot, I'm here to assist you.

        The given commands are used to interact with WinDbg Copilot, a tool that utilizes the OpenAI model for assistance with debugging. The commands include:

        !chat: Chat mode, conversation will be sent to OpenAI ChatGPT model, ChatGPT can reply with simple explanations or suggest a single command to execute to further analyze the problem. User will decide to execute the suggested command or not.
        !command: Command mode, user inputs are sent to debugger and debugger outputs will be sent to OpenAI ChatGPT model, ChatGPT can reply with simple explanations or suggest a single command to execute to further analyze the problem.
        !problem <problem statement>: Updates the problem description by providing a new problem statement.
        !quit or !q or q or qq: Terminates the debugger session.
        !help or !h: Provides help information.

        Note: WinDbg Copilot requires an active Internet connection to function properly, as it relies on Openai API.

Uninstallation

        Open a command prompt or terminal window.
        Use pip to uninstall the WinDbg Copilot package:

                pip uninstall WinDbg_Copilot

        The packages will be uninstalled automatically.

Disclaimer: WinDbg Copilot

WinDbg Copilot is an application designed for debugging learning purposes only. It is important to note that this application should not be used to load or handle any customer data. WinDbg Copilot is intended solely for the purpose of providing a platform for debugging practice and learning experiences.

When using WinDbg Copilot, please be aware that any debugging input and output generated during your debugging sessions will be sent to OpenAI or Azure OpenAI according to your selection. This data may be used for analysis and improvement of the application's performance and capabilities. However, it is crucial to understand that no customer data should be loaded or shared through WinDbg Copilot.

WinDbg Copilot project takes the privacy and security of user information seriously and endeavors to handle all data with utmost care and in accordance with applicable laws and regulations. Nevertheless, it is strongly recommended to refrain from providing any sensitive or confidential information while using WinDbg Copilot.

By using WinDbg Copilot, you acknowledge and agree that any debugging input and output you generate may be transmitted to OpenAI or Azure OpenAI for research and development purposes. You also understand that WinDbg Copilot should not be used with customer data and that WinDbg Copilot project is not responsible for any consequences that may arise from the misuse or mishandling of such data.

Please ensure that you exercise caution and adhere to best practices when utilizing WinDbg Copilot to ensure the privacy and security of your own data. WinDbg Copilot project will not be held liable for any damages, losses, or unauthorized access resulting from the misuse of this application.

By proceeding to use WinDbg Copilot, you signify your understanding and acceptance of these terms and conditions.