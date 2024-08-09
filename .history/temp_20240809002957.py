def f(x,y):
    return x + y * 0.25 / 834

if __name__ == "__main__":
    dataset_name = "ETTh1"
    output_file = f"{dataset_name}.py"
    figure_name = "ModernTCN"
    ipt = [
        (0.6, -257),
        (0.55, -255),
        (0.4, 161),
        (0.4, 88),
        (0.4, 76),
        (0.55, -399),
        (0.55, -408)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} * 0.3 / 905 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    