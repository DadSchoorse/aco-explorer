# ACO explorer

Simple Python script to continuously output various ACO specific representations of a GLSL compute shader.
The output files are automatically updated when the input file changes.


## Dependencies
- python 3.10
- RADV
- Fossilize
- glslang
- inotify-tools

## Usage

```
usage: aco_explorer.py [-h] [--nir NIR] [--acoir ACOIR] [--asm ASM]
                       [--stats STATS]
                       input

positional arguments:
  input          GLSL compute shader input path

options:
  -h, --help     show this help message and exit
  --nir NIR      NIR output path
  --acoir ACOIR  ACO IR output path
  --asm ASM      GCN/RDNA asm output path
  --stats STATS  shader stats output path
```

## Useful Environment Variables

| Environment Variable               | Description  |
| :--------------------------------- | :----------- |
| `FOSSILIZE`                        | Prefix for the Fossilize cli commands, e.g. a local Fossilize build |
| `RADV_PATH`                        | RADV icd json file, default is `/usr/share/vulkan/icd.d/radeon_icd.x86_64.json` |
| `RADV_FAMILY`                      | AMD gpu generation that's used for the output, default is sienna_cichlid. See https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/src/amd/common/amd_family.c for a complete list. |
