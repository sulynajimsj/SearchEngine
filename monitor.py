import psutil
import time
import csv

def monitor_resources():
    with open('resource_usage.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'CPU%', 'Memory%', 'Disk_IO_Read', 'Disk_IO_Write', 'Network_Sent', 'Network_Recv'])
        
        while True:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk_io = psutil.disk_io_counters()
            network = psutil.net_io_counters()
            
            writer.writerow([
                time.time(),
                cpu,
                memory,
                disk_io.read_bytes,
                disk_io.write_bytes,
                network.bytes_sent,
                network.bytes_recv
            ])
            time.sleep(1)