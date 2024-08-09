def f(x,y):
    return x + y / 8270

if __name__ == "__main__":
    while True:
        x,y = eval(input())
        print(f"{x} + {y} / 8270 = {f(x,y)}")