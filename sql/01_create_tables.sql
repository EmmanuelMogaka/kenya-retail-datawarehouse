CREATE TABLE dim_date (
  date_key INT PRIMARY KEY,
  full_date DATE,
  month INT,
  quarter INT,
  year INT,
  is_weekend BOOLEAN
);

CREATE TABLE dim_store (
  store_key INT PRIMARY KEY,
  store_name VARCHAR(100),
  town VARCHAR(100),
  region VARCHAR(100)
);

CREATE TABLE dim_product (
  product_key INT PRIMARY KEY,
  product_name VARCHAR(150),
  category VARCHAR(100),
  cost_price DECIMAL(10,2)
);

CREATE TABLE dim_customer (
  customer_key INT PRIMARY KEY,
  customer_name VARCHAR(150),
  join_date DATE
);

CREATE TABLE dim_payment_method (
  payment_key INT PRIMARY KEY,
  method_name VARCHAR(50)
);

CREATE TABLE fact_sales (
  sale_line_id INT PRIMARY KEY,
  date_key INT,
  foreign key (date_key) references dim_date(date_key) on delete cascade,  
  store_key INT,
  foreign key (store_key) references dim_store(store_key) on delete cascade,  
  product_key INT, 
  foreign key (product_key) references dim_product(product_key) on delete cascade,  
  customer_key INT,
  foreign key (customer_key) references dim_customer(customer_key) on delete cascade,  
  payment_key INT,
  foreign key (payment_key) references dim_payment_method(payment_key) on delete cascade,  
  quantity INT,
  unit_price DECIMAL(10,2),
  discount DECIMAL(10,2),
  total_amount DECIMAL(10,2)
);S