def f(x,y):
    return x + y * 0.3 / 905

if __name__ == "__main__":
    dataset_name = "Weather"
    output_file = f"{dataset_name}.py"
    figure_name = "MLP"
    ipt = [
        (0.7, -132),
        (0.5, 123),
        (0.5, 114),
        (0.5, 56),
        (0.5, -125),
        (0.5, -204)
    ]
    result = []
    while len(ipt) > 0:
        x, y = ipt.pop(0)
        z = f(x,y)
        print(f"{x} + {y} / 8270 = {z}")
        result.append(z)
    with open(output_file, "a") as f:
        f.write(f"{figure_name} = {result}\n")
    