# Computational environment

Recorded on 2026-10-28 at the start of the project.

| Item | Value |
|---|---|
| Host | Local workstation, WSL2 on Windows (kernel 6.18.54.1-microsoft-standard-WSL2) |
| OS | Ubuntu 26.04.1 LTS |
| CPU | 8 logical cores |
| RAM | 11 GiB |
| GPU | NVIDIA GeForce GTX 1650, 4 GiB (visible via `nvidia-smi`) |
| Disk | ~950 GB free |
| Python | 3.14.4, isolated virtualenv in `.venv/` (not committed) |
| Packages | see `requirements.txt` (numpy, scipy, matplotlib, pandas, plotly, pytest) |

## GPU decision

The GPU is not used. The electrostatic solver is a charge-simulation method
with a few hundred ring charges per geometry: a dense least-squares solve of
roughly 500 x 250 takes milliseconds on the CPU, and field-line tracing is
vectorised NumPy. A full parameter sweep finishes in minutes on the CPU. A
CUDA stack (CuPy or similar) would add install weight and a second code path
without changing the accuracy, which is limited by the physics closures
(Peek onset, Townsend current, no space charge), not by arithmetic.

GPU acceleration would become worthwhile for a self-consistent 3-D
space-charge solver of many discrete pins, which is listed as future work.

## Reproduce

```bash
python3 -m venv --without-pip .venv            # this Ubuntu image ships without ensurepip
curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && .venv/bin/python /tmp/get-pip.py
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```
