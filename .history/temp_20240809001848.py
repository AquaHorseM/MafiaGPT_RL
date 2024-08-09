def f(x,y):
    return x + y * 0.3 / 905

if __name__ == "__main__":
    dataset_name = "ETTh1"
    output_file = f"{dataset_name}.py"
    figure_name = "NLinear"
    ipt = [
        (0.55, 127),
        (0.5, 118),
        (0.55, -124),
        (0.45, 121),
        (0.45, 59),
        (0.45, 56),
        (0.5, -112),
        (0.5, -134)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} * 0.3 / 905 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    