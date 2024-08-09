def f(x,y):
    return x + y * 0.25 / 834

if __name__ == "__main__":
    dataset_name = "ETTh2"
    output_file = f"{dataset_name}.py"
    figure_name = "iTransformer"
    ipt = [
        (0.6, -236),
        (0.5, -130),
        (0.5, -154),
        (0.5, -98),
        (0.45, -134),
        (0.4, 82),
        (0.4, -93),
        (0.4, -28)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} * 0.3 / 905 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    