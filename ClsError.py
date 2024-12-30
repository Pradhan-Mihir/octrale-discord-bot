from multipledispatch import dispatch


class Error:
    filepath = "Error.log"
    message = ""

    def __init__(self):
        self.file = None

    @dispatch(str)
    def log(self, text: str):
        try:
            self.file = open(self.filepath, "a")
            self.file.write(text + "\n")
        except Exception as e:
            print(e)
        finally:
            if self.file is not None:
                self.file.close()

    @dispatch(str, str)
    def log(self, method: str, text: str):
        try:
            file = open(self.filepath, "a")
            self.message = "Method: " + method + " | Error: " + text
            file.write(self.message)
        except Exception as e:
            print(e)
        finally:
            if self.file is not None:
                self.file.close()

    @dispatch(Exception, str)
    def log(self, e: Exception, text: str):
        try:
            file = open(self.filepath, "a")
            file.write("+++++++++++Error Start+++++++++++\n")
            self.message = "Message: " + text + "\n"
            file.write(self.message)
            file.write(e.__str__())
            file.write("\n")
            file.write("+++++++++++Error End+++++++++++\n")
        except Exception as e:
            print(e)
        finally:
            if self.file is not None:
                self.file.close()

    @dispatch(str, Exception)
    def log(self, text: str, e: str):
        try:
            file = open(self.filepath, "a")
            file.write("+++++++++++Error Start+++++++++++\n")
            self.message = "Message: " + text + "\n"
            file.write(self.message)
            file.write(e.__str__())
            file.write("\n")
            file.write("+++++++++++Error End+++++++++++\n")
        except Exception as e:
            print(e)
        finally:
            if self.file is not None:
                self.file.close()
