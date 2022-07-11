# Приложение Дэш
import dash
import dash_core_components as dcc
# Создание html элементов
import dash_html_components as html
# Разделение сайта на таблицу для удобного расположения
import dash_bootstrap_components as dbc
# Функции передачи парметров из слайдера в функцию, которая строит график и наоборот (график в приложение)
# State - состояние, применяется как тригер обновления (для кнопки)
# Кнопка нужна если данных слишком много, чтобы не обновлять все время, сделана кнопка
from dash.dependencies import Input, Output, State
# Добавление таблицы на вторую выкладку на сайте
import dash_table

import requests
import pandas as pd
# Нужно для категорий точек
import numpy as np
# График
import plotly.express as px
import plotly.graph_objects as go

""" READ DATA """

# результат запроса API (2000 строк)
response = requests.get('http://asterank.com/api/kepler?query={}&limit=1000')
# перевод результата в json
df = pd.json_normalize(response.json())
# Пока не учитываем отрицательное вращение
df = df[df["PER"] > 0]

# График из радиуса и температуры планет в кельвинах (В возвращении функции нет смысла его строить)
# fig = px.scatter(df, x='RPLANET', y='A')


# Категория размеров звезд
# Проценты, размеры звезд
bins = [0, 0.8, 1.2, 100]
names = ["Меньше солнца", "Похожа на солнце", "Больше солнца"]
# Разбили колонку размер звезд на размеры и названия
df['StarSize'] = pd.cut(df['RSTAR'], bins, labels=names)

# Температура категория
tp_bins = [0, 200, 400, 500, 5000]
tp_labels = ["Низкая", "Оптимальная", "Высокая", "Экстремальная"]
df['temp'] = pd.cut(df['TPLANET'], tp_bins, labels=tp_labels)

# Категория размеров
rp_bins = [0, 0.5, 2, 4, 100]
rp_labels = ["Низкий", "Оптимальный", "Высокий", "Экстремальный"]
# 0,5 и 4 подходящая, 4 возможная, если в специальных костюмах
df['level gravity'] = pd.cut(df['RPLANET'], rp_bins, labels=rp_labels)

# Статус планеты
df['Status'] = np.where((df['temp'] == "Оптимальная") &
                        (df['level gravity'] == "Оптимальный"),
                        "Подходящий", None)
df['Status'] = np.where((df['temp'] == "Оптимальная") &
                        (df['level gravity'].isin(["Низкий", "Высокий"])),
                        "Сложно-допустимый", df['Status'])
df['Status'] = np.where((df['level gravity'] == "Оптимальный") &
                        (df['temp'].isin(["Низкая", "Высокая"])),
                        "Сложно-допустимый", df['Status'])
df['Status'] = df.Status.fillna("Экстремальный")

# Относительное расстояние (расстояние до солнца/сумма радиусов планеты)
df.loc[:, 'relative_dist'] = df['A'] / df['RSTAR']

# print(df.groupby('Status')['ROW'].count())

""" ГЛОБАЛЬНЫЕ ПАРАМЕТРЫ ДИЗАЙНА """

CHARTS_TEMPLATE = go.layout.Template(
    layout=dict(
        font=dict(family='Century Gothic'),
        legend=dict(orientation='h',
                    title_text='',
                    x=0,
                    y=1.2)
    )
)
# СПЕЦИАЛЬНЫЕ ЦВЕТА ДЛЯ ГРАФИКОВ (СЕРЫЙ, КРАСНЫЙ, ЗЕЛЕНЫЙ)
COLOR_STATUS_VALUES = ['#b3b3b3', '#ff1a1a', '#00ff00']
COLOR_STATUS_VALUES1 = ['#00ff00', '#b3b3b3', '#ff1a1a']

# Список словарей, в каждом из которых идут значыения из категорий
options1 = []
for k in names:
    options1.append({"label": k, "value": k})

# Название, настройки (значения категории), значения, несколько значений (Фильтер размера звезд)
star_size_selector = dcc.Dropdown(
    id="star-selector",
    options=options1,
    value=["Меньше солнца", "Похожа на солнце", "Больше солнца"],
    multi=True
)

# Фильтер радиуса планет
rplanet_selector = dcc.RangeSlider(
    id="range-slider",
    # Минимальное от радиуса
    min=min(df['RPLANET']),
    # Максимальное от радиуса
    max=max(df['RPLANET']),
    # Отметки на слайдере
    marks={5: "5", 10: "10", 20: "20"},
    # Шаг
    step=1,
    # Начальные значения
    value=[min(df['RPLANET']), max(df['RPLANET'])]
)

