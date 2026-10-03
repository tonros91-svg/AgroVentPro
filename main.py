import math
import json
import urllib.request
import flet as ft

def calc_dew_point(t, rh):
    """Расчет точки росы (Магнус-Тетенс)"""
    a = 17.27
    b = 237.7
    rh = max(0.001, rh)
    alpha = ((a * t) / (b + t)) + math.log(rh / 100.0)
    return (b * alpha) / (a - alpha)

def calc_absolute_humidity(t, rh):
    """Расчет абсолютной влажности (г/м³)"""
    p_sat = 6.112 * math.exp((17.67 * t) / (243.5 + t))
    p_v = p_sat * (rh / 100.0)
    return 216.7 * (p_v / (273.15 + t))

def main(page: ft.Page):
    page.title = "АгроВент Калькулятор"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.WHITE
    
    page.window.width = 450
    page.window.height = 800

    def show_message(message, color=ft.Colors.RED_700):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # ==========================================
    # ИНСТРУМЕНТ ЗАЩИТЫ ОТ ПЕРЕСЕЧЕНИЯ ТЕКСТА
    # ==========================================
    def make_input_field(label_text, default_value):
        """Создает поле ввода с отдельным заголовком сверху (исключает наложение текста на рамку)"""
        input_widget = ft.TextField(value=default_value, keyboard_type=ft.KeyboardType.NUMBER, height=45, content_padding=10)
        container = ft.Column([
            ft.Text(label_text, size=13, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_700),
            input_widget
        ], spacing=2)
        return input_widget, container

    # Создаем сами поля ввода и их визуальные контейнеры
    t1_input, t1_block = make_input_field("Темп. воздуха в камере (°C)", "12.3")
    rh1_input, rh1_block = make_input_field("Влажность в камере (%)", "98")
    t_prod_input, t_prod_block = make_input_field("Температура КАРТОФЕЛЯ (°C)", "10.0")
    
    t2_input, t2_block = make_input_field("Темп. улицы (приток) (°C)", "9.0")
    rh2_input, rh2_block = make_input_field("Влажность улицы (%)", "72")

    # ==========================================
    # ЭКРАН 1: КАЛЬКУЛЯТОР (РУЧНОЙ ВВОД)
    # ==========================================
    result_panel = ft.Column(spacing=8)

    def on_calculate(e):
        try:
            t1 = float(t1_input.value.replace(',', '.'))
            rh1 = float(rh1_input.value.replace(',', '.'))
            t_prod = float(t_prod_input.value.replace(',', '.'))
            
            t2 = float(t2_input.value.replace(',', '.'))
            rh2 = float(rh2_input.value.replace(',', '.'))
            
            if not (0 < rh1 <= 100) or not (0 < rh2 <= 100):
                show_message("Влажность должна быть от 1 до 100%")
                return

            dp1 = calc_dew_point(t1, rh1)
            ah1 = calc_absolute_humidity(t1, rh1)
            
            dp2 = calc_dew_point(t2, rh2)
            ah2 = calc_absolute_humidity(t2, rh2)

            result_panel.controls.clear()

            result_panel.controls.append(ft.Text(f"КАМЕРА: Точка росы {dp1:.1f} °C | Влага {ah1:.1f} г/м³", color=ft.Colors.GREY_700))
            result_panel.controls.append(ft.Text(f"УЛИЦА: Точка росы {dp2:.1f} °C | Влага {ah2:.1f} г/м³", color=ft.Colors.GREY_700))
            result_panel.controls.append(ft.Divider(height=10, color=ft.Colors.TRANSPARENT))

            result_panel.controls.append(ft.Text(f"--- ВЕРДИКТ ДЛЯ КАРТОФЕЛЯ ({t_prod} °C) ---", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900))
            
            if t_prod < dp1:
                result_panel.controls.append(ft.Text(f"⚠️ ТЕКУЩИЙ СТАТУС: Картофель 'потеет'. Его температура ниже точки росы ({dp1:.1f} °C).", color=ft.Colors.ORANGE_800, weight=ft.FontWeight.W_500))
            else:
                result_panel.controls.append(ft.Text(f"✅ ТЕКУЩИЙ СТАТУС: Картофель сухой. Конденсата в закрытой камере нет.", color=ft.Colors.BLUE_GREY_700))
                
            result_panel.controls.append(ft.Divider(height=2, color=ft.Colors.TRANSPARENT))
            
            if t_prod < dp2:
                result_panel.controls.append(ft.Text(f"❌ РЕЗУЛЬТАТ ОБДУВА: Не вентилировать! Уличный воздух осядет конденсатом на клубнях.", color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD))
            else:
                if ah2 < ah1:
                    result_panel.controls.append(ft.Text(f"✅ РЕЗУЛЬТАТ ОБДУВА: Включайте вентиляцию! Идет безопасная сушка картофеля.", color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD))
                else:
                    result_panel.controls.append(ft.Text(f"⛔ РЕЗУЛЬТАТ ОБДУВА: Неэффективно. Улица занесет больше влаги, чем выведет (сушка не пойдет).", color=ft.Colors.BROWN_700, weight=ft.FontWeight.W_500))

            page.update()

        except ValueError:
            show_message("Пожалуйста, введите числовые значения")

    calc_button = ft.FilledButton(content=ft.Text("Анализировать вентиляцию", size=15, weight=ft.FontWeight.BOLD), on_click=on_calculate, height=50, width=300)

    # ==========================================
    # ЭКРАН 2: ИНФОРМАЦИЯ О ПОГОДЕ (ОНЛАЙН)
    # ==========================================
    weather_temp_text = ft.Text("-- °C", size=40, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
    weather_rh_text = ft.Text("Влажность: -- %", size=20, color=ft.Colors.GREY_700)
    
    def on_fetch_weather(e):
        try:
            lat = 56.43
            lon = 37.16
            
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
            
            with urllib.request.urlopen(weather_url, timeout=5) as response:
                weather_data = json.loads(response.read().decode())
                
            temp = weather_data["current"]["temperature_2m"]
            rh = weather_data["current"]["relative_humidity_2m"]
            
            weather_temp_text.value = f"{temp} °C"
            weather_rh_text.value = f"Влажность: {rh} %"
            
            show_message("Данные успешно обновлены!", color=ft.Colors.GREEN_700)
            page.update()
            
        except Exception as ex:
            show_message("Ошибка связи с сервером. Проверьте интернет.")

    fetch_weather_btn = ft.FilledButton(content=ft.Text("Обновить данные", size=15, weight=ft.FontWeight.BOLD), on_click=on_fetch_weather, bgcolor=ft.Colors.CYAN_700)


    # ==========================================
    # НАСТРОЙКА НАВИГАЦИИ МЕЖДУ ЭКРАНАМИ
    # ==========================================
    def go_to_main_menu(e):
        main_menu.visible = True
        screen_1.visible = False
        screen_2.visible = False
        page.update()

    def go_to_calculations(e):
        main_menu.visible = False
        screen_1.visible = True
        screen_2.visible = False
        page.update()

    def go_to_weather(e):
        main_menu.visible = False
        screen_1.visible = False
        screen_2.visible = True
        page.update()

    # СБОРКА ЭКРАНОВ
    # 1. Главное меню
    main_menu = ft.Column(
        controls=[
            ft.Container(height=100),
            ft.Text("АгроВент Калькулятор", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Text("С. Рогачёво", size=16, color=ft.Colors.GREY_600),
            ft.Divider(height=50, color=ft.Colors.TRANSPARENT),
            ft.FilledButton(content=ft.Text("📊 Расчеты вентиляции", size=16, weight=ft.FontWeight.BOLD), on_click=go_to_calculations, height=60, width=300),
            ft.Container(height=20),
            ft.FilledButton(content=ft.Text("☁️ Текущая погода", size=16, weight=ft.FontWeight.BOLD), on_click=go_to_weather, height=60, width=300, bgcolor=ft.Colors.CYAN_700),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
        visible=True # При запуске показываем только его
    )

    # 2. Экран калькулятора
    screen_1 = ft.ListView(
        controls=[
            ft.TextButton("⬅ Назад в меню", on_click=go_to_main_menu, icon_color=ft.Colors.BLUE_900),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Text("Внутри хранилища", weight=ft.FontWeight.BOLD, size=18, color=ft.Colors.BLUE_900),
            t1_block, rh1_block, t_prod_block,
            ft.Divider(height=15, color=ft.Colors.GREY_300),
            ft.Text("Приток с улицы (ввод вручную)", weight=ft.FontWeight.BOLD, size=18, color=ft.Colors.BLUE_900),
            t2_block, rh2_block,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Row([calc_button], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            result_panel,
            ft.Container(height=30)
        ],
        padding=20,
        expand=True,
        visible=False
    )

    # 3. Экран погоды
    screen_2 = ft.Column(
        controls=[
            # Изменили START на CENTER для центрирования кнопки
            ft.Row([ft.TextButton("⬅ Назад в меню", on_click=go_to_main_menu)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=20),
            ft.Text("☁️", size=80), 
            ft.Text("Текущая погода", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Московская обл., с. Рогачёво", size=16, color=ft.Colors.GREY_500),
            ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
            weather_temp_text,
            weather_rh_text,
            ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
            fetch_weather_btn
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
        visible=False
    )

    # Добавляем все три экрана на страницу
    page.add(main_menu, screen_1, screen_2)

ft.run(main)