WITH customer_base AS (
  SELECT
    -- Primary key (using customer_unique_id as the unique identifier)
    customer_unique_id as customer_key,
    
    -- Customer identifiers (take any customer_id for each unique customer)
    ANY_VALUE(customer_id) as customer_id_original,

    -- Location data (cleaned from staging - should be consistent for each customer)
    ANY_VALUE(customer_city) as customer_city,
    ANY_VALUE(customer_state) as customer_state,
    ANY_VALUE(customer_zip_prefix) as customer_zip_prefix
    
  FROM {{ ref('stg_customers') }}
  WHERE customer_id IS NOT NULL
      AND customer_unique_id IS NOT NULL
  GROUP BY customer_unique_id
),

customer_regions AS (
  SELECT
    c.*,
    
    -- Regional classifications via seed table join
    COALESCE(r.region, 'Unknown') as customer_region,
    COALESCE(r.economic_zone, 'Unknown') as customer_economic_zone,
    
    -- Full state name for display
    COALESCE(r.state_name, c.customer_state) as customer_state_name
    
  FROM customer_base c
  LEFT JOIN {{ ref('brazil_state_regions') }} r
    ON UPPER(c.customer_state) = UPPER(r.state_code)
)

SELECT * FROM customer_regions
ORDER BY customer_key