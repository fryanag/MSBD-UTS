CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    unit_price NUMERIC(14,2) NOT NULL CHECK (unit_price >= 0),
    stock_qty INTEGER NOT NULL CHECK (stock_qty >= 0),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales (
    transaction_id VARCHAR(40) PRIMARY KEY,
    transaction_date TIMESTAMP NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(14,2) NOT NULL CHECK (unit_price >= 0),
    total_amount NUMERIC(14,2) NOT NULL CHECK (total_amount >= 0),
    payment_method VARCHAR(30) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(transaction_date);
CREATE INDEX IF NOT EXISTS idx_sales_product_date ON sales(product_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_products_stock ON products(stock_qty);
