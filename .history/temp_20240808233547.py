def f(x,y):
    return x + y / 8270

if __name__ == "__main__":
    while True:
        x = eval(input("Enter x: "))
        y = eval(input("Enter y: "))
        print(f"{x} + {y} / 8270 = {f(x,y)}")