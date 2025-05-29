use `kafka-server-metrics`;

CREATE TABLE server_metrics (
	id INT AUTO_INCREMENT PRIMARY KEY,
	server_id int,
	cpu int,
	ram int,
	disk int
	);
    
CREATE TABLE loadbalancer_logs (
    ip_address VARCHAR(45),
    user_id INT,
    timestamp DATETIME,
    method VARCHAR(10),
    filename VARCHAR(255),
    status_code INT,
    file_size BIGINT
);

select * from server_metrics;
select * from loadbalancer_logs;