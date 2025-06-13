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

# --- Tambah Judul Baru ke Spreadsheet ---
st.subheader("➕ Tambah Judul Anime Baru")

with st.form("form_tambah_anime"):
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Judul Anime")
        score = st.number_input("Skor", min_value=0.0, max_value=10.0, step=0.1)
        episodes = st.number_input("Jumlah Episode", min_value=1, step=1)
    with col2:
        vote = st.number_input("Jumlah Vote", min_value=0, step=1)
        status = st.selectbox("Status", options=["Finished Airing", "Currently Airing", "Not Yet Aired"])

    submit = st.form_submit_button("📥 Tambahkan ke Tabel")

    if submit:
        if title.strip() == "":
            st.warning("⚠️ Judul tidak boleh kosong!")
        else:
            new_row = [[title.strip(), score, episodes, vote, status]]
            try:
                sheet.append_rows(new_row)  # Tambah ke baris akhir
                st.success(f"✅ Anime '{title}' berhasil ditambahkan!")
                st.experimental_rerun()  # Muat ulang aplikasi agar tabel ter-update
            except Exception as e:
                st.error(f"❌ Gagal menambahkan: {e}")

# --- Edit & Hapus Data ---
st.subheader("🛠️ Edit atau Hapus Anime")

# Tambahkan indeks untuk baris
df_filtered = df_filtered.reset_index(drop=True)
selected_row = st.selectbox("Pilih Anime yang ingin diedit atau dihapus:", df_filtered['Title'])

# Ambil baris index-nya
row_index = df_filtered[df_filtered['Title'] == selected_row].index[0]
sheet_row_number = df[df['Title'] == selected_row].index[0] + 2  # +2 karena header di baris 1, dan index 0-based

with st.expander("✏️ Edit Data"):
    with st.form("form_edit"):
        new_title = st.text_input("Judul Anime", value=df_filtered.loc[row_index, 'Title'])
        new_score = st.number_input("Skor", min_value=0.0, max_value=10.0, value=float(df_filtered.loc[row_index, 'Score']), step=0.1)
        new_episodes = st.number_input("Jumlah Episode", min_value=1, value=int(df_filtered.loc[row_index, 'Episodes']), step=1)
        new_vote = st.number_input("Jumlah Vote", min_value=0, value=int(df_filtered.loc[row_index, 'Vote']), step=1)
        new_status = st.selectbox("Status", options=["Finished Airing", "Currently Airing", "Not Yet Aired"], index=["Finished Airing", "Currently Airing", "Not Yet Aired"].index(df_filtered.loc[row_index, 'Status']))

        submit_edit = st.form_submit_button("💾 Simpan Perubahan")

        if submit_edit:
            try:
                sheet.update(f"A{sheet_row_number}:E{sheet_row_number}", [[new_title, new_score, new_episodes, new_vote, new_status]])
                st.success("✅ Data berhasil diperbarui!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Gagal mengedit data: {e}")

with st.expander("🗑️ Hapus Data"):
    if st.button("Hapus Anime Ini"):
        try:
            sheet.delete_rows(sheet_row_number)
            st.success("✅ Baris berhasil dihapus!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"❌ Gagal menghapus baris: {e}")
