import threading
import pyttsx3
import pythoncom

def w():
    pythoncom.CoInitialize()
    engine = pyttsx3.init()
    engine.say('test')
    engine.runAndWait()

t = threading.Thread(target=w)
t.start()
t.join()
