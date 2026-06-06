#屬性
#print(__name__)
#print(__file__)
#print(__doc__)
#print(__package__)

def main(): #定義一個函式 main(主程式)
    print("這裡是main function的命名空間")
    print(m)

if __name__ == '__main__': #當前模組是主程式
    n = 10
    m = 20
    print(n)
    main() #呼叫 main 函式