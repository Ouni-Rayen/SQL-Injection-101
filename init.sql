CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL,
  password VARCHAR(100) NOT NULL,
  role VARCHAR(20) NOT NULL
);

-- guest comes first on purpose: "' OR 1=1#" logs in as guest, not admin
INSERT INTO users (username, password, role) VALUES
  ('guest', 'guest', 'user'),
  ('admin', 'k9#Tz!q2Lw8vRm4xPd7sNb3e', 'admin');
