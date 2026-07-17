import clr, os, sys
sys.path.insert(0, r"C:\Users\Jweda\Desktop\projects\monitor tool")
os.chdir(r"C:\Users\Jweda\Desktop\projects\monitor tool")
clr.AddReference(r"assets\LibreHardwareMonitorLib.dll")
from LibreHardwareMonitor.Hardware import Computer, SensorType
c = Computer()
c.IsStorageEnabled = True
c.Open()
import time
time.sleep(3)
for h in c.Hardware:
    h.Update()
    for s in h.Sensors:
        if s.SensorType == SensorType.Temperature:
            with open("disk_test.txt", "a") as f:
                f.write(f"{h.Name} | {s.Name}: {s.Value}\n")
c.Close()
