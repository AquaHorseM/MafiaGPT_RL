def f(x,y):
    return x + y * 0.2 / 428

if __name__ == "__main__":
    dataset_name = "Traffic2"
    output_file = f"{dataset_name}.py"
    figure_name = "MLP"
    ipt = [
        (0.75, 73),
        (0.75, -135),
        (0.7, -73),
        (0.6, 121),
        (0.6, 85),
        (0.6, 91),
        (0.6, 92),
        (0.6, 57),
        (0.6, 68)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} * 0.2 / 428 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    