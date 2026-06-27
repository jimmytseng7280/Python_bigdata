import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

x = np.linspace(0, 4 * np.pi, 500)

fig, ax = plt.subplots(figsize=(10, 6))
plt.subplots_adjust(bottom=0.25)

A_init, omega_init, phi_init = 1.0, 1.0, 0.0

line_sin, = ax.plot(x, A_init * np.sin(omega_init * x + phi_init),
                    label='sin', color='blue', linewidth=2)
line_cos, = ax.plot(x, A_init * np.cos(omega_init * x + phi_init),
                    label='cos', color='red', linewidth=2, linestyle='--')

ax.set_xlim(0, 4 * np.pi)
ax.set_ylim(-5, 5)
ax.set_title('正弦與餘弦波形互動調整', fontsize=14)
ax.set_xlabel('x', fontsize=12)
ax.set_ylabel('y', fontsize=12)
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend(fontsize=11)

ax_A = plt.axes([0.15, 0.12, 0.7, 0.03])
ax_omega = plt.axes([0.15, 0.07, 0.7, 0.03])
ax_phi = plt.axes([0.15, 0.02, 0.7, 0.03])

slider_A = Slider(ax_A, '振幅 A', 0.1, 5.0, valinit=A_init)
slider_omega = Slider(ax_omega, '頻率 ω', 0.1, 10.0, valinit=omega_init)
slider_phi = Slider(ax_phi, '相位 φ', 0, 2 * np.pi, valinit=phi_init)

def update(val):
    A = slider_A.val
    omega = slider_omega.val
    phi = slider_phi.val
    line_sin.set_ydata(A * np.sin(omega * x + phi))
    line_cos.set_ydata(A * np.cos(omega * x + phi))
    ax.set_ylim(-A * 1.5, A * 1.5)
    fig.canvas.draw_idle()

slider_A.on_changed(update)
slider_omega.on_changed(update)
slider_phi.on_changed(update)

plt.show()
