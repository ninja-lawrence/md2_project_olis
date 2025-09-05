WITH order_items_base AS (
  SELECT
    -- Surrogate key: unique identifier for each order item
    CONCAT(order_id, '-', order_item_id) as order_item_sk,
    
    -- Foreign keys for dimension joins
    order_id as order_key,
    product_id as product_key,
    seller_id as seller_key,
    
    -- Measures from order items
    price as item_price,
    freight_value,
    1 as quantity,  -- Each order item represents 1 product
    
    -- Calculate total item value (price + freight)
    price + freight_value as total_item_value
    
  FROM {{ ref('stg_order_items') }}
  WHERE order_id IS NOT NULL 
    AND product_id IS NOT NULL 
    AND seller_id IS NOT NULL
),

enriched_orders AS (
  SELECT
    oi.*, -- All columns from order_items_base
    
    -- Customer key from customers table (using customer_unique_id)
    c.customer_unique_id as customer_key,
    -- Date key for temporal analysis
    FORMAT_DATE('%Y-%m-%d', o.order_purchase_timestamp) as date_key
    
  FROM order_items_base oi
  INNER JOIN {{ ref('stg_orders') }} o
    ON oi.order_key = o.order_id
  INNER JOIN {{ ref('stg_customers') }} c
    ON o.customer_id = c.customer_id
  WHERE o.customer_id IS NOT NULL
    AND o.order_purchase_timestamp IS NOT NULL
    AND c.customer_unique_id IS NOT NULL
  ),

final_fact AS (
  SELECT
    -- Primary key
    eo.order_item_sk,
    
    -- Foreign keys to dimensions
    eo.order_key,
    eo.customer_key,
    eo.product_key,
    eo.seller_key,
    eo.date_key,
    
    -- Payment key (nullable - some orders might not have payments)
    p.payment_key,
    
    -- Review key (nullable - not all orders have reviews)
    r.review_key,
    
    -- Measures
    eo.item_price,
    eo.freight_value,
    eo.total_item_value,
    eo.quantity,
    
    -- Payment measures (aggregated per order)
    COALESCE(p.total_payment_value, 0) as payment_value,
    COALESCE(p.total_installments, 1) as total_installments,
    COALESCE(p.payment_methods_count, 1) as payment_methods_count,
    
    -- Payment method flags
    COALESCE(p.uses_credit_card, FALSE) as uses_credit_card,
    COALESCE(p.uses_boleto, FALSE) as uses_boleto,
    COALESCE(p.uses_voucher, FALSE) as uses_voucher,
    COALESCE(p.uses_debit_card, FALSE) as uses_debit_card,
    
    -- Primary payment type
    COALESCE(p.primary_payment_type, 'unknown') as primary_payment_type
    
  FROM enriched_orders eo
  
  -- Join with payments (LEFT JOIN - some orders might not have payments)
  LEFT JOIN {{ ref('dim_payments') }} p
    ON eo.order_key = p.payment_key
    
  -- Join with reviews (LEFT JOIN - not all orders have reviews)
  LEFT JOIN {{ ref('dim_reviews') }} r
    ON eo.order_key = r.review_key
)

SELECT * FROM final_fact
ORDER BY order_item_sk