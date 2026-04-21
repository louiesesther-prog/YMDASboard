import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import plotly.express as px

# --- 1. DASHBOARD CONFIG ---
st.set_page_config(page_title="YM=F Dual Session Tracker", layout="wide")
st.title("📊 YM=F Volume Spike Pattern Analysis")
st.markdown("Comparing institutional spikes in **Non-US** vs **US** Sessions.")

# --- 2. DATA FETCHING (With Fallback) ---
@st.cache_data(ttl=600)
def get_market_data():
    # Attempt 1: YM Futures (Best for Volume)
    # Attempt 2: ^DJI (Backup if YM fails)
    for ticker in ['YM=F', '^DJI']:
        try:
            df_raw = yf.download(tickers=ticker, period='60d', interval='15m', progress=False)
            if not df_raw.empty and len(df_raw) > 20:
                # Flatten MultiIndex
                if isinstance(df_raw.columns, pd.MultiIndex):
                    df_raw.columns = df_raw.columns.get_level_values(0)
                
                df = df_raw.reset_index()
                # Force timestamp column name
                df.columns.values[0] = 'timestamp'
                df.columns = [str(col).lower() for col in df.columns]
                
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
                
                # Identify Sessions (EST/New York Time)
                df['hour'] = df['timestamp'].dt.hour
                df['session'] = np.where(df['hour'].between(9, 16), "US Session", "Non-US Session")
                return df, ticker
        except Exception:
            continue
    return pd.DataFrame(), None

# --- 3. QUANT LOGIC ---
try:
    df, active_ticker = get_market_data()

    if df.empty:
        st.error("🚨 Market data unavailable. This usually means Yahoo Finance is temporarily blocking the connection. Please refresh in a few minutes.")
        st.info("Technical Tip: If you are seeing this on Streamlit Cloud, it's a common IP block. Trying again usually works.")
    else:
        st.sidebar.success(f"Connected to: {active_ticker}")
        
        # Sidebar Settings
        st.sidebar.header("Filter Controls")
        session_choice = st.sidebar.multiselect(
            "Select Sessions", 
            options=["US Session", "Non-US Session"], 
            default=["US Session", "Non-US Session"]
        )
        
        z_thresh = st.sidebar.slider("Volume Spike Sensitivity (Z-Score)", 1.5, 6.0, 3.5)
        
        # Calculate Z-Score
        df['vol_mean'] = df['volume'].rolling(window=20).mean()
        df['vol_std'] = df['volume'].rolling(window=20).std()
        df['z_score'] = (df['volume'] - df['vol_mean']) / df['vol_std']
        
        # Identify Spikes
        df['is_spike'] = (df['z_score'] > z_thresh) & (df['session'].isin(session_choice))
        spikes_df = df[df['is_spike']].copy()

        # --- 4. THE UI ---
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"15m Chart ({active_ticker})")
            fig = go.Figure(data=[go.Candlestick(
                x=df['timestamp'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                name=active_ticker
            )])

            fig.add_trace(go.Scatter(
                x=spikes_df['timestamp'],
                y=spikes_df['high'] * 1.001,
                mode='markers',
                marker=dict(color='#FFD700', size=10, symbol='triangle-down'),
                name="Volume Spike"
            ))

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
            st.plotly_chart(fig, width="stretch")

        with col2:
            st.subheader("🕒 Spike Patterns")
            if not spikes_df.empty:
                spikes_df['time'] = spikes_df['timestamp'].dt.strftime('%H:%M')
                spikes_df['date'] = spikes_df['timestamp'].dt.strftime('%Y-%m-%d')
                st.dataframe(
                    spikes_df[['date', 'time', 'session', 'z_score']].sort_values(by='date', ascending=False),
                    width="stretch", height=550
                )
            else:
                st.info("No spikes found. Try lowering the Z-Score slider.")

        # --- 5. SEASONALITY ---
        st.divider()
        if not spikes_df.empty:
            st.subheader("📈 Pattern Uniformity: When do spikes occur?")
            pattern_freq = spikes_df.groupby(['time', 'session']).size().reset_index(name='count')
            
            freq_fig = px.bar(
                pattern_freq, x='time', y='count', color='session',
                barmode='group',
                color_discrete_map={"US Session": "#00CC96", "Non-US Session": "#EF553B"}
            )
            freq_fig.update_layout(template="plotly_dark", xaxis_title="Time of Day", yaxis_title="Number of Spikes")
            st.plotly_chart(freq_fig, width="stretch")

except Exception as e:
    st.error(f"Logic Error: {e}")
