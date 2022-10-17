import re


def run_main():
    for i in range(10):
        if i > 5:
            return
        else:
            yield i


if __name__ == "__main__":
    print(int(3/2))
