import streamlit as st
import requests
import pandas as pd
import time

# Настройка страницы
st.set_page_config(page_title="App Store Review Parser", page_icon="🍏", layout="centered")

st.title("🍏 App Store Review Parser")
st.write("Скрипт выгружает до 500 последних отзывов о приложении из выбранного региона.")

# --- Боковая панель или форма настроек ---
with st.form("parser_form"):
    app_id = st.number_input("Введите App ID приложения:", value=570060128, step=1)
    country = st.text_input("Код страны (например: ru, us, kz):", value="ru").lower().strip()
    submit_button = st.form_submit_button(label="Собрать отзывы")

# --- Логика парсинга при нажатии кнопки ---
if submit_button:
    all_reviews = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    status_text.info(f"Начинаем сбор отзывов для App ID: {app_id} (Регион: {country.upper()})...")
    
    for page in range(1, 11):
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"page={page}/id={app_id}/sortby=mostrecent/json"
        )

        try:
            resp = requests.get(url, timeout=15)
        except Exception as e:
            st.error(f"Ошибка сети на странице {page}: {e}")
            break

        if resp.status_code != 200:
            # Если страница 1 вернула ошибку, возможно ID или страна неверны
            if page == 1:
                st.error(f"Не удалось получить данные. Проверьте правильность App ID и кода страны (Статус: {resp.status_code}).")
            break

        data = resp.json()
        entries = data.get("feed", {}).get("entry", [])

        if page == 1 and entries:
            entries = entries[1:]  # Первый элемент — метаданные приложения

        if not entries:
            break

        for e in entries:
            try:
                all_reviews.append({
                    "date":   e["updated"]["label"][:10],
                    "rating": int(e["im:rating biographical"] if "im:rating" in e else e["im:rating"]["label"]), # Фикс на случай разных ключей
                    "review": e["content"]["label"]
                })
            except (KeyError, ValueError):
                # Альтернативный вариант парсинга рейтинга, если структура чуть изменится
                try:
                    all_reviews.append({
                        "date":   e["updated"]["label"][:10],
                        "rating": int(e["im:rating"]["label"]),
                        "review": e["content"]["label"]
                    })
                except:
                    continue

        status_text.text(f"Загрузка: Страница {page} обработана. Всего отзывов: {len(all_reviews)}")
        progress_bar.progress(page * 10)
        time.sleep(0.3)

    # --- Вывод результатов ---
    progress_bar.empty()
    
    if not all_reviews:
        status_text.warning("⚠️ Отзывы не найдены. Возможно, у приложения нет отзывов в этом регионе или неверно указан ID.")
    else:
        status_text.success(f"✅ Успешно собрано отзывов: {len(all_reviews)}")
        
        # Создаем датафрейм
        df = pd.DataFrame(all_reviews)[["date", "rating", "review"]]
        
        # Отображаем таблицу в интерфейсе
        st.dataframe(df, use_container_width=True)
        
        # Конвертируем в CSV для скачивания (с поддержкой Excel / utf-8-sig)
        csv_data = df.to_csv(index=False, encoding="utf-8-sig")
        
        st.download_button(
            label="💾 Скачать отзывы в CSV",
            data=csv_data,
            file_name=f"reviews_{app_id}_{country}.csv",
            mime="text/csv"
        )