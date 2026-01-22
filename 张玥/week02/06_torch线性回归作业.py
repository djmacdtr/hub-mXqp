import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt

# ==========================
# 1. 构造 sin 数据集
# ==========================
# 为了画曲线更平滑，用等间隔采样，而不是随机采样
# x 范围可以调大：例如 0~2π、0~4π
x_numpy = np.linspace(0, 2 * np.pi, 200).reshape(-1, 1)
y_numpy = np.sin(x_numpy)

# 转成 torch tensor
X = torch.from_numpy(x_numpy).float()
y = torch.from_numpy(y_numpy).float()

# ==========================
# 2. 定义多层网络（MLP）
# ==========================
# 说明：
# - 输入 1 维（x）
# - 输出 1 维（sin(x)）
# - 中间隐藏层越宽/越深，一般表达能力越强，但训练更慢、也更容易不稳定
model = nn.Sequential(
    nn.Linear(1, 64),
    nn.Tanh(),          # 拟合 sin 这种平滑曲线，Tanh 往往比 ReLU 更舒服
    nn.Linear(64, 64),
    nn.Tanh(),
    nn.Linear(64, 1)
)

# ==========================
# 3. 损失函数与优化器
# ==========================
loss_fn = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)  # Adam 对这种函数拟合更省心

# ==========================
# 4. 训练
# ==========================
num_epochs = 3000
for epoch in range(num_epochs):
    model.train()

    y_pred = model(X)
    loss = loss_fn(y_pred, y)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if (epoch + 1) % 300 == 0:
        print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item():.6f}")

# ==========================
# 5. 可视化：真实曲线 vs 拟合曲线
# ==========================
model.eval()
with torch.no_grad():
    y_fit = model(X).cpu().numpy()

plt.figure(figsize=(10, 6))
plt.plot(x_numpy, y_numpy, label="True: sin(x)", linewidth=2)
plt.plot(x_numpy, y_fit, label="Pred: MLP fit", linewidth=2)
plt.scatter(x_numpy[::10], y_numpy[::10], label="Samples (every 10)", alpha=0.4)  # 点一下样本
plt.xlabel("x")
plt.ylabel("y")
plt.title("Fit sin(x) with a Multi-Layer Perceptron (MLP)")
plt.grid(True)
plt.legend()
plt.show()
