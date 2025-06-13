import pandas as pd
import streamlit as st
import plotly.express as px
from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import json

# --- Konfigurasi Streamlit ---
st.set_page_config(page_title="Anime Explorer Dashboard", layout="wide")
st.title("🎌 Anime Explorer Dashboard")

# --- Autentikasi Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
credentials = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(credentials)
sheet = client.open("AnimeDataset100").sheet1

# --- Load Data ---
df = get_as_dataframe(sheet).dropna(how="all")

# --- Preprocessing ---
df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
df['Episodes'] = pd.to_numeric(df['Episodes'], errors='coerce')
df['Vote'] = pd.to_numeric(df['Vote'], errors='coerce')
df = df.head(100)  # Batasi ke 100 anime teratas

# --- Sidebar Filter ---
st.sidebar.header("🔍 Filter Anime")
st.sidebar.markdown("Filter berdasarkan kriteria berikut:")

min_score, max_score = float(df['Score'].min()), float(df['Score'].max())
score_range = st.sidebar.slider("Skor Anime", min_score, max_score, (min_score, max_score), step=0.1)

status_list = df['Status'].dropna().unique().tolist()
selected_status = st.sidebar.multiselect("Status Tayang", status_list, default=status_list)

# --- Filtered Data ---
df_filtered = df[
    (df['Score'] >= score_range[0]) &
    (df['Score'] <= score_range[1]) &
    (df['Status'].isin(selected_status))
]

# --- Statistik Sidebar ---
st.sidebar.markdown("---")
st.sidebar.metric("Jumlah Anime", len(df_filtered))
st.sidebar.metric("Skor Tertinggi", f"{df_filtered['Score'].max():.2f}")
st.sidebar.metric("Rata-rata Episode", f"{df_filtered['Episodes'].mean():.1f}")

# --- Tabel Data ---
st.subheader("📋 Tabel Anime Terpilih")
st.dataframe(df_filtered[['Title', 'Score', 'Episodes', 'Vote', 'Status']], use_container_width=True)

# --- Visualisasi Skor ---
st.subheader("⭐ Distribusi Skor Anime")
fig1 = px.histogram(df_filtered, x='Score', nbins=20, title='Distribusi Skor Anime')
st.plotly_chart(fig1, use_container_width=True)

# --- Visualisasi Episode vs Skor ---
st.subheader("🎞️ Episode vs Skor")
fig2 = px.scatter(df_filtered, x='Episodes', y='Score', hover_name='Title', size='Vote', title='Episode vs Skor', color='Status')
st.plotly_chart(fig2, use_container_width=True)

# --- Visualisasi Popularitas ---
st.subheader("📈 Vote Terbanyak")
top_voted = df_filtered.sort_values(by='Vote', ascending=False).head(10)
fig3 = px.bar(top_voted, x='Vote', y='Title', orientation='h', title='Top 10 Anime Berdasarkan Vote')
st.plotly_chart(fig3, use_container_width=True)

# --- Unduh Data ---
st.subheader("⬇️ Unduh Data")
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

csv = convert_df(df_filtered)
st.download_button("Download CSV", csv, "anime_terpilih.csv", "text/csv")
