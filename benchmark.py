import requests
import time
import statistics
import concurrent.futures
import matplotlib.pyplot as plt
from multiprocessing import Process
from monitor import monitor_resources
def measure_response_time(url, query):
    start_time = time.time()
    response = requests.get(f"{url}/home?keywords={query}")
    end_time = time.time()
    return (end_time - start_time) * 1000  # Convert to milliseconds

def run_benchmark(base_url, query, num_requests, concurrent_requests):
    print(f"\nRunning benchmark with {num_requests} total requests ({concurrent_requests} concurrent)...")
    
    times = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [executor.submit(measure_response_time, base_url, query) 
                  for _ in range(num_requests)]
        
        for future in concurrent.futures.as_completed(futures):
            times.append(future.result())
    
    return times

def plot_results(results, title):
    plt.figure(figsize=(10, 6))
    plt.boxplot(results)
    plt.title(title)
    plt.ylabel('Response Time (ms)')
    plt.savefig(f'{title.lower().replace(" ", "_")}.png')
    plt.close()

def main():
    BASE_URL = "http://3.208.239.112"
    TEST_QUERY = "test"
    
    # Start resource monitoring in a separate process
    monitor_process = Process(target=monitor_resources)
    monitor_process.start()
    
    scenarios = [
        (100, 1),    # Sequential
        (100, 10),   # 10 concurrent
        (100, 25),   # 25 concurrent
        (100, 50)    # 50 concurrent
    ]
    
    all_results = []
    
    for total_requests, concurrent in scenarios:
        times = run_benchmark(BASE_URL, TEST_QUERY, total_requests, concurrent)
        all_results.append(times)
        
        print(f"\nResults for {concurrent} concurrent requests:")
        print(f"Average response time: {statistics.mean(times):.2f}ms")
        print(f"Median response time: {statistics.median(times):.2f}ms")
        print(f"95th percentile: {sorted(times)[int(len(times)*0.95)]:.2f}ms")
        print(f"Standard deviation: {statistics.stdev(times):.2f}ms")
    
    plot_results(all_results, "Response Times by Concurrency Level")
    
    # Stop monitoring
    monitor_process.terminate()

if __name__ == "__main__":
    main()