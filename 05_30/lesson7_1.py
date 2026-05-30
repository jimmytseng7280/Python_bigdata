#open("student.txt")引數名稱呼叫(可以不依順序呼叫)

try:
	with open(file="student.txt", mode='r', encoding='utf-8') as file:
			data = file.read()
			print(data)
except Exception as e:
	print("發生錯誤:", e)