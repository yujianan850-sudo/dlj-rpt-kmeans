import matplotlib.pyplot as plt

# 绘图
def draw(data,labels):
    plt.subplot(2,1,1)
    plt.plot(data, color='blue', label='current')
    plt.subplot(2,1,2)
    plt.plot(labels, color='red', label='labels')
    plt.show()

def drawbytime(times, values, labels):
    # 绘制图形的代码
    plt.plot(times, values, label='Values')
    plt.plot(times, labels, label='Labels')
    plt.xlabel('Time')
    plt.ylabel('Values and Labels')
    plt.legend()
    plt.show()