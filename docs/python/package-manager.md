# Python package and project manager

- [UV](https://docs.astral.sh/uv/): An extremely fast Python package and project manager, written in Rust.

## UV 

> An extremely fast Python package and project manager, written in Rust.
****
### Install Dependencies

Using uv (Recommended):
```**bash**
uv sync
uv run main.py
```

or Using pip + virtual environment:
```bash
python3 -m venv .venv
sh .venv/Scripts/activate & source .venv/Scripts/activate
pip install -e .
python main.py
```