# Выкладки приложения

tab1_content = [
    dbc.Row([
        dbc.Col([
            html.Div(
                "(Длина) Температура планеты ~ (Ширина) Расстояние от звезды"),
            # Диаграмма расстояний
            dcc.Graph(id="dist-temp-chart")
        ],
            md=6),
        dbc.Col([
            html.Div("Позиция на небесной сфере (небесные координаты) (Длина) Прямое восхождение ~ (Ширина) Склонение"),
            # Диаграмма планет
            dcc.Graph(id="celestial-chart")
        ],
            md=6)
    ],
        style={"margin-bottom": 40,
               "margin-top": 20}),
    dbc.Row([
        # Диаграмма расстояний
        dbc.Col([
            html.Div("Относительное расстояние планеты до звезды включая ее радиус"),
            dcc.Graph(id="relative-dist-chart")
        ],
            md=6),
        # Диаграмма звезд
        dbc.Col([
            html.Div("(Длина) Температура звезды ~ (Ширина) Масса звезды"),
            dcc.Graph(id="mstar-tstar-chart")
        ],
            md=6)
    ])
]

tab2_content = [
    dbc.Row([
        dbc.Col([
            html.Div("Исходные данные"),
            html.Div(id="data-table"),
        ])
    ],
        style={"margin-top": 20})
]

# ТАБЛИЦА В ВЫКЛАДКЕ О СТРАНИЦЕ

table_header = [
    html.Thead(html.Tr([html.Th("Имя поля"), html.Th("Описание")]))
]

expl = {'KOI': "Номер интересующего объекта",
        'A': "Большая полуось (AU)",
        'RPLANET': "Радиус планеты (радиусы Земли)",
        'RSTAR': "Звездный радиус (Солнечные радиусы)",
        'TSTAR': "Эффективная температура звезды-хозяина, указанная в KIC (Кельвинах)",
        'KMAG': "Магнитуда Кеплера (kmag)",
        'TPLANET': "Равновесная температура планеты, согласно Боруцки и др. (Кельвинах)",
        'T0': "Время транзитного центра (BJD-2454900)",
        'UT0': "Неопределенность во времени транзитного центра (+-jd)",
        'UT0': "Неопределенность во времени транзитного центра (+-jd)",
        'PER': "Период (дни)",
        'UPER': "Неопределенность периода (+-дней)",
        'DEC': "Склонение (@J200)",
        'RA': "Прямое восхождение (@J200)",
        'MSTAR': "Полученная звездная масса(msol)"
        }

tbl_rows = []
for i in expl:
    tbl_rows.append(html.Tr([html.Td(i), html.Td(expl[i])]))
table_body = [html.Tbody(tbl_rows)]
table = dbc.Table(table_header + table_body, bordered=True)

About_content = [
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Div(
                    "Привет всем! Я, студент Кооперативного техникума, Антипин Дмитрий и это моя страница - дашборд,"
                    " его суть, показать, что есть планеты схожие на нашу, где может быть жизнь и многое другое."),
                html.A("Данные поступают из Kepler API через asterank.com", href='http://www.asterank.com/kepler')
            ]),
        ],
            style={"margin-bottom": 40}),

        dbc.Row([
            dbc.Col(width={'size': 3}),
            dbc.Col(html.Div(children=table),
                    width={'size': 6}),
        ]),
    ],
        style={"margin-top": 20})
]

# Дэш приложение (инициализация)

app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP])

""" LAYOUT """

