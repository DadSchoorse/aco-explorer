#!/usr/bin/env python3
# Copyright 2022 Georg Lehmann
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import dataclasses
import os
import pathlib
import subprocess

@dataclasses.dataclass
class EnvInfo:
    glslang: str = "glslangValidator"
    fossilize_path: str = ""
    inotifywait: str = "inotifywait"
    spv_file: str = "/tmp/aco_explorer{}.spv".format(os.getpid())
    foz_file: str = "/tmp/aco_explorer{}.foz".format(os.getpid())
    disasm_dir: str = "/tmp/aco_explorer{}_dis".format(os.getpid())
    radv_path: str = "/usr/share/vulkan/icd.d/radeon_icd.x86_64.json"
    radv_drm_shim = "/path/to/libamdgpu_noop_drm_shim.so"
    radv_family: str = "navi21"

    @property
    def fossilize_synth(self):
        return os.path.join(self.fossilize_path, "fossilize-synth")

    @property
    def fossilize_disasm(self):
        return os.path.join(self.fossilize_path, "fossilize-disasm")

def get_env_info() -> EnvInfo:
    e = EnvInfo()
    for item in vars(e).items():
        envvar = item[0].upper()
        if envvar in os.environ and os.environ[envvar] != "":
            vars(e)[item[0]] = os.environ[envvar]
    return e


ENVIRONMENT = get_env_info()

def inotifywait(file: str) -> bool:
    return subprocess.run([ENVIRONMENT.inotifywait, "-e", "modify", file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def compile_shader(infile: str, outfile: str) -> bool:
    return subprocess.run([ENVIRONMENT.glslang, "-V", "--target-env", "vulkan1.2", "-S", "comp", "--quiet", infile, "-o", outfile]).returncode == 0

def create_foz(infile: str, outfile: str) -> bool:
    return subprocess.run([ENVIRONMENT.fossilize_synth, "--comp", infile, "--output", outfile], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def disassemble_foz(infile: str) -> str:
    out_dir = ENVIRONMENT.disasm_dir
    result = subprocess.run([ENVIRONMENT.fossilize_disasm, infile, "--output", out_dir, "--target", "isa"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(result.stderr.decode('utf-8'))
        return None
    files = os.listdir(out_dir)
    if len(files) != 1:
        return None
    file = os.path.join(out_dir, files[0])
    with open(file, "r") as f:
        output = f.read()
    os.remove(file)
    return output

def write_output(file: str, output: str):
    if file is None:
        return
    with open(file, "w") as f:
        f.write(output)

def output_disasm(disasm: str, args):
    nir = disasm.split("Representation: ACO IR")[0]
    disasm = disasm[len(nir):]
    acoir = disasm.split("Representation: Assembly")[0]
    disasm = disasm[len(acoir):]
    asm = disasm.split("SGPRs")[0]
    stats = disasm[len(asm):]

    write_output(args.nir, nir)
    write_output(args.acoir, acoir)
    write_output(args.asm, asm)
    write_output(args.stats, stats)

def process(args):
    spv_file = ENVIRONMENT.spv_file
    foz_file = ENVIRONMENT.foz_file
    if not compile_shader(args.input, spv_file):
        print("glslang failed")
        return
    if not create_foz(spv_file, foz_file):
        print("fossilize-synth failed")
        return
    disasm = disassemble_foz(foz_file)
    if disasm is None:
        print("fossilize-disasm failed")
        return
    output_disasm(disasm, args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="GLSL compute shader input path")
    parser.add_argument("--nir", type=str, help="NIR output path")
    parser.add_argument("--acoir", type=str, help="ACO IR output path")
    parser.add_argument("--asm", type=str, help="GCN/RDNA asm output path")
    parser.add_argument("--stats", type=str, help="shader stats output path")
    args = parser.parse_args()

    print(args)
    print(ENVIRONMENT)

    os.environ["VK_ICD_FILENAMES"] = ENVIRONMENT.radv_path
    os.environ["AMDGPU_GPU_ID"] = ENVIRONMENT.radv_family
    os.environ["LD_PRELOAD"] = ENVIRONMENT.radv_drm_shim

    pathlib.Path(ENVIRONMENT.spv_file).touch()
    pathlib.Path(ENVIRONMENT.foz_file).touch()
    os.mkdir(ENVIRONMENT.disasm_dir)

    try:
        while True:
            process(args)
            inotifywait(args.input)
    except KeyboardInterrupt:
        print("")

    os.remove(ENVIRONMENT.spv_file)
    os.remove(ENVIRONMENT.foz_file)
    os.rmdir(ENVIRONMENT.disasm_dir)


if __name__ == "__main__":
    main()
