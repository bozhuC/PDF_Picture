import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import zipfile

# --- 页面全局配置 ---
st.set_page_config(page_title="PDF工坊 - Web版", page_icon="✂️", layout="wide")

st.title("📄 PDF工坊 - Web版 (作者：Acu-BBamboo)")
st.markdown("纯净、极速的 PDF 转高清长图/单图神器。**无需安装，随开随用。**")

# --- 初始化状态 (用于保存每一页的裁切参数) ---
if 'crop_ratios' not in st.session_state:
    st.session_state.crop_ratios = {}

# --- 侧边栏：导入与设置 ---
with st.sidebar:
    st.header("1. 📁 导入设置")
    uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])
    
    st.markdown("---")
    st.header("⚙️ 全局设置")
    dpi = st.number_input("渲染清晰度 (DPI)", min_value=72, max_value=600, value=300, step=50)
    st.caption("300为标准高清。数值越高，生成的图片越清晰，但处理时间会稍长。")

if uploaded_file:
    # 读取 PDF 进内存
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)

    # 自动为每一页初始化裁切参数
    for i in range(total_pages):
        if i not in st.session_state.crop_ratios:
            st.session_state.crop_ratios[i] = (0.0, 0.0)

    # --- 主区域：编辑与预览 ---
    st.header("✂️ 2. 裁切与预览")
    
    col1, col2 = st.columns([1, 2]) # 左右比例 1:2

    with col1:
        # 左侧控制面板
        page_idx = st.number_input(f"选择预览页码 (共 {total_pages} 页)", min_value=1, max_value=total_pages, value=1) - 1
        
        current_top, current_bottom = st.session_state.crop_ratios[page_idx]
        
        new_top = st.slider("顶部丢弃比例 (%)", 0.0, 99.0, current_top * 100, step=0.5) / 100.0
        new_bottom = st.slider("底部丢弃比例 (%)", 0.0, 99.0, current_bottom * 100, step=0.5) / 100.0
        
        # 保存当前页的调整
        if new_top + new_bottom < 1.0:
            st.session_state.crop_ratios[page_idx] = (new_top, new_bottom)
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ 将此比例应用到所有页", use_container_width=True):
            for i in range(total_pages):
                st.session_state.crop_ratios[i] = (new_top, new_bottom)
            st.success("已成功同步至所有页面！", icon="✅")

    with col2:
        # 右侧预览画面 (使用 150 DPI 快速渲染预览图)
        page = doc.load_page(page_idx)
        matrix = fitz.Matrix(150 / 72.0, 150 / 72.0)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 执行裁切预览
        w, h = img.size
        t_y, b_y = int(h * new_top), int(h * (1 - new_bottom))
        cropped_preview = img.crop((0, t_y, w, b_y))
        
        st.image(cropped_preview, caption=f"第 {page_idx + 1} 页 (实时裁切预览)", use_container_width=True)

    # --- 底部：导出区域 ---
    st.markdown("---")
    st.header("💾 3. 导出作品")

    # 定义一个渲染所有高清原图的函数
    def render_all_images():
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        imgs = []
        for i in range(total_pages):
            p = doc.load_page(i)
            px = p.get_pixmap(matrix=matrix)
            im = Image.frombytes("RGB", [px.width, px.height], px.samples)
            tr, br = st.session_state.crop_ratios[i]
            width, height = im.size
            imgs.append(im.crop((0, int(height * tr), width, int(height * (1 - br)))))
        return imgs

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        if st.button("🚀 生成无缝长图", use_container_width=True, type="primary"):
            with st.spinner('正在全速渲染并拼接高清长图...'):
                imgs = render_all_images()
                total_h = sum(img.size[1] for img in imgs)
                max_w = max(img.size[0] for img in imgs)
                long_img = Image.new("RGB", (max_w, total_h), (255, 255, 255))
                
                curr_y = 0
                for img in imgs:
                    long_img.paste(img, ((max_w - img.size[0]) // 2, curr_y))
                    curr_y += img.size[1]
                
                # 将图片保存到内存，用于网页下载
                buf = io.BytesIO()
                long_img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.success("长图生成完毕！点击下方按钮下载。")
                st.download_button(
                    label="⬇️ 下载高清长图 (.png)",
                    data=byte_im,
                    file_name="PDF工坊_长图导出.png",
                    mime="image/png",
                    use_container_width=True
                )

    with col_exp2:
        if st.button("🚀 生成单页图片压缩包", use_container_width=True):
            with st.spinner('正在批量切图并打包压缩...'):
                imgs = render_all_images()
                zip_buf = io.BytesIO()
                
                with zipfile.ZipFile(zip_buf, "w") as zf:
                    for i, img in enumerate(imgs):
                        img_buf = io.BytesIO()
                        img.save(img_buf, format="PNG")
                        zf.writestr(f"PDF工坊_第{i+1}页.png", img_buf.getvalue())
                        
                st.success("打包完毕！点击下方按钮下载。")
                st.download_button(
                    label="⬇️ 下载单页压缩包 (.zip)",
                    data=zip_buf.getvalue(),
                    file_name="PDF工坊_单页集合.zip",
                    mime="application/zip",
                    use_container_width=True
                )
else:
    st.info("👈 请在左侧侧边栏上传 PDF 文件开始工作。")