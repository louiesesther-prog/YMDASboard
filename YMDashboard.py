import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import plotly.express as px

# --- 1. SETTINGS ---
st.set_page_config(page_title="5-Year Quant Lab", layout="wide")
st.title("🏛️ YM/NQ 5-Year Institutional Spike Analysis")

# --- 2. THE META-PARSER ENGINE ---
@st.cache_data
def get_unified_data(uploaded_file, ticker_choice):
    # Live Data Sync
    try:
        live_df = yf.download(ticker_choice, period='60d', interval='15m', progress=False)
        if isinstance(live_df.columns, pd.MultiIndex):
            live_df.columns = live_df.columns.get_level_values(0)
        live_df = live_df.reset_index()
        live_df.columns.values[0] = 'timestamp'
        live_df.columns = [str(col).lower() for col in live_df.columns]
        live_df['timestamp'] = pd.to_datetime(live_df['timestamp'], utc=True).dt.tz_convert('America/New_York')
    except:
        live_df = pd.DataFrame()

    # Historical Data Sync
    if uploaded_file is not None:
        try:
            # FIX 1: Read as Tab-Separated (sep='\t') because your data isn't comma-separated
            hist_df = pd.read_csv(uploaded_file, sep='\t') 
            hist_df.columns = [str(col).lower().strip() for col in hist_df.columns]
            
            # FIX 2: Identify the DateTime column from your specific header
            if 'datetime' in hist_df.columns:
                hist_df.rename(columns={'datetime': 'timestamp'}, inplace=True)
            elif 'date' in hist_df.columns and 'time' in hist_df.columns:
                hist_df['timestamp'] = hist_df['date'].astype(str) + ' ' + hist_df['time'].astype(str)
            else:
                hist_df.rename(columns={hist_df.columns[0]: 'timestamp'}, inplace=True)

            # FIX 3: Convert MT5 periods (2025.07.15) to standard date format
            hist_df['timestamp'] = hist_df['timestamp'].astype(str).str.replace('.', '-', regex=False)
            hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'], errors='coerce', utc=True).dt.tz_convert('America/New_York')
            
            # Clean up and merge
            hist_df = hist_df.dropna(subset=['timestamp'])
            
            # TickVolume vs Volume check (MT5 often uses 'tickvolume' for futures)
            if 'tickvolume' in hist_df.columns and ('volume' not in hist_df.columns or hist_df['volume'].sum() == 0):
                hist_df['volume'] = hist_df['tickvolume']

            df = pd.concat([hist_df, live_df]).drop_duplicates(subset=['timestamp'])
            st.sidebar.success(f"✅ Loaded {len(hist_df):,} historical rows.")
            return df.sort_values('timestamp')
        except Exception as e:
            st.error(f"CSV Error: {e}")
            return live_df
    return live_df

# --- 3. UI & LOGIC ---
ticker = st.sidebar.selectbox("Select Asset", ["YM=F", "NQ=F"])
csv_upload = st.sidebar.file_uploader("Upload 15m_data.csv", type=["csv", "txt"])
z_thresh = st.sidebar.slider("Z-Score Sensitivity", 3.0, 15.0, 5.0)

df = get_unified_data(csv_upload, ticker)

if not df.empty:
    # Quant Calculations
    df['vol_mean'] = df['volume'].rolling(window=20).mean()
    df['vol_std'] = df['volume'].rolling(window=20).std()
    df['z_score'] = (df['volume'] - df['vol_mean']) / df['vol_std']
    
    df['hour_min'] = df['timestamp'].dt.strftime('%H:%M')
    df['session'] = np.where(df['timestamp'].dt.hour.between(9, 16), "US Session", "Non-US Session")
    
    spikes = df[df['z_score'] > z_thresh].copy()

    # Visuals
    st.subheader(f"Analyzing {len(df):,} Bars")
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=df['timestamp'], y=df['close'], name="Price", line=dict(color='#444')))
    fig.add_trace(go.Scattergl(x=spikes['timestamp'], y=spikes['close'], mode='markers', 
                               marker=dict(color='gold', size=7), name="Spike"))
    fig.update_layout(template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Uniformity Chart
    if not spikes.empty:
        pattern = spikes.groupby(['hour_min', 'session']).size().reset_index(name='count')
        freq_fig = px.bar(pattern, x='hour_min', y='count', color='session',
                          color_discrete_map={"US Session": "#00F2FF", "Non-US Session": "#FF007F"})
        freq_fig.update_layout(template="plotly_dark", xaxis={'categoryorder':'total descending'})
        st.plotly_chart(freq_fig, use_container_width=True)