app.layout = html.Div([
    # Header
    dbc.Row([
        dbc.Col(
            html.Img(src=app.get_asset_url('images/logo.png'),
                     style={'width': '100px', 'margin-left': '40px'}),
            width={'size': 2}
        ),
        dbc.Col([
            html.H1("Экзопланеты, визуализация данных"),
            html.A("Почитать о экзопланетах", href="https://trends.rbc.ru/trends/futurology/607f135e9a79474d800799b7")],
            width={'size': 7}, style={'margin-top': '20px'}),
    ],
        className='app-header'),


    # ДЛЯ ТОГО ЧТОБЫ ПОДГРУЖАТЬ ОДИН ГРАФИК В ПАМЯТЬ ВМЕСТО ВСЕХ СРАЗУ
    # Результат фильтрации


    dcc.Store(id='filtered_date', storage_type='session'),


    # Body
    html.Div([
        dbc.Row([
            # Планеты
            dbc.Col([
                html.Div("Выберите диапазон основных полуосей планеты"),
                html.Div(rplanet_selector)
            ],
                width={"size": 2, }),
            # Звезды
            dbc.Col([
                html.Div("Размер звезды"),
                html.Div(star_size_selector)
            ],
                # Размер и отступ
                width={"size": 3, "offset": 1}),
            # Кнопка, текст, ид, сколько кликов нужно, класс (внешний вид)
            dbc.Col(dbc.Button("Применить", id="submit-val", n_clicks=0,
                               className='mr-2'))
        ],
            style={"margin-bottom": 40}),

        dbc.Tabs([
            dbc.Tab(tab1_content, label='Графики'),
            dbc.Tab(tab2_content, label='Данные'),
            dbc.Tab(About_content, label='О странице')
        ])

    ],
        style={'margin-left': '80px',
               'margin-right': '80px',
               'margin-top': '20px'})
])

""" CALLBACK """


# CALLBACK для фильтрации данных

@app.callback(Output(component_id="filtered_date", component_property="data"),
              [Input(component_id="submit-val", component_property='n_clicks')],
              [State(component_id="range-slider", component_property="value"),
               State(component_id="star-selector", component_property="value")]
              )
def filter_data(n, radius_range, star_size):
    # Две шкалы для выбора графиков
    my_data = df[(df['RPLANET'] > radius_range[0]) &
                 (df['RPLANET'] < radius_range[1]) &
                 (df['StarSize'].isin(star_size))]
    # Параметры как записать в json
    return my_data.to_json(date_format='json', orient='split', default_handler=str)


# Оболочка над функцией используется для динамики (Обращение, пересылание параметров и получение результата)
# Передаем результат в график, Передаем значения
# Значения должны идти в строгом порядке
@app.callback(
    # Ид и то, что передаем (Output - График, Input - значения)
    [Output(component_id="dist-temp-chart", component_property="figure"),
     Output(component_id="celestial-chart", component_property="figure"),
     Output(component_id="relative-dist-chart", component_property="figure"),
     Output(component_id="mstar-tstar-chart", component_property="figure"),
     Output(component_id="data-table", component_property="children")],
    [Input(component_id="filtered_date", component_property='data')]
)
# Функция возвращения графика (Два значения min, max), fig, передается в figure, Также количество кликов - n
def update_dist_temp_chart(data):

    chart_data = pd.read_json(data, orient='split')

    # Температура планеты ~ Расстояние от звезды
    fig = px.scatter(chart_data, x='TPLANET', y="A", color="StarSize", color_discrete_sequence=COLOR_STATUS_VALUES1)
    # Изменение вида графика
    fig.update_layout(template=CHARTS_TEMPLATE)
    # Небесные координаты
    fig1 = px.scatter(chart_data, x='RA', y='DEC', size='RPLANET', color='Status',
                      color_discrete_sequence=COLOR_STATUS_VALUES)
    fig1.update_layout(template=CHARTS_TEMPLATE)
    # Относительное расстояние
    fig2 = px.histogram(chart_data, x='relative_dist',
                        color='Status', barmode='overlay', marginal='violin',
                        color_discrete_sequence=COLOR_STATUS_VALUES)
    fig2.add_vline(x=1, annotation_text='Земля', line_dash='dot')
    fig2.update_layout(template=CHARTS_TEMPLATE)
    # Масса звезды
    fig3 = px.scatter(chart_data, x='MSTAR', y='TSTAR', size='RPLANET', color='Status',
                      color_discrete_sequence=COLOR_STATUS_VALUES)
    fig3.update_layout(template=CHARTS_TEMPLATE)
    # Таблица исходных данных
    raw_data = chart_data.drop(['relative_dist', 'StarSize', 'temp', 'level gravity'], axis=1)
    tbl = dash_table.DataTable(data=raw_data.to_dict('records'),
                               columns=[{'name': i, 'id': i}
                                        for i in raw_data.columns],
                               style_header={'textAlign': 'center'},
                               page_size=40)

    return fig, fig1, fig2, fig3, tbl


if __name__ == '__main__':
    app.run_server(debug=True)
