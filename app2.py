import numpy as np
import cv2
import streamlit as st
from PIL import Image
from sklearn.cluster import MiniBatchKMeans

# Função para redimensionar imagem conforme escolha do usuário
def resize_image(image, shape_option):
    original_h, original_w = image.shape[:2]
    target_area = 1.2  # Área em metros quadrados
    scaling_factor = (target_area * 1e6) / (original_h * original_w)

    if shape_option == "Retangular (1200x800)":
        width, height = 1200, 800
    elif shape_option == "Quadrado (1000x1000)":
        width = height = 1000
    else:
        aspect_ratio = original_w / original_h
        height = max(1, int(np.sqrt(scaling_factor / aspect_ratio)))
        width = max(1, int(height * aspect_ratio))
    
    if width > 0 and height > 0:
        resized_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
    else:
        st.error("Erro ao redimensionar a imagem: dimensões inválidas.")
        return None
    return resized_image

# Função para segmentar imagem em camadas de cor com amostragem
def segment_image_into_layers(image, nb_color=5, sample_fraction=0.1):
    data = np.float32(image) / 255.0
    h, w, ch = data.shape
    
    # Amostragem por blocos
    sampled_data = data.reshape((-1, 3))
    sample_size = max(1, int(sampled_data.shape[0] * sample_fraction))
    if sample_size < nb_color:
        st.error("A fração de amostra é muito pequena para o número de camadas solicitado. Aumente a fração de amostra.")
        return None, None
    
    sampled_data = sampled_data[np.random.choice(sampled_data.shape[0], size=sample_size, replace=False)]
    
    kmeans = MiniBatchKMeans(n_clusters=nb_color, random_state=42).fit(sampled_data)
    labels = kmeans.predict(data.reshape((-1, 3))).reshape(h, w)
    
    color_layers = []
    for i in range(nb_color):
        mask = (labels == i).astype(np.uint8) * 255
        color_layer = np.zeros_like(image, dtype=np.float32)
        color_layer[labels == i] = kmeans.cluster_centers_[i]
        color_layers.append(color_layer)
    
    return color_layers, kmeans.cluster_centers_

# Função para preparar camadas para corte em MDF com cores dominantes preservadas
def prepare_layers_for_mdf(color_layers, color_centers):
    mdf_layers = []
    for idx, layer in enumerate(color_layers):
        gray = cv2.cvtColor((layer * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        
        # Suaviza bordas dos contornos
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresholded = cv2.threshold(blurred, 1, 255, cv2.THRESH_BINARY)
        
        # Obtem contornos sólidos e preenchidos
        contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        solid_layer = np.zeros_like(layer)
        
        # Preenche as áreas internas com a cor dominante
        cv2.drawContours(solid_layer, contours, -1, tuple(map(int, color_centers[idx] * 255)), thickness=cv2.FILLED)
        
        # Adiciona um contorno leve e desfocado para efeito "curva de nível"
        cv2.drawContours(solid_layer, contours, -1, (0, 0, 0), thickness=1)
        solid_layer = cv2.GaussianBlur(solid_layer, (3, 3), 0)
        
        mdf_layers.append(solid_layer)
    return mdf_layers

# Interface no Streamlit
st.title('Mapa Topográfico em Camadas')
uploaded_file = st.file_uploader("Carregue uma imagem", type=["jpg", "png"])

if uploaded_file:
    image = np.array(Image.open(uploaded_file).convert("RGB"))
    st.image(image, caption='Imagem Carregada', use_column_width=True)
    
    shape_option = st.selectbox("Escolha o formato da imagem", ["Retangular (1200x800)", "Quadrado (1000x1000)", "Proporção Original"])
    resized_image = resize_image(image, shape_option)
    
    if resized_image is not None:
        nb_color = st.slider('Número de Cores (Camadas)', 1, 50, 5)
        sample_fraction = st.slider('Fração de amostra para processamento', 0.05, 0.5, 0.1)
        color_layers, color_centers = segment_image_into_layers(resized_image, nb_color, sample_fraction)
        
        if color_layers is not None:
            st.subheader("Camadas Segmentadas para Corte")
            mdf_layers = prepare_layers_for_mdf(color_layers, color_centers)
            
            for idx, layer in enumerate(mdf_layers):
                layer_display = (layer * 255).astype(np.uint8)
                st.image(layer_display, caption=f"Camada {idx + 1}", use_column_width=True)
            
            stacked_image = np.zeros_like(mdf_layers[0], dtype=np.uint8)
            for idx, layer in enumerate(mdf_layers):
                stacked_image = cv2.add(stacked_image, (layer * 255).astype(np.uint8))
                
            st.subheader("Mapa Topográfico Empilhado (Visualização)")
            st.image(stacked_image, caption="Mapa Topográfico em Camadas", use_column_width=True)

            result_bytes = cv2.imencode('.png', stacked_image)[1].tobytes()
            st.download_button("Baixar Mapa Topográfico Empilhado", data=result_bytes, file_name='mapa_topografico.png', mime='image/png')
