def f(x,y):
    return x + y / 8270

if __name__ == "__main__":
    dataset_name = "Weather"
    output_file = f"{dataset_name}.py"
    figure_name = "iTransformer"
    ipt = [
        (0.22, 106),
        (0.24, -105),
        (0.2, 70),
        (0.22, -158),
        (0.22, -173),
        (0.22, -195),
        (0.22, -182),
        (0.22, -173)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} / 8270 = {z}")
        result.append(z)
    with open(output_file, "w") as f:
        f.write(f"{figure_name} = {result}")
    