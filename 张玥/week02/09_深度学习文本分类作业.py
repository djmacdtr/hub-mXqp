import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

# ==========================
# 一、数据读取与基础预处理
# ==========================
# 从 TSV 文件中读取数据
# 每一行： [文本, 标签]
dataset = pd.read_csv("../../Week01/dataset.csv", sep="\t", header=None)
texts = dataset[0].tolist()          # 文本列表，例如："帮我导航到北京"
string_labels = dataset[1].tolist()  # 标签列表，例如："Travel-Query"

# --------------------------
# 标签数值化（模型只能处理数字）
# --------------------------
# 类似 Java 中的 enum → int 映射
label_to_index = {label: i for i, label in enumerate(set(string_labels))}
numerical_labels = [label_to_index[label] for label in string_labels]

# ==========================
# 二、字符表（Vocabulary）构建
# ==========================
# <pad> 用于补齐长度，对应索引 0
char_to_index = {'<pad>': 0}

# 遍历所有文本，构建字符到索引的映射
for text in texts:
    for char in text:
        if char not in char_to_index:
            char_to_index[char] = len(char_to_index)

# 反向映射（预测时用）
index_to_char = {i: char for char, i in char_to_index.items()}

# 字符表大小，直接决定模型输入维度
vocab_size = len(char_to_index)

# 每条文本的最大长度（超出截断，不足补 0）
max_len = 40

# ==========================
# 三、自定义 Dataset：字符级 Bag-of-Words
# ==========================
class CharBoWDataset(Dataset):
    def __init__(self, texts, labels, char_to_index, max_len, vocab_size):
        self.texts = texts
        self.labels = torch.tensor(labels, dtype=torch.long)
        self.char_to_index = char_to_index
        self.max_len = max_len
        self.vocab_size = vocab_size

        # 预先构造好所有样本的 BoW 向量（一次性算好，训练更快）
        self.bow_vectors = self._create_bow_vectors()

    def _create_bow_vectors(self):
        """
        将文本转换为字符级 Bag-of-Words 向量
        每个样本最终是一个长度为 vocab_size 的向量
        """
        tokenized_texts = []
        for text in self.texts:
            # 1. 字符 → index
            tokenized = [self.char_to_index.get(char, 0) for char in text[:self.max_len]]
            # 2. padding 到固定长度
            tokenized += [0] * (self.max_len - len(tokenized))
            tokenized_texts.append(tokenized)

        bow_vectors = []
        for text_indices in tokenized_texts:
            # 初始化一个全 0 的 BoW 向量
            bow_vector = torch.zeros(self.vocab_size)
            # 统计字符出现次数（忽略 padding=0）
            for index in text_indices:
                if index != 0:
                    bow_vector[index] += 1
            bow_vectors.append(bow_vector)

        # 堆叠成 [样本数, vocab_size]
        return torch.stack(bow_vectors)

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        # 返回 (特征, 标签)
        return self.bow_vectors[idx], self.labels[idx]

# ==========================
# 四、模型定义：两层全连接神经网络
# ==========================
'''
输入 → 隐藏层 → 输出层
单层结果大致如下：
初始loss：Epoch [1/10], Loss: 2.4112
Epoch [5/10], Loss: 1.1933
最终loss：Epoch [10/10], Loss: 0.5814
'''
# class SimpleClassifier(nn.Module):
#     def __init__(self, input_dim, hidden_dim, output_dim):
#         """
#         input_dim  : 输入维度（字符表大小）
#         hidden_dim : 隐藏层神经元个数（模型容量关键参数）
#         output_dim : 类别数
#         """
#         super(SimpleClassifier, self).__init__()
#
#         # 第一层：输入 → 隐藏表示
#         self.fc1 = nn.Linear(input_dim, hidden_dim)
#         # 非线性激活函数
#         self.relu = nn.ReLU()
#         # 第二层：隐藏表示 → 类别打分
#         self.fc2 = nn.Linear(hidden_dim, output_dim)
#
#     def forward(self, x):
#         """
#         前向传播：定义数据如何在模型中流动
#         """
#         out = self.fc1(x)   # 线性变换
#         out = self.relu(out)  # 非线性
#         out = self.fc2(out)   # 输出每个类别的分数
#         return out

'''
尝试增加层数
输入 → 隐藏层1 → 隐藏层2 → 输出
结果如下：
Epoch [1/10], Loss: 2.4442，
Epoch [5/10], Loss: 1.9793，
Epoch [10/10], Loss: 0.6320
对比下来发现，增加层数后，两层模型不仅收敛更慢，而且最终 loss 更高
研究得出以下结论：
1.在小规模文本数据集上，模型性能主要受数据质量和特征表示限制
2.单隐藏层模型已能充分拟合任务需求，继续增加节点数收益有限
3.在未引入正则化和训练技巧的情况下，增加网络层数会提高训练难度，导致 loss 下降变慢甚至性能下降
'''
class SimpleClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(SimpleClassifier, self).__init__()

        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu1 = nn.ReLU()

        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.relu2 = nn.ReLU()

        self.fc3 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu1(x)

        x = self.fc2(x)
        x = self.relu2(x)

        x = self.fc3(x)
        return x


