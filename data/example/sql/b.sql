CREATE TABLE user_profiles (
    profile_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    age INT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
