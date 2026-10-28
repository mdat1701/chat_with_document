-- Extension bắt buộc cho hạ tầng dữ liệu (SADD §2.3, ADR-04).
-- vector:    pgvector — lưu và truy vấn embedding (CHUNK.embedding)
-- unaccent:  tìm kiếm từ khóa không dấu (US-017, T-401)
-- citext:    APP_USER.email không phân biệt hoa/thường (SADD §3.1.1)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS citext;
