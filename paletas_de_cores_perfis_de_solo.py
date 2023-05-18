import streamlit as st
import numpy as np
import cv2
from matplotlib import pyplot as plt
from PIL import Image

st.title("Análise de Paleta de Cores em Imagens de Solo")

def extrair_paleta(imagem, n_cores):
    if imagem.shape[2] == 4:  # Remove o canal alfa se existir
        imagem = cv2.cvtColor(imagem, cv2.COLOR_BGRA2BGR)
    pixels = imagem.reshape(-1, 3).astype(np.float32)  # Converte para uma matriz 2D e assegura o tipo correto (float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixels, n_cores, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    segmented_image = centers[labels.flatten()].reshape(imagem.shape)  # Recupera a imagem original
    return centers, segmented_image

n_cores = st.sidebar.slider('Número de cores na paleta:', min_value=2, max_value=20, value=5, step=1)

imagem_up = st.file_uploader("Carregar imagem do solo:", type=['jpg', 'png', 'jpeg'])

if imagem_up is not None:
    imagem = Image.open(imagem_up)
    imagem_cv = np.array(imagem)

    if imagem_cv.size == 0:  # Teste para imagem vazia
        st.error("A imagem carregada está vazia. Por favor, carregue uma imagem válida.")
    else:
        st.image(imagem_cv, caption='Imagem Original', use_column_width=True)

        centers, segmented_image = extrair_paleta(imagem_cv, n_cores)
        st.image(segmented_image, caption='Imagem Segmentada', use_column_width=True)

        st.subheader('Paleta de Cores:')
        plt.figure(figsize=(5, 2))
        plt.imshow([centers.astype(int)], aspect='auto')
        plt.axis('off')
        st.pyplot(plt)
