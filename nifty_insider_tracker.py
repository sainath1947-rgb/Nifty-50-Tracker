import streamlit as st
import pandas as pd
from pnsea import NSE
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="Nifty Insider High-Volume Tracker", layout="wide")
st.title("🔥 Nifty 50 Insider High-Volume Tracker")
st.markdown("**Real-time tracking of insider buys & sells (high volume) from NSE/SEBI disclosures**")

# Initialize NSE client
@st.cache_resource
def get_nse_client():
    return NSE()

nse = get_nse_client()

# Get latest Nifty 50 symbols (auto-updated hourly)
@st.cache_data(ttl=3600)
def get_nifty50_symbols():
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
    df = pd.read_csv(url)
    symbols = df['Symbol'].dropna().str.strip().tolist()
    return set(symbols)

nifty_symbols = get_nifty50_symbols()

# Sidebar filters
st.sidebar.header("Filters")
days_back = st.sidebar.slider("Look back (days)", 1, 90, 30)
min_volume = st.sidebar.number_input("Minimum shares (high volume threshold)", value=500000, step=100000)

date_to = datetime.now().date()
date_from = date_to - timedelta(days=days_back)

st.sidebar.info(f"Showing data from **{date_from}** to **{date_to}**")

# Fetch button
if st.button("Fetch Latest Insider Transactions", type="primary"):
    with st.spinner("Fetching fresh data from NSE..."):
        try:
            # Fetch insider data
            data = nse.insider.insider_data(
                from_date=date_from.strftime("%d-%m-%Y"),
                to_date=date_to.strftime("%d-%m-%Y")
            )

            if not data:
                st.warning("No data returned. Try a different date range.")
            else:
                df = pd.DataFrame(data)

                # Clean column names
                df = df.rename(columns={
                    'symbol': 'Symbol',
                    'companyName': 'Company',
                    'nameOfAcquirerDisposer': 'Insider',
                    'noOfSecurities': 'Shares',
                    'acquisitionDisposal': 'Type',
                    'broadcastDateTime': 'Date',
                    'value': 'Value (₹)'
                })

                # Filter to only Nifty 50 stocks
                df = df[df['Symbol'].isin(nifty_symbols)].copy()

                # Convert data types
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                if 'Shares' in df.columns:
                    df['Shares'] = pd.to_numeric(df['Shares'], errors='coerce')
                if 'Value (₹)' in df.columns:
                    df['Value (₹)'] = pd.to_numeric(df['Value (₹)'], errors='coerce')

                # High-volume filter
                high_volume_df = df[df['Shares'] >= min_volume].copy()

                # Classify Buy vs Sell
                high_volume_df['Action'] = high_volume_df['Type'].apply(
                    lambda x: '● BUY' if isinstance(x, str) and ('Acquisition' in x or 'Buy' in x) else '● SELL'
                )

                st.success(f"Found **{len(high_volume_df)} high-volume insider transactions** in Nifty 50 stocks")

                # Display table
                st.subheader("High-Volume Insider Transactions")
                display_cols = ['Date', 'Symbol', 'Company', 'Insider', 'Action', 'Shares', 'Value (₹)', 'Type']
                st.dataframe(
                    high_volume_df[display_cols].sort_values(by='Shares', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )

                # Quick stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total High-Volume Buys", len(high_volume_df[high_volume_df['Action'] == '● BUY']))
                with col2:
                    st.metric("Total High-Volume Sells", len(high_volume_df[high_volume_df['Action'] == '● SELL']))
                with col3:
                    st.metric("Biggest Single Transaction (shares)", f"{high_volume_df['Shares'].max():,} shares")

                # Optional: full raw data
                with st.expander("See full raw data (including low-volume)"):
                    st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Error fetching data: {e}")
            st.info("Tip: The library is very reliable. Try again in a few minutes if NSE is slow.")

else:
    st.info("👆 Click the button above to load the latest insider data")

st.caption("Built with ❤️ using official NSE data • Data refreshes instantly • Completely free & open-source")