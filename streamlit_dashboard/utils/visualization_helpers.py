"""
Visualization Helper Functions for Olist Analytics Dashboard
Provides standardized chart creation functions using Plotly
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional, List, Dict, Any
import streamlit as st

# Color schemes for consistent styling
COLOR_SCHEMES = {
    'primary': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
    'secondary': ['#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
    'diverging': ['#d73027', '#fc8d59', '#fee08b', '#d9ef8b', '#91cf60', '#1a9850'],
    'qualitative': ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33']
}

def create_line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_title: str = None,
    y_title: str = None,
    color_col: Optional[str] = None,
    height: int = 400,
    show_legend: bool = True
) -> go.Figure:
    """
    Create a standardized line chart
    
    Args:
        df: DataFrame with data
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        x_title: X-axis title
        y_title: Y-axis title
        color_col: Column name for color grouping
        height: Chart height
        show_legend: Whether to show legend
        
    Returns:
        Plotly figure object
    """
    if color_col:
        fig = px.line(
            df, 
            x=x_col, 
            y=y_col, 
            color=color_col,
            title=title,
            height=height
        )
    else:
        fig = px.line(
            df, 
            x=x_col, 
            y=y_col,
            title=title,
            height=height
        )
    
    # Standardize styling
    fig.update_layout(
        title_x=0.5,
        title_font_size=16,
        showlegend=show_legend,
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=False
        )
    )
    
    if x_title:
        fig.update_xaxes(title=x_title)
    if y_title:
        fig.update_yaxes(title=y_title)
    
    return fig

def create_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_title: str = None,
    y_title: str = None,
    color_col: Optional[str] = None,
    orientation: str = 'v',
    height: int = 400,
    show_legend: bool = True
) -> go.Figure:
    """
    Create a standardized bar chart
    
    Args:
        df: DataFrame with data
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        x_title: X-axis title
        y_title: Y-axis title
        color_col: Column name for color grouping
        orientation: 'v' for vertical, 'h' for horizontal
        height: Chart height
        show_legend: Whether to show legend
        
    Returns:
        Plotly figure object
    """
    if color_col:
        fig = px.bar(
            df, 
            x=x_col, 
            y=y_col, 
            color=color_col,
            title=title,
            height=height,
            orientation=orientation
        )
    else:
        fig = px.bar(
            df, 
            x=x_col, 
            y=y_col,
            title=title,
            height=height,
            orientation=orientation
        )
    
    # Standardize styling
    fig.update_layout(
        title_x=0.5,
        title_font_size=16,
        showlegend=show_legend,
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=False
        )
    )
    
    if x_title:
        fig.update_xaxes(title=x_title)
    if y_title:
        fig.update_yaxes(title=y_title)
    
    return fig

def create_pie_chart(
    df: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: str,
    height: int = 400,
    show_legend: bool = True
) -> go.Figure:
    """
    Create a standardized pie chart
    
    Args:
        df: DataFrame with data
        names_col: Column name for slice labels
        values_col: Column name for slice values
        title: Chart title
        height: Chart height
        show_legend: Whether to show legend
        
    Returns:
        Plotly figure object
    """
    fig = px.pie(
        df,
        names=names_col,
        values=values_col,
        title=title,
        height=height
    )
    
    # Standardize styling
    fig.update_layout(
        title_x=0.5,
        title_font_size=16,
        showlegend=show_legend,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def create_customer_behavior_pie_chart(
    df: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: str,
    height: int = 400
) -> go.Figure:
    """
    Create a customer behavior pie chart with all possible segments shown in legend
    
    Args:
        df: DataFrame with customer behavior data
        names_col: Column name for segment labels
        values_col: Column name for segment values
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly figure with enhanced legend
    """
    # Define all possible customer behavior segments with descriptions
    all_segments = {
        'One-Time Customer': 'One-Time Customer (1 order)',
        'Regular Customer': 'Regular Customer (2-5 orders)',
        'Loyal Customer': 'Loyal Customer (6+ orders)'
    }
    
    # Create a complete dataset with all segments
    complete_data = []
    for segment, description in all_segments.items():
        # Find if this segment exists in the data
        segment_data = df[df[names_col] == segment]
        if not segment_data.empty:
            value = segment_data[values_col].iloc[0]
            complete_data.append({'segment': description, 'value': value, 'original_name': segment})
        else:
            # Add segment with 0 value to ensure it appears in legend
            complete_data.append({'segment': description, 'value': 0, 'original_name': segment})
    
    # Create pie chart with complete data
    fig = px.pie(
        pd.DataFrame(complete_data),
        names='segment',
        values='value',
        title=title,
        height=height
    )
    
    # Update layout with enhanced styling
    fig.update_layout(
        title_x=0.5,
        title_font_size=16,
        showlegend=True,
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=12)
        )
    )
    
    # Hide segments with 0 values but keep them in legend
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Customers: %{value}<extra></extra>",
        textinfo="percent"
    )
    
    return fig

def create_customer_value_pie_chart(
    df: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: str,
    height: int = 400
) -> go.Figure:
    """
    Create a customer value pie chart with all possible segments shown in legend
    
    Args:
        df: DataFrame with customer value data
        names_col: Column name for segment labels
        values_col: Column name for segment values
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly figure with enhanced legend
    """
    # Define all possible customer value segments with descriptions
    all_segments = {
        'Low Value': 'Low Value (≤$100 spend)',
        'Medium Value': 'Medium Value ($101-$500 spend)',
        'High Value': 'High Value ($500+ spend)'
    }
    
    # Create a complete dataset with all segments
    complete_data = []
    for segment, description in all_segments.items():
        # Find if this segment exists in the data
        segment_data = df[df[names_col] == segment]
        if not segment_data.empty:
            value = segment_data[values_col].iloc[0]
            complete_data.append({'segment': description, 'value': value, 'original_name': segment})
        else:
            # Add segment with 0 value to ensure it appears in legend
            complete_data.append({'segment': description, 'value': 0, 'original_name': segment})
    
    # Create pie chart with complete data
    fig = px.pie(
        pd.DataFrame(complete_data),
        names='segment',
        values='value',
        title=title,
        height=height
    )
    
    # Update layout with enhanced styling
    fig.update_layout(
        title_x=0.5,
        title_font_size=16,
        showlegend=True,
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=12)
        )
    )
    
    # Hide segments with 0 values but keep them in legend
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Revenue: $%{value:,.2f}<extra></extra>",
        textinfo="percent"
    )
    
    return fig

def create_metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal"
) -> None:
    """
    Display a metric card using Streamlit's metric component
    
    Args:
        label: Metric label
        value: Metric value
        delta: Change indicator (optional)
        delta_color: Color of delta ("normal", "inverse", "off")
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color
    )

