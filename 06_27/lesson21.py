import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

labels = ['奶茶', '紅茶', '綠茶', '咖啡']
values = [50, 25, 35, 40]
colors = ['#FFB6C1', '#87CEFA', '#98FB98', '#D3D3D3']
explode = [0.2, 0, 0, 0]

figure = plt.figure()
axes = figure.add_subplot()
axes.pie(values,
         labels=labels,
         colors=colors,
         explode=explode,
         shadow=True,
         autopct="%1.1f%%",
         startangle=90)

plt.show()
