import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. DASHBOARD CONFIG ---
st.set_page_config(page_title="YM=F Dual Session Tracker", layout="wide")
st.title("📊 YM=F Volume Spike Pattern Analysis")
st.markdown("Comparing institutional spikes in **Non-US** vs **US** Sessions.")

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=600)
def get_ym_data():
    ticker = 'YM=F'
    df_raw = yf.download(tickers=ticker, period='60d', interval='15m')
    
    if df_raw.empty:
        return pd.DataFrame()

    if isinstance(df_raw.columns, pd.MultiIndex):
        df_raw.columns = df_raw.columns.get_level_values(0)
    
    df = df_raw.reset_index()
    df.rename(columns={df.columns[0]: 'timestamp'}, inplace=True)
    df.columns = [str(col).lower() for col in df.columns]
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
    
    # Identify Sessions (Based on EST/New York Time)
    # yfinance data is usually in the exchange timezone (EST for YM)
    df['hour'] = df['timestamp'].dt.hour
    
    # US Session: 09:00 to 16:00 EST
    # Non-US: Everything else (London/Asia)
    df['session'] = np.where(df['hour'].between(9, 16), "US Session", "Non-US Session")
    
    return df

# --- 3. QUANT LOGIC ---
try:
    df = get_ym_data()

    if df.empty:
        st.error("YM=F Data currently unavailable.")
    else:
        # Sidebar Settings
        st.sidebar.header("Filter Controls")
        session_choice = st.sidebar.multiselect(
            "Select Sessions to Analyze", 
            options=["US Session", "Non-US Session"], 
            default=["US Session", "Non-US Session"]
        )
        
        z_thresh = st.sidebar.slider("Volume Spike Sensitivity (Z-Score)", 1.5, 6.0, 3.5)
        
        # Calculate Z-Score
        df['vol_mean'] = df['volume'].rolling(window=20).mean()
        df['vol_std'] = df['volume'].rolling(window=20).std()
        df['z_score'] = (df['volume'] - df['vol_mean']) / df['vol_std']
        
        # Identify Spikes based on Sidebar Selection
        df['is_spike'] = (df['z_score'] > z_thresh) & (df['session'].isin(session_choice))
        spikes_df = df[df['is_spike']].copy()

        # --- 4. THE UI ---
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"15m Candlestick Chart ({', '.join(session_choice)})")
            fig = go.Figure(data=[go.Candlestick(
                x=df['timestamp'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                name="YM Futures"
            )])

            # Mark volume spikes (Yellow for selection)
            fig.add_trace(go.Scatter(
                x=spikes_df['timestamp'],
                y=spikes_df['high'] * 1.001,
                mode='markers',
                marker=dict(color='#FFD700', size=10, symbol='triangle-down'),
                name="Spike Detected"
            ))

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
            st.plotly_chart(fig, width="stretch")

        with col2:
            st.subheader("🕒 Spike Patterns")
            if not spikes_df.empty:
                spikes_df['time'] = spikes_df['timestamp'].dt.strftime('%H:%M')
                spikes_df['date'] = spikes_df['timestamp'].dt.strftime('%Y-%m-%d')
                
                # Display with Session tag
                st.dataframe(
                    spikes_df[['date', 'time', 'session', 'z_score']].sort_values(by='date', ascending=False),
                    width="stretch",
                    height=550
                )
            else:
                st.info("No spikes found in selected session.")

        # --- 5. COMPARISON ANALYSIS ---
        st.divider()
        if not spikes_df.empty:
            st.subheader("📈 Time Uniformity Comparison")
            # Create a bar chart showing which specific hours have the most spikes
            pattern_freq = spikes_df.groupby(['time', 'session']).size().reset_index(name='count')
            
            import plotly.express as px
            freq_fig = px.bar(
                pattern_freq, 
                x='time', 
                y='count', 
                color='session',
                title="When do spikes occur most frequently?",
                barmode='group',
                color_discrete_map={"US Session": "#00CC96", "Non-US Session": "#EF553B"}
            )
            freq_fig.update_layout(template="plotly_dark")
            st.plotly_chart(freq_fig, width="stretch")

except Exception as e:
    st.error(f"Logic Error: {e}")
