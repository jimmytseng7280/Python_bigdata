import streamlit as st
import matplotlib.pyplot as plt

st.title("手機品牌市占率圓餅圖")

brands = ["Nokia", "Samsung", "Apple", "Lumia"]
values = [20, 30, 45, 10]
colors = ["yellow", "green", "red", "blue"]
explode = (0.3, 0, 0, 0)

fig, ax = plt.subplots()
ax.pie(
    values,
    labels=brands,
    colors=colors,
    explode=explode,
    shadow=True,
    autopct="%1.1f%%",
    startangle=180,
)
ax.axis("equal")

st.pyplot(fig)
