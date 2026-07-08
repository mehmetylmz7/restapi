-- ============================================================
-- Stripe REST API Manager — PDF & Files Tabloları
-- Çalıştırma: MySQL Workbench veya terminalde
--   mysql -u root -p stripe_db < create_pdf_tables.sql
-- ============================================================

USE stripe_db;

-- ── 1. payment_pdfs: Ödeme faturası PDF'leri (LONGBLOB) ─────
CREATE TABLE IF NOT EXISTS payment_pdfs (
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    payment_intent_stripe_id VARCHAR(255) NOT NULL,
    pdf_data                 LONGBLOB NOT NULL,
    olusturma_tarihi         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_payment_pdf (payment_intent_stripe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 2. stripe_files: Stripe'a yüklenen dosyalar ─────────────
CREATE TABLE IF NOT EXISTS stripe_files (
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    stripe_file_id           VARCHAR(255) NOT NULL,
    purpose                  VARCHAR(100) NOT NULL,
    filename                 VARCHAR(255),
    file_size                INT,
    payment_intent_stripe_id VARCHAR(255),
    olusturma_tarihi         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_stripe_file (stripe_file_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
