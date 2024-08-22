def f(x,y):
    return x + y * 0.2 / 428

if __name__ == "__main__":
    dataset_name = "ETTh2"
    output_file = f"{dataset_name}.py"
    figure_name = "ModernTCN"
    ipt = [
        (0.45, -87),
        (0.4, -128),
        (0.35, 0),
        (0.45, -322),
        (0.45, -312),
        (0.40, -175)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} * 0.2 / 428 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    