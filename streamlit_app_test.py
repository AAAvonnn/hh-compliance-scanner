import streamlit as st
st.title("HH 合规扫描器 v8")
st.write("正在加载...")
uploaded = st.file_uploader("拖拽视频", type=["mp4","mov","avi"], accept_multiple_files=True)
if uploaded:
    st.write(f"已上传 {len(uploaded)} 个文件")
