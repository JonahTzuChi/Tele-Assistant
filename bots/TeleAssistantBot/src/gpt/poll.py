class __PollingPolicy:
    def __init__(self, name):
        self.__name = name

    def __str__(self):
        return f"Policy: {self.__name}"


class LinearAdditiveGrowth(__PollingPolicy):
    def __init__(self, name="Linear Additive", step=1):
        super().__init__(name)
        self.__step = step

    def __call__(self, x) -> int:
        return x + self.__step


class LinearMultiplicativeGrowth(__PollingPolicy):
    def __init__(self, name="Linear Multiplicative", factor=2):
        super().__init__(name)
        self.__factor = factor

    def __call__(self, x) -> int:
        return x * self.__factor


class ExponentialGrowth(__PollingPolicy):
    def __init__(self, name = "Exponential", factor = 2):
        super().__init__(name)
        self.__factor = factor

    def __call__(self, x) -> int:
        return x**self.__factor