# ==========================
# 五、数据加载与模型初始化
# ==========================
# 构建 Dataset
char_dataset = CharBoWDataset(
    texts, numerical_labels, char_to_index, max_len, vocab_size
)

# DataLoader：负责 batch 化和打乱数据
dataloader = DataLoader(char_dataset, batch_size=32, shuffle=True)

# 模型超参数
hidden_dim = 128                     # 可调参数 - 隐藏层维度 表示模型容量

'''
首先尝试 hidden_dim = 32， 如果效果不好， 逐步增加 hidden_dim 的值， 观察验证集精度的变化。
验证结果如下：
初始loss：Epoch [1/10], Loss: 2.4022
最终loss：Epoch [10/10], Loss: 0.5917
收敛情况：逐步平稳下降
'''
# hidden_dim = 32
'''
尝试 hidden_dim = 64
验证结果如下：
初始loss：Epoch [1/10], Loss: 2.4037
最终loss：Epoch [10/10], Loss: 0.5871
收敛情况：逐步平稳下降，略优于 hidden_dim=32 但是区别并不大
'''
# hidden_dim = 64
'''
尝试 hidden_dim = 256
验证结果如下：
初始loss：Epoch [1/10], Loss: 2.4112
Epoch [5/10], Loss: 1.1933
最终loss：Epoch [10/10], Loss: 0.5814
收敛情况：先前几轮下降较快，后期趋于平稳，略优于 hidden_dim=128  但提升并不明显，可能是数据量有限的原因？
'''
# hidden_dim = 256
'''
增大到4位数 hidden_dim = 1024
验证结果如下：
初始loss：Epoch [1/10], Loss: 2.3975
Epoch [5/10], Loss: 1.1890
最终loss：Epoch [10/10], Loss: 0.5790
收敛情况：与 hidden_dim=256 相比提升不大，但是发现运行时间明显增加。
'''
# hidden_dim = 1024

output_dim = len(label_to_index)     # 类别数 - 输出维度

# 初始化模型
model = SimpleClassifier(vocab_size, hidden_dim, output_dim)

# 损失函数：内部包含 softmax
criterion = nn.CrossEntropyLoss()

# 优化器：随机梯度下降（SGD）
optimizer = optim.SGD(model.parameters(), lr=0.01)

# ==========================
# 六、训练循环
# ==========================
num_epochs = 10

for epoch in range(num_epochs):
    model.train()  # 训练模式
    running_loss = 0.0

    for idx, (inputs, labels) in enumerate(dataloader):
        # 1. 梯度清零
        optimizer.zero_grad()

        # 2. 前向传播（预测）
        outputs = model(inputs)

        # 3. 计算 loss
        loss = criterion(outputs, labels)

        # 4. 反向传播（计算梯度）
        loss.backward()

        # 5. 参数更新
        optimizer.step()

        running_loss += loss.item()

        if idx % 50 == 0:
            print(f"Batch {idx}, 当前 Batch Loss: {loss.item():.4f}")

    # 每个 epoch 的平均 loss
    print(f"Epoch [{epoch + 1}/{num_epochs}], Loss: {running_loss / len(dataloader):.4f}")

# ==========================
# 七、预测函数（推理阶段）
# ==========================
def classify_text(text, model, char_to_index, vocab_size, max_len, index_to_label):
    # 与训练阶段一致的特征构造流程
    tokenized = [char_to_index.get(char, 0) for char in text[:max_len]]
    tokenized += [0] * (max_len - len(tokenized))

    bow_vector = torch.zeros(vocab_size)
    for index in tokenized:
        if index != 0:
            bow_vector[index] += 1

    # 增加 batch 维度
    bow_vector = bow_vector.unsqueeze(0)

    model.eval()  # 推理模式
    with torch.no_grad():
        output = model(bow_vector)

    # 取分数最大的类别
    _, predicted_index = torch.max(output, 1)
    predicted_label = index_to_label[predicted_index.item()]

    return predicted_label

# 索引 → 标签
index_to_label = {i: label for label, i in label_to_index.items()}

# 测试预测
new_text = "帮我导航到北京"
print(f"输入 '{new_text}' 预测为: '{classify_text(new_text, model, char_to_index, vocab_size, max_len, index_to_label)}'")

new_text_2 = "查询明天北京的天气"
print(f"输入 '{new_text_2}' 预测为: '{classify_text(new_text_2, model, char_to_index, vocab_size, max_len, index_to_label)}'")
