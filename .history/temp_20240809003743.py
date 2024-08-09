def f(x,y):
    return x + y * 0.25 / 834

if __name__ == "__main__":
    dataset_name = "ETTh2"
    output_file = f"{dataset_name}.py"
    figure_name = "iTransformer"
    ipt = [
        (0.5, -96),
        (0.55, -266),
        (0.4, -42),
        (0.45, -208),
        (0.4, -125),
        (0.4, -120),
        (0.4, -128),
        (0.35, 29)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} * 0.3 / 905 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    