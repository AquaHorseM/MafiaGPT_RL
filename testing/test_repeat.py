import inspect
from functools import partial, wraps

def count_adjustable_params(func):    
    # Get the signature of the function
    sig = inspect.signature(func)
    params = sig.parameters
    
    # Determine if it's a method (by checking if 'self' or 'cls' is the first parameter)
    is_method = inspect.ismethod(func) or (inspect.isfunction(func) and 'self' in params)

    count = 0
    for i, param in enumerate(params.values()):
        print(f"param: {param}")
        # Skip 'self' or 'cls' for methods
        if is_method and i == 0 and param.name in ('self', 'cls'):
            continue
        # Count only adjustable (non-default) parameters
        if param.default == param.empty and param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY, param.KEYWORD_ONLY):
            count += 1
    return count

repeat_num = 3

def _repeat(a):
        #if a is a function, return a(i) for i in range(repeat_num)
        if callable(a):
            param_count = count_adjustable_params(a)
            if param_count == 1:
                return [a(i) for i in range(repeat_num)]
            elif param_count == 0:
                return [a()] * repeat_num
            else:
                raise ValueError(f'Function must have 0 or 1 parameter, but it has {param_count} parameters.')
        else:
            return [a for _ in range(repeat_num)]
    
class A:
    def __init__(self, value):
        self.value = value
        
    def mult(self, x):
        return self.value * x
    
    def double_mult(self, x, y):
        return self.value * x * y
    
if __name__ == '__main__':
    a = A(3)
    print(_repeat(a.mult))
    print(_repeat(partial(a.double_mult, y = 2)))
    