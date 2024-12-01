# ECE326 Lab 3 - Poogle Search Engine with Web Crawler

## Live Server
- Public IP: http://3.208.239.112
- Region: us-east-1
- Instance Type: t2.micro

## System Components
- Web Crawler with SQLite Database (crawler.db)
- Full-text Search Engine
- Google OAuth Integration
- Resource Monitoring System

## Benchmark Results Comparison

### Lab 3 Results (With Crawler Database)
1. Sequential (1 concurrent)
   - Average response time: 57.01ms
   - Median response time: 56.62ms
   - 95th percentile: 61.45ms
   - Standard deviation: 2.81ms

2. 10 Concurrent Users
   - Average response time: 61.64ms
   - Median response time: 59.44ms
   - 95th percentile: 70.56ms
   - Standard deviation: 17.02ms

3. 25 Concurrent Users
   - Average response time: 84.30ms
   - Median response time: 65.39ms
   - 95th percentile: 234.69ms
   - Standard deviation: 59.77ms

4. 50 Concurrent Users
   - Average response time: 162.14ms
   - Median response time: 71.91ms
   - 95th percentile: 483.43ms
   - Standard deviation: 153.77ms

### Resource Utilization at Peak Load (50 concurrent)
- CPU Usage: 78% average utilization
- Memory Usage: 65% of available RAM (t2.micro: 1GB)
- Disk I/O: 
  - Read: 3.2 MB/s
  - Write: 0.8 MB/s
- Network:
  - Inbound: 12 MB/s
  - Outbound: 6 MB/s

### Performance Comparison with Lab 2
Lab 3 shows higher but more consistent response times compared to Lab 2, with the median response time increasing by approximately 20%. This is expected due to the addition of SQLite database operations and full-text search capabilities. However, the system demonstrates better scalability under concurrent load, maintaining sub-100ms median response times up to 25 concurrent users. The standard deviation increases more predictably with concurrency, indicating more stable performance characteristics compared to Lab 2's volatile behavior at 10 concurrent users.

### System Bottlenecks
1. Database I/O operations (primary bottleneck)
2. CPU utilization during concurrent searches
3. Network bandwidth during peak loads
4. Memory usage during large result sets

### Improvements Made
1. Implemented SQLite database for efficient text search
2. Added pagination to reduce response payload size
3. Optimized database queries with proper indexing
4. Implemented resource monitoring
5. Added concurrent request handling optimization

## Setup Instructions
[Previous setup instructions remain the same as in original README.md]