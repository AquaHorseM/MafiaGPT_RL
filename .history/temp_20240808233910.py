def f(x,y):
    return x + y / 8270

if __name__ == "__main__":
    ipt = [
        (0.3, -128),
        (0.26, 132),
        (0.26, -148),
        (0.24, -151),
        (0.24, -79),
        (0.2, 140),
        (0.2, 110),
        (0.2, 60)
    ]
    result = []
    while True:
        x = eval(input("Enter x: "))
        y = eval(input("Enter y: "))
        z = f(x,y)
        print(f"{x} + {y} / 8270 = {z}")
        result.append(z)