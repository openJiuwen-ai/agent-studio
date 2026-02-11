from enum import Enum
from datetime import datetime

class PrintTarget(Enum):
    FILE = 1
    CONSOLE = 2
    BOTH = 3

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Reporter:
    def __init__(self, filename: str, printTarget: PrintTarget):
        self.filename = filename
        self.printTarget = printTarget

    def addStep(self, moduleName: str, stepName: str, isSuccess: bool, errorText: str = ""):
        """
        Prints a formatted log line:
        [datetime] [moduleName] [stepName] [SUCCESS/FAILED] errorText
        errorText is printed only when isSuccess == False
        """

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if isSuccess else "FAILED"

        if isSuccess:
            line = f"[{timestamp}] [{moduleName}] [{stepName}] [{status}]"
        else:
            line = f"[{timestamp}] [{moduleName}] [{stepName}] [{status}] {errorText}"

        # Print to console
        if self.printTarget in (PrintTarget.CONSOLE, PrintTarget.BOTH):
            print(line)

        # Write to file
        if self.printTarget in (PrintTarget.FILE, PrintTarget.BOTH):
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(line + "\n")
