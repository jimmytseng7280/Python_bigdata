#資料結構list (list建立後可修改內容, Read and Write)
#list的建立方式是使用方括號[]，元素之間用逗號分隔。
#list的特點是可變（mutable），可以修改其內容，包括添加、刪除和修改元素。
#list的使用場景非常廣泛，適用於需要存儲有序數據、需要頻繁修改數據的情況等。
scores = [80,20,30,40,50]
print(scores)
print(scores[0]) #索引從0開始
print(scores[1]) #索引從0開始
scores[1] = 90
print(scores[1]) #索引從0開始
print(scores)


#資料結構tuple (tuple建立後不可修改內容, Read only)
#tuple的建立方式是使用小括號()，元素之間用逗號分隔。
#tuple的特點是不可變（immutable），一旦創建後就不能修改其內容。
#tuple的使用場景包括需要保護數據不被修改、作為字典的鍵（因為字典的鍵必須是不可變類型）等。
scores1 = (85,92,87,73,59)
print(scores1)
print(scores1[0]) #索引從0開始
print(scores1[1]) #索引從0開始


#dict (dict建立後可修改內容, Read and Write)
#dict的建立方式是使用花括號{}，鍵值對之間用冒號:分隔，鍵值對之間用逗號分隔。
#dict的特點是無序（在Python 3.7之前）或有序（在Python 3.7及以後），鍵必須是不可變類型，值可以是任意類型。
#dict的使用場景包括需要存儲鍵值對數據、需要快速查找數據的情況等。
#dict的使用方式是通過鍵來訪問對應的值，可以使用方括號[]來訪問或修改值。
student = {'chinese': 85, 'english': 92, 'math': 87, 'history': 73, 'science': 59}
print(student)
print(student['chinese']) #使用鍵來訪問值
print(student['english']) #使用鍵來訪問值