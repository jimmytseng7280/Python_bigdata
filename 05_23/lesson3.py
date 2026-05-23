import random

# 電腦隨機產生 1~100 的數字
answer = random.randint(1, 100)

print("=== 猜數字遊戲 ===")
print("請猜一個 1 到 100 的數字")

count = 0

while True:
    guess = int(input("請輸入你猜測的數字："))
    count += 1

    if guess > answer:
        print("太大了！")
    elif guess < answer:
        print("太小了！")
    else:
        print("恭喜答對！")
        print(f"你總共猜了 {count} 次")
        break