def create_sales_trend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a comprehensive sales trend chart with multiple metrics
    
    Args:
        df: DataFrame with sales trend data
        
    Returns:
        Plotly figure with subplots
    """
    if df.empty:
        return go.Figure()
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Total Sales', 'Total Orders', 'Average Order Value', 'Total Items'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Add traces (pure line charts for better trend visualization)
    fig.add_trace(
        go.Scatter(
            x=df['month_year'], 
            y=df['total_sales'],
            mode='lines',
            name='Total Sales',
            line=dict(color=COLOR_SCHEMES['primary'][0], width=2)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['month_year'], 
            y=df['total_orders'],
            mode='lines',
            name='Total Orders',
            line=dict(color=COLOR_SCHEMES['primary'][1], width=2)
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['month_year'], 
            y=df['avg_order_value'],
            mode='lines',
            name='Avg Order Value',
            line=dict(color=COLOR_SCHEMES['primary'][2], width=2)
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['month_year'], 
            y=df['total_items'],
            mode='lines',
            name='Total Items',
            line=dict(color=COLOR_SCHEMES['primary'][3], width=2)
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    return fig

def create_regional_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Create a heatmap for regional sales analysis
    
    Args:
        df: DataFrame with regional sales data
        
    Returns:
        Plotly heatmap figure
    """
    if df.empty:
        return go.Figure()
    
    # Ensure 'total_sales' is float to avoid Decimal errors
    df = df.copy()
    df['total_sales'] = df['total_sales'].astype(float)

    # Pivot data for heatmap
    pivot_df = df.pivot(
        index='customer_region', 
        columns='seller_region', 
        values='total_sales'
    ).fillna(0)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='Blues',
        text=pivot_df.values.round(2),
        texttemplate="%{text:,}",
        textfont={"size": 14},
        hoverongaps=False
    ))
    
    fig.update_layout(
        title="Regional Sales Heatmap (Customer vs Seller)",
        title_x=0.5,
        xaxis_title="Seller Region",
        yaxis_title="Customer Region",
        height=500,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def create_payment_method_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a comprehensive payment method analysis chart
    
    Args:
        df: DataFrame with payment analysis data
        
    Returns:
        Plotly figure with multiple chart types
    """
    if df.empty:
        return go.Figure()
    
    # Create subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Payment Method Distribution', 'Payment Method Performance'),
        specs=[[{"type": "pie"}, {"type": "bar"}]]
    )
    
    # Pie chart for distribution
    fig.add_trace(
        go.Pie(
            labels=df['primary_payment_type'],
            values=df['total_orders'],
            name="Orders by Payment Type"
        ),
        row=1, col=1
    )
    
    # Bar chart for performance
    fig.add_trace(
        go.Bar(
            x=df['primary_payment_type'],
            y=df['total_sales'],
            name="Sales by Payment Type",
            marker_color=COLOR_SCHEMES['primary']
        ),
        row=1, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=500,
        title_text="Payment Method Analysis",
        title_x=0.5,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def create_delivery_performance_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a delivery performance analysis chart
    
    Args:
        df: DataFrame with delivery performance data
        
    Returns:
        Plotly figure with delivery metrics
    """
    if df.empty:
        return go.Figure()
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Avg Delivery Days', 'On-Time Delivery Rate', 'Delivery vs Estimate', 'Regional Performance'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Avg delivery days
    fig.add_trace(
        go.Bar(
            x=df['customer_region'],
            y=df['avg_delivery_days'],
            name='Avg Delivery Days',
            marker_color=COLOR_SCHEMES['primary'][0]
        ),
        row=1, col=1
    )
    
    # On-time delivery rate
    fig.add_trace(
        go.Bar(
            x=df['customer_region'],
            y=df['on_time_delivery_rate'],
            name='On-Time Rate (%)',
            marker_color=COLOR_SCHEMES['primary'][1]
        ),
        row=1, col=2
    )
    
    # Delivery vs estimate
    fig.add_trace(
        go.Bar(
            x=df['customer_region'],
            y=df['avg_delivery_vs_estimate'],
            name='Days vs Estimate',
            marker_color=COLOR_SCHEMES['primary'][2]
        ),
        row=2, col=1
    )
    
    # Regional performance (scatter)
    fig.add_trace(
        go.Scatter(
            x=df['avg_delivery_days'],
            y=df['on_time_delivery_rate'],
            mode='markers+text',
            text=df['customer_region'],
            textposition="middle right",
            name='Regional Performance',
            marker=dict(
                size=df['total_orders'] / 1000,  # Size by order volume
                color=COLOR_SCHEMES['primary'][3],
                showscale=True
            )
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        title_text="Delivery Performance Analysis",
        title_x=0.5,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    return fig

def format_currency(value: float) -> str:
    """
    Format numeric value as currency
    
    Args:
        value: Numeric value to format
        
    Returns:
        Formatted currency string
    """
    if pd.isna(value) or value == 0:
        return "$0.00"
    
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    else:
        return f"${value:.2f}"

def format_percentage(value: float) -> str:
    """
    Format numeric value as percentage
    
    Args:
        value: Numeric value to format (0-1 or 0-100)
        
    Returns:
        Formatted percentage string
    """
    if pd.isna(value):
        return "0.0%"
    
    # Handle both 0-1 and 0-100 ranges
    if abs(value) <= 1:
        return f"{value*100:.1f}%"
    else:
        return f"{value:.1f}%"





