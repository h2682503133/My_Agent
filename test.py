import subprocess

def search(keyword):
    return subprocess.run(["powershell", "-Command", "clawhub search weather"])
print(search("weather"))
a=input()