def f(x,y):
    return x + y / 8270

if __name__ == "__main__":
    dataset_name = "Weather"
    output_file = f"{dataset_name}.py"
    figure_name = "iTransformer"
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
    while ipt:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} / 8270 = {z}")
        result.append(z)
    with open(output_file, "w") as f:
        f.write(f"{figure_name} = {result}")
    