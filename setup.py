import platform
from typing import Literal

import pip
from setuptools import setup


def prompt_pytorch_choice(
    available_backends: list[str]
) -> str:
    print("Input backend number: ")
    for n, item in enumerate(available_backends):
        print(f"{n}. [{item}]")

    try:
        user_input = int(input("Backend number: ")) - 1
        return available_backends[user_input]

    except (ValueError, IndexError):
        print("Falling back to [cpu] backend")

    return available_backends[
        available_backends.index('cpu')
    ]


def install_pytorch():
    matched_cpu_install: list[str] = ["install"]
    available_backends: dict[Literal['cuda', 'rocm'] | str, list[str]] = {}

    match platform.system():
        case 'Windows':
            matched_cpu_install.extend(("torch", "torchvision", "torchaudio"))
            available_backends['cuda11'] = [
                'install', 'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu118'
            ]
            available_backends['cuda'] = [
                'install', 'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu124'
            ]
            available_backends['cuda12.6'] = [
                'install', 'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu126'
            ]

        case 'Linux':
            matched_cpu_install.extend((
                "torch",
                "torchvision",
                "torchaudio",
                "--index-url",
                "https://download.pytorch.org/whl/cpu"
            ))
            available_backends['cuda11'] = [
                'install', 'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu118'
            ]
            available_backends['cuda12'] = [
                'install', 'torch', 'torchvision', 'torchaudio'
            ]
            available_backends['cuda12.6'] = [
                'install', 'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu126'
            ]
            available_backends['rocm'] = [
                'install', 'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/rocm6.2.4'
            ]

    available_backends['cpu'] = matched_cpu_install
    matched_install = prompt_pytorch_choice(list(available_backends.keys()))
    pip.main(available_backends[matched_install])


def install_detectron2():
    pip.main(
        ['install', 'git+https://github.com/facebookresearch/detectron2.git', '--no-build-isolation']
    )


setup()
install_pytorch()
install_detectron2()
