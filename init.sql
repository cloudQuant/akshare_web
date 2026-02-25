-- init.sql: Docker entrypoint initialization script for MySQL
-- Creates the data warehouse database if it doesn't exist

CREATE DATABASE IF NOT EXISTS `akshare_web` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `akshare_data` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant permissions to the application user on both databases
-- (The MYSQL_USER from docker-compose already has access to MYSQL_DATABASE,
--  but we also need access to akshare_data for the data warehouse)
GRANT ALL PRIVILEGES ON `akshare_data`.* TO 'akshare_user'@'%';
FLUSH PRIVILEGES;
