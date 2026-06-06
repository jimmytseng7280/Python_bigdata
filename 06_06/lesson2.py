#屬性
#print(__name__)
#print(__file__)
#print(__doc__)
#print(__package__)

r = 50 #定義一個變數 r，這裡是全域命名空間(全域變數或文件變數)。

def main(): #定義一個函式 main(主程式)
    o = 30 #定義一個變數 o，這裡是 main function 的命名空間。
    #在 main 函式內部定義的變數，main 函式外部無法使用，此變數是區域變數。
    print("這裡是main function的命名空間")
    print(m)
    print(o)

if __name__ == '__main__': #當前模組是主程式
    n = 10
    m = 20
    print(n)
    main() #呼叫 main 函式
    print(r)