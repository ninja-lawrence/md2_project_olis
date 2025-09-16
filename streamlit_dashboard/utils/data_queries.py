"""
Data Query Functions for Olist Analytics Dashboard
Implements queries for all 8 critical business questions using BigQuery marts
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, Tuple
from .bigquery_client import execute_query, init_connection
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Load .env (prefer .env, fallback to .env.sample / env_sample) ---
root_dir = Path(__file__).resolve().parents[2]  # go up 2 levels
env_candidates = [root_dir / ".env", root_dir / ".env.sample", root_dir / "env_sample"]

for p in env_candidates:
    if p.exists():
        load_dotenv(dotenv_path=p)
        logger.info("Loaded environment variables from %s", p)
        break
else:
    logger.warning("No .env file found; relying on existing environment variables")

PROJECT_ID = os.getenv("PROJECT_ID")  # or your project var
# --- Resolve marts dataset name robustly ---
RAW_NAME = os.getenv("MARTS_DATASET_NAME", "").strip()

def ensure_marts_suffix(name: str) -> str:
    """Append '_marts' only if not already present; raise if empty."""
    if not name:
        raise EnvironmentError("MARTS_DATASET_NAME is not set (or empty).")
    return name if name.endswith("_marts") else f"{name}_marts"

try:
    marts_dataset = ensure_marts_suffix(RAW_NAME)
except EnvironmentError as e:
    # You can choose to default or hard-fail; here we hard-fail loudly.
    logger.error(str(e))
    raise

@st.cache_data(ttl=600)
def get_monthly_sales_trends(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get monthly sales trends data for business question 1
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Monthly sales metrics with columns:
            - month_year: Month and year
            - total_orders: Number of orders
            - total_sales: Total sales revenue
            - avg_order_value: Average order value
            - total_items: Total items sold
    """
    try:
        # Build query with optional filters
        year_condition = f"AND d.year = {year_filter}" if year_filter and year_filter != "All Years" else ""
        region_condition = f"AND c.customer_region = '{region_filter}'" if region_filter and region_filter != "All Regions" else ""
        
        query = f"""
        SELECT 
            FORMAT_DATE('%Y-%m', MIN(d.full_date)) as month_year,
            d.year,
            d.month,
            d.month_name,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(SUM(f.payment_value), 2) as total_payments,
            ROUND(SUM(f.total_item_value) / COUNT(DISTINCT f.order_key), 2) as avg_order_value,
            ROUND(SUM(f.payment_value) / COUNT(DISTINCT f.order_key), 2) as avg_payment_value
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key
        JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key
        WHERE 1=1 {year_condition} {region_condition}
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get monthly sales trends: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_top_products_categories(limit: int = 20, year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get top products and categories performance for business question 2
    
    Args:
        limit (int): Number of top categories to return
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Category performance metrics
    """
    try:
        # Build query with optional filters
        year_condition = ""
        region_condition = ""
        joins = [f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_products` p ON f.product_key = p.product_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            year_condition = f"AND d.year = {year_filter}"
            
        if region_filter and region_filter != "All Regions":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key")
            region_condition = f"AND c.customer_region = '{region_filter}'"
        
        query = f"""
        SELECT 
            p.product_category_english as category,
            COUNT(DISTINCT p.product_key) as unique_products,
            COUNT(f.order_item_sk) as items_sold,
            ROUND(SUM(f.total_item_value), 2) as total_revenue,
            ROUND(AVG(f.total_item_value), 2) as avg_item_value,
            ROUND(SUM(f.freight_value), 2) as total_freight,
            ROUND(SUM(f.item_price), 2) as total_item_price
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        WHERE p.product_category_english IS NOT NULL {year_condition} {region_condition}
        GROUP BY p.product_category_english
        ORDER BY total_revenue DESC
        LIMIT {limit}
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get top products categories: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_sales_by_region(year_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get geographic sales distribution for business question 3
    
    Args:
        year_filter (str, optional): Filter by specific year
        
    Returns:
        pd.DataFrame: Regional sales metrics for customers and sellers
    """
    try:
        # Build query with optional year filter
        year_condition = ""
        joins = [
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_sellers` s ON f.seller_key = s.seller_key"
        ]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            year_condition = f"AND d.year = {year_filter}"
        
        query = f"""
        SELECT 
            c.customer_region,
            s.seller_region,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.total_item_value), 2) as avg_order_value,
            COUNT(DISTINCT c.customer_key) as unique_customers,
            COUNT(DISTINCT s.seller_key) as unique_sellers
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        WHERE c.customer_region IS NOT NULL AND s.seller_region IS NOT NULL {year_condition}
        GROUP BY c.customer_region, s.seller_region
        ORDER BY total_sales DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get sales by region: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_sales_by_state(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get state-level sales distribution for detailed geographic analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: State-level sales metrics
    """
    try:
        # Build query with optional filters
        conditions = ["c.customer_state IS NOT NULL"]
        joins = [f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            c.customer_state,
            c.customer_region,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.total_item_value), 2) as avg_order_value,
            COUNT(DISTINCT c.customer_key) as unique_customers
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY c.customer_state, c.customer_region
        ORDER BY total_sales DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get sales by state: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_customer_seller_flow(year_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get customer-seller regional flow analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        
    Returns:
        pd.DataFrame: Customer-seller flow metrics
    """
    try:
        # Build query with optional year filter
        year_condition = ""
        joins = [
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_sellers` s ON f.seller_key = s.seller_key"
        ]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            year_condition = f"AND d.year = {year_filter}"
        
        query = f"""
        SELECT 
            CASE 
                WHEN c.customer_region = s.seller_region THEN 'Same Region'
                ELSE 'Cross Region'
            END as transaction_type,
            c.customer_region,
            s.seller_region,
            COUNT(DISTINCT f.order_key) as total_orders,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            COUNT(DISTINCT c.customer_key) as unique_customers,
            COUNT(DISTINCT s.seller_key) as unique_sellers
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        WHERE c.customer_region IS NOT NULL AND s.seller_region IS NOT NULL {year_condition}
        GROUP BY 
            CASE 
                WHEN c.customer_region = s.seller_region THEN 'Same Region'
                ELSE 'Cross Region'
            END,
            c.customer_region, 
            s.seller_region
        ORDER BY total_sales DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get customer seller flow: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_customer_behavior(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get customer purchase behavior analysis for business question 4
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Customer behavior metrics and segments
    """
    try:
        # Build query with optional filters
        conditions = []
        if year_filter and year_filter != "All Years":
            conditions.append(f"d.year = {year_filter}")
        if region_filter and region_filter != "All Regions":
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        WITH order_summary AS (
            -- First, aggregate sales at the ORDER level (not order item level)
            SELECT 
                f.order_key,
                c.customer_key,
                c.customer_region,
                d.full_date,
                SUM(f.total_item_value) as order_total_value,
                COUNT(f.order_item_sk) as items_in_order
            FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
            JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key
            JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key
            {where_clause}
            GROUP BY f.order_key, c.customer_key, c.customer_region, d.full_date
        ),
        customer_metrics AS (
            -- Then, aggregate at the customer level
            SELECT 
                customer_key,
                customer_region,
                COUNT(DISTINCT order_key) as order_count,  -- Now correctly counting unique orders
                ROUND(SUM(order_total_value), 2) as total_spent,
                ROUND(AVG(order_total_value), 2) as avg_order_value,
                DATE_DIFF(MAX(full_date), MIN(full_date), DAY) as customer_lifetime_days
            FROM order_summary
            GROUP BY customer_key, customer_region
        )
        SELECT 
            customer_region,
            COUNT(*) as customer_count,
            ROUND(AVG(order_count), 1) as avg_orders_per_customer,
            ROUND(AVG(total_spent), 2) as avg_customer_lifetime_value,
            ROUND(AVG(avg_order_value), 2) as avg_order_value,
            ROUND(AVG(customer_lifetime_days), 1) as avg_customer_lifetime_days,
            SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END) as one_time_customers,
            SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) as repeat_customers
        FROM customer_metrics
        GROUP BY customer_region
        ORDER BY avg_customer_lifetime_value DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get customer behavior: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_customer_segmentation(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get detailed customer segmentation analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Customer segments with detailed metrics
    """
    try:
        # Build query with optional filters
        conditions = []
        if year_filter and year_filter != "All Years":
            conditions.append(f"d.year = {year_filter}")
        if region_filter and region_filter != "All Regions":
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        WITH customer_metrics AS (
            SELECT 
                c.customer_key,
                c.customer_region,
                COUNT(DISTINCT f.order_key) as order_count,
                ROUND(SUM(f.total_item_value), 2) as total_spent,
                ROUND(AVG(f.total_item_value), 2) as avg_order_value,
                DATE_DIFF(MAX(d.full_date), MIN(d.full_date), DAY) as customer_lifetime_days
            FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
            JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key
            JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key
            {where_clause}
            GROUP BY c.customer_key, c.customer_region
        ),
        customer_segments AS (
            SELECT 
                *,
                CASE 
                    WHEN order_count = 1 THEN 'One-Time Customer'
                    WHEN order_count BETWEEN 2 AND 5 THEN 'Regular Customer'
                    WHEN order_count > 5 THEN 'Loyal Customer'
                END as customer_segment,
                CASE 
                    WHEN total_spent <= 100 THEN 'Low Value'
                    WHEN total_spent BETWEEN 101 AND 500 THEN 'Medium Value'
                    WHEN total_spent > 500 THEN 'High Value'
                END as value_segment
            FROM customer_metrics
        )
        SELECT 
            customer_segment,
            value_segment,
            COUNT(*) as customer_count,
            ROUND(AVG(order_count), 1) as avg_orders,
            ROUND(AVG(total_spent), 2) as avg_lifetime_value,
            ROUND(AVG(avg_order_value), 2) as avg_order_value,
            ROUND(AVG(customer_lifetime_days), 1) as avg_lifetime_days,
            ROUND(SUM(total_spent), 2) as segment_total_value
        FROM customer_segments
        GROUP BY customer_segment, value_segment
        ORDER BY segment_total_value DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get customer segmentation: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_customer_frequency_analysis(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get customer purchase frequency distribution
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Purchase frequency distribution
    """
    try:
        # Build query with optional filters
        conditions = []
        if year_filter and year_filter != "All Years":
            conditions.append(f"d.year = {year_filter}")
        if region_filter and region_filter != "All Regions":
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        WITH customer_order_counts AS (
            SELECT 
                c.customer_key,
                COUNT(DISTINCT f.order_key) as order_count,
                ROUND(SUM(f.total_item_value), 2) as total_spent
            FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
            JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key
            JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key
            {where_clause}
            GROUP BY c.customer_key
        )
        SELECT 
            order_count,
            COUNT(*) as customer_count,
            ROUND(AVG(total_spent), 2) as avg_customer_value,
            ROUND(SUM(total_spent), 2) as total_segment_value,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage_of_customers
        FROM customer_order_counts
        GROUP BY order_count
        ORDER BY order_count
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get customer frequency analysis: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_payment_analysis(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get payment method impact analysis for business question 5
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Payment method usage and impact metrics
    """
    try:
        # Build query with optional filters
        conditions = []
        joins = [f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_payments` p ON f.payment_key = p.payment_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key")
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            p.primary_payment_type,
            COUNT(DISTINCT f.order_key) as total_orders,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.total_item_value), 2) as avg_order_value,
            ROUND(AVG(p.total_installments), 1) as avg_installments,
            SUM(CASE WHEN p.uses_credit_card THEN 1 ELSE 0 END) as credit_card_orders,
            SUM(CASE WHEN p.uses_boleto THEN 1 ELSE 0 END) as boleto_orders,
            SUM(CASE WHEN p.uses_voucher THEN 1 ELSE 0 END) as voucher_orders,
            ROUND(SUM(f.payment_value), 2) as total_payments,
            ROUND(AVG(p.payment_methods_count), 1) as avg_payment_methods_count
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY p.primary_payment_type
        ORDER BY total_sales DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get payment analysis: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_installment_analysis(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get detailed installment usage analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Installment usage patterns and impact
    """
    try:
        # Build query with optional filters
        conditions = []
        joins = [f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_payments` p ON f.payment_key = p.payment_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key")
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            p.total_installments,
            COUNT(DISTINCT f.order_key) as order_count,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.total_item_value), 2) as avg_order_value,
            ROUND(SUM(f.payment_value), 2) as total_payments,
            ROUND(AVG(f.payment_value), 2) as avg_payment_value,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage_of_orders
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY p.total_installments
        ORDER BY p.total_installments
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get installment analysis: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_seller_performance(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get seller performance analysis for business question 6
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Seller performance metrics by region
    """
    try:
        # Build query with optional filters
        conditions = ["s.seller_region IS NOT NULL"]
        joins = [f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_sellers` s ON f.seller_key = s.seller_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            conditions.append(f"s.seller_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            s.seller_region,
            COUNT(DISTINCT s.seller_key) as unique_sellers,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_revenue,
            ROUND(AVG(f.total_item_value), 2) as avg_item_value,
            ROUND(SUM(f.total_item_value) / COUNT(DISTINCT s.seller_key), 2) as revenue_per_seller,
            COUNT(DISTINCT f.product_key) as unique_products_sold,
            ROUND(AVG(f.freight_value), 2) as avg_freight_value,
            ROUND(SUM(f.freight_value), 2) as total_freight_revenue
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY s.seller_region
        ORDER BY total_revenue DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get seller performance: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_top_sellers(limit: int = 20, year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get top individual sellers by performance
    
    Args:
        limit (int): Number of top sellers to return
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Top sellers with detailed metrics
    """
    try:
        # Build query with optional filters
        conditions = ["s.seller_region IS NOT NULL"]
        joins = [f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_sellers` s ON f.seller_key = s.seller_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            conditions.append(f"s.seller_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            s.seller_key,
            s.seller_region,
            s.seller_state,
            s.seller_city,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_revenue,
            ROUND(AVG(f.total_item_value), 2) as avg_item_value,
            COUNT(DISTINCT f.product_key) as unique_products_sold,
            ROUND(SUM(f.freight_value), 2) as total_freight_revenue,
            COUNT(DISTINCT f.customer_key) as unique_customers_served
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY s.seller_key, s.seller_region, s.seller_state, s.seller_city
        ORDER BY total_revenue DESC
        LIMIT {limit}
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get top sellers: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_seller_product_diversity(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get seller product diversity analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Seller product diversity metrics
    """
    try:
        # Build query with optional filters
        conditions = ["s.seller_region IS NOT NULL", "p.product_category_english IS NOT NULL"]
        joins = [
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_sellers` s ON f.seller_key = s.seller_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_products` p ON f.product_key = p.product_key"
        ]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            conditions.append(f"s.seller_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        WITH seller_categories AS (
            SELECT 
                s.seller_region,
                s.seller_key,
                COUNT(DISTINCT p.product_category_english) as category_count,
                COUNT(DISTINCT f.product_key) as product_count,
                ROUND(SUM(f.total_item_value), 2) as total_revenue
            FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
            {' '.join(joins)}
            {where_clause}
            GROUP BY s.seller_region, s.seller_key
        )
        SELECT 
            seller_region,
            COUNT(*) as seller_count,
            ROUND(AVG(category_count), 1) as avg_categories_per_seller,
            ROUND(AVG(product_count), 1) as avg_products_per_seller,
            ROUND(AVG(total_revenue), 2) as avg_revenue_per_seller,
            SUM(CASE WHEN category_count = 1 THEN 1 ELSE 0 END) as single_category_sellers,
            SUM(CASE WHEN category_count > 3 THEN 1 ELSE 0 END) as diverse_sellers
        FROM seller_categories
        GROUP BY seller_region
        ORDER BY avg_revenue_per_seller DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get seller product diversity: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_reviews_sales_correlation(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get reviews and sales correlation analysis for business question 7
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Review impact on sales performance
    """
    try:
        # Build query with optional filters
        conditions = []
        joins = [f"LEFT JOIN `{PROJECT_ID}.{marts_dataset}.dim_reviews` r ON f.review_key = r.review_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key")
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            CASE 
                WHEN r.review_key IS NULL THEN 'No Review'
                WHEN r.review_score >= 4 THEN 'Positive (4-5)'
                WHEN r.review_score = 3 THEN 'Neutral (3)'
                ELSE 'Negative (1-2)'
            END as review_category,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.total_item_value), 2) as avg_item_value,
            ROUND(AVG(COALESCE(r.review_score, 0)), 1) as avg_review_score,
            COUNT(r.review_key) as reviews_count,
            COUNT(*) - COUNT(r.review_key) as no_review_count,
            COUNT(DISTINCT f.order_key) as total_orders
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY 
            CASE 
                WHEN r.review_key IS NULL THEN 'No Review'
                WHEN r.review_score >= 4 THEN 'Positive (4-5)'
                WHEN r.review_score = 3 THEN 'Neutral (3)'
                ELSE 'Negative (1-2)'
            END
        ORDER BY total_sales DESC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get reviews sales correlation: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_review_score_distribution(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get detailed review score distribution analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Review score distribution with sales impact
    """
    try:
        # Build query with optional filters
        conditions = []
        joins = [f"LEFT JOIN `{PROJECT_ID}.{marts_dataset}.dim_reviews` r ON f.review_key = r.review_key"]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key")
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            COALESCE(r.review_score, 0) as review_score,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.total_item_value), 2) as avg_item_value,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(r.review_key) as actual_reviews,
            ROUND(COUNT(f.order_item_sk) * 100.0 / SUM(COUNT(f.order_item_sk)) OVER(), 1) as percentage_of_items
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY COALESCE(r.review_score, 0)
        ORDER BY review_score
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get review score distribution: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_review_timing_analysis(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get review timing impact analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Review timing and its impact on scores
    """
    try:
        # Build query with optional filters
        conditions = ["r.review_key IS NOT NULL"]  # Only analyze actual reviews
        joins = [
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_reviews` r ON f.review_key = r.review_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_orders` o ON f.order_key = o.order_key"
        ]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key")
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        WITH review_timing AS (
            SELECT 
                r.days_to_review,
                r.review_score,
                f.total_item_value,
                f.order_key,
                CASE 
                    WHEN r.days_to_review <= 7 THEN 'Quick (≤7 days)'
                    WHEN r.days_to_review <= 30 THEN 'Normal (8-30 days)'
                    WHEN r.days_to_review <= 90 THEN 'Delayed (31-90 days)'
                    ELSE 'Very Late (>90 days)'
                END as timing_category
            FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
            {' '.join(joins)}
            {where_clause}
            AND r.days_to_review IS NOT NULL
        )
        SELECT 
            timing_category,
            COUNT(*) as review_count,
            ROUND(AVG(review_score), 1) as avg_review_score,
            ROUND(SUM(total_item_value), 2) as total_sales,
            ROUND(AVG(total_item_value), 2) as avg_item_value,
            ROUND(AVG(days_to_review), 1) as avg_days_to_review
        FROM review_timing
        GROUP BY timing_category
        ORDER BY avg_days_to_review
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get review timing analysis: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_delivery_patterns(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get delivery time patterns analysis for business question 8
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Delivery performance metrics by region
    """
    try:
        # Build query with optional filters
        conditions = ["o.days_to_delivery IS NOT NULL"]
        joins = [
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_orders` o ON f.order_key = o.order_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key"
        ]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            c.customer_region,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(o.days_to_delivery), 1) as avg_delivery_days,
            ROUND(AVG(o.delivery_vs_estimate_days), 1) as avg_delivery_vs_estimate,
            SUM(CASE WHEN o.is_delivered_on_time THEN 1 ELSE 0 END) as on_time_deliveries,
            SUM(CASE WHEN NOT o.is_delivered_on_time THEN 1 ELSE 0 END) as late_deliveries,
            ROUND(
                SUM(CASE WHEN o.is_delivered_on_time THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT f.order_key), 
                1
            ) as on_time_delivery_rate,
            ROUND(MIN(o.days_to_delivery), 1) as min_delivery_days,
            ROUND(MAX(o.days_to_delivery), 1) as max_delivery_days,
            ROUND(STDDEV(o.days_to_delivery), 1) as delivery_days_stddev
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY c.customer_region
        ORDER BY avg_delivery_days ASC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get delivery patterns: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_delivery_time_distribution(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get delivery time distribution analysis
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Delivery time distribution by categories
    """
    try:
        # Build query with optional filters
        conditions = ["o.days_to_delivery IS NOT NULL"]
        joins = [
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_orders` o ON f.order_key = o.order_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key"
        ]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            CASE 
                WHEN o.days_to_delivery <= 5 THEN 'Very Fast (≤5 days)'
                WHEN o.days_to_delivery <= 10 THEN 'Fast (6-10 days)'
                WHEN o.days_to_delivery <= 20 THEN 'Normal (11-20 days)'
                WHEN o.days_to_delivery <= 30 THEN 'Slow (21-30 days)'
                ELSE 'Very Slow (>30 days)'
            END as delivery_speed_category,
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(o.days_to_delivery), 1) as avg_days_in_category,
            SUM(CASE WHEN o.is_delivered_on_time THEN 1 ELSE 0 END) as on_time_orders,
            ROUND(
                SUM(CASE WHEN o.is_delivered_on_time THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT f.order_key), 
                1
            ) as on_time_rate,
            ROUND(AVG(o.delivery_vs_estimate_days), 1) as avg_vs_estimate
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY 
            CASE 
                WHEN o.days_to_delivery <= 5 THEN 'Very Fast (≤5 days)'
                WHEN o.days_to_delivery <= 10 THEN 'Fast (6-10 days)'
                WHEN o.days_to_delivery <= 20 THEN 'Normal (11-20 days)'
                WHEN o.days_to_delivery <= 30 THEN 'Slow (21-30 days)'
                ELSE 'Very Slow (>30 days)'
            END
        ORDER BY avg_days_in_category
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get delivery time distribution: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_delivery_efficiency_analysis(year_filter: Optional[str] = None, region_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Get delivery efficiency analysis by customer-seller region combinations
    
    Args:
        year_filter (str, optional): Filter by specific year
        region_filter (str, optional): Filter by specific region
        
    Returns:
        pd.DataFrame: Delivery efficiency by region combinations
    """
    try:
        # Build query with optional filters
        conditions = ["o.days_to_delivery IS NOT NULL"]
        joins = [
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_orders` o ON f.order_key = o.order_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_customers` c ON f.customer_key = c.customer_key",
            f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_sellers` s ON f.seller_key = s.seller_key"
        ]
        
        if year_filter and year_filter != "All Years":
            joins.append(f"JOIN `{PROJECT_ID}.{marts_dataset}.dim_date` d ON f.date_key = d.date_key")
            conditions.append(f"d.year = {year_filter}")
            
        if region_filter and region_filter != "All Regions":
            conditions.append(f"c.customer_region = '{region_filter}'")
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
        SELECT 
            c.customer_region,
            s.seller_region,
            CASE 
                WHEN c.customer_region = s.seller_region THEN 'Same Region'
                ELSE 'Cross Region'
            END as delivery_type,
            COUNT(DISTINCT f.order_key) as total_orders,
            ROUND(AVG(o.days_to_delivery), 1) as avg_delivery_days,
            ROUND(AVG(o.delivery_vs_estimate_days), 1) as avg_vs_estimate,
            ROUND(
                SUM(CASE WHEN o.is_delivered_on_time THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT f.order_key), 
                1
            ) as on_time_rate,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.freight_value), 2) as avg_freight_cost
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        {' '.join(joins)}
        {where_clause}
        GROUP BY c.customer_region, s.seller_region, 
            CASE 
                WHEN c.customer_region = s.seller_region THEN 'Same Region'
                ELSE 'Cross Region'
            END
        ORDER BY avg_delivery_days ASC
        """
        
        return execute_query(query)
        
    except Exception as e:
        logger.error(f"Failed to get delivery efficiency analysis: {str(e)}")
        return pd.DataFrame()

def get_dashboard_summary() -> Dict[str, Any]:
    """
    Get summary metrics for dashboard overview
    
    Returns:
        Dict: Summary metrics for all business areas
    """
    try:
        # Get basic counts and totals
        summary_query = """
        SELECT 
            COUNT(DISTINCT f.order_key) as total_orders,
            COUNT(f.order_item_sk) as total_items,
            ROUND(SUM(f.total_item_value), 2) as total_sales,
            ROUND(AVG(f.total_item_value), 2) as avg_order_value,
            COUNT(DISTINCT f.customer_key) as unique_customers,
            COUNT(DISTINCT f.seller_key) as unique_sellers,
            COUNT(DISTINCT f.product_key) as unique_products
        FROM `{PROJECT_ID}.{marts_dataset}.fact_sales` f
        """
        
        summary_df = execute_query(summary_query)
        
        if len(summary_df) > 0:
            return {
                'total_orders': int(summary_df.iloc[0]['total_orders']),
                'total_items': int(summary_df.iloc[0]['total_items']),
                'total_sales': float(summary_df.iloc[0]['total_sales']),
                'avg_order_value': float(summary_df.iloc[0]['avg_order_value']),
                'unique_customers': int(summary_df.iloc[0]['unique_customers']),
                'unique_sellers': int(summary_df.iloc[0]['unique_sellers']),
                'unique_products': int(summary_df.iloc[0]['unique_products'])
            }
        else:
            return {}
            
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {str(e)}")
        return {}

def validate_marts_data() -> Dict[str, bool]:
    """
    Validate that all required marts tables exist and have data
    
    Returns:
        Dict: Validation status for each table
    """
    required_tables = [
        'fact_sales',
        'dim_customers', 
        'dim_products',
        'dim_sellers',
        'dim_orders',
        'dim_payments',
        'dim_reviews',
        'dim_date'
    ]
    
    validation_results = {}
    
    for table in required_tables:
        try:
            query = f"SELECT COUNT(*) as count FROM `{PROJECT_ID}.{marts_dataset}.{table}`"
            result = execute_query(query)
            validation_results[table] = len(result) > 0 and result.iloc[0]['count'] > 0
        except Exception as e:
            logger.error(f"Failed to validate table {table}: {str(e)}")
            validation_results[table] = False
    
    return validation_results





