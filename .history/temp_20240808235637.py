def f(x,y):
    return x + y / 8270

if __name__ == "__main__":
    dataset_name = "Weather"
    output_file = f"{dataset_name}.py"
    figure_name = "ModernTCN"
    ipt = [
        (0.24, -89),
        (0.24, -133),
        (0.2, 114),
        (0.24, -274),
        (0.22, -122),
        (0.22, -135),
        (0.24, -304)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} / 8270 